import asyncio
import json
import time
from ..metrics import CACHE_AGE


class CurveService:
    def __init__(self, chain, redis=None, ttl=5):
        self.chain, self.redis, self.ttl = chain, redis, ttl

    async def spot(self):
        key = f'mud:{self.chain.settings.chain_id}:spot:v1'
        if self.redis:
            cached = await self.redis.get(key)
            if cached:
                value = json.loads(cached)
                age = time.time()-value['quote_timestamp']
                if 0 <= age < self.ttl:
                    CACHE_AGE.set(age)
                    return {**value, 'cached': True, 'cache_age_seconds': age}
        token, oracle = self.chain.contract('token'), self.chain.contract('oracle')
        block = await self.chain.block('latest')
        n = block['number']
        async def call(contract, name):
            return await getattr(contract.functions, name)().call(block_identifier=n)
        supply, reserve, price, fees, gross, net, paused = await asyncio.gather(*[
            call(token, name) for name in ('totalSupply', 'getReserveBalance', 'getSpotPrice', 'accruedFees',
                                          'grossRedemptionLiability', 'netRedemptionLiability', 'paused')])
        try:
            q, updated = await call(oracle, 'read')
            metadata = {'valid': True, 'price_usd8': str(q), 'updated_at': updated, 'age_seconds': block['timestamp']-updated}
        except Exception:
            metadata = {'valid': False, 'error': 'oracle validation failed; checkout unavailable'}
        value = {'kind': 'SNAPSHOT_NOT_EXECUTION', 'chain_id': self.chain.settings.chain_id,
                 'token_address': token.address, 'collateral_address': self.chain.manifest['contracts']['collateral'],
                 'total_supply': str(supply), 'curve_accounted_supply': str(supply), 'reserve_balance': str(reserve),
                 'spot_price': str(price), 'price_units': 'collateral atoms per whole MUD',
                 'collateral_decimals': self.chain.manifest['collateralDecimals'], 'mud_decimals': 18,
                 'accrued_fees': str(fees), 'gross_redemption_liability': str(gross), 'net_redemption_liability': str(net),
                 'coverage_bps': str((reserve-fees)*10000//gross) if gross and reserve >= fees else None,
                 'reserve_healthy': reserve >= gross+fees, 'paused': paused, 'oracle': metadata,
                 'block_number': n, 'block_hash': block['hash'], 'block_timestamp': block['timestamp'],
                 'quote_timestamp': int(time.time()), 'valid_for_seconds': self.ttl,
                 'cached': False, 'cache_age_seconds': 0}
        CACHE_AGE.set(0)
        if self.redis:
            await self.redis.set(key, json.dumps(value), ex=self.ttl)
        return value

    async def quote(self, side, amount):
        block = await self.chain.block('latest')
        values = await getattr(self.chain.contract('token').functions, 'quoteBuy' if side == 'buy' else 'quoteSell')(amount).call(block_identifier=block['number'])
        return {'kind': 'QUOTE_NOT_TRANSACTION', 'side': side, 'input_amount': str(amount), 'output_amount': str(values[0]),
                'fee': str(values[1]), 'curve_cost_or_gross_refund': str(values[2]), 'chain_id': self.chain.settings.chain_id,
                'block_number': block['number'], 'block_hash': block['hash'], 'quote_timestamp': int(time.time()), 'valid_for_seconds': 15}
