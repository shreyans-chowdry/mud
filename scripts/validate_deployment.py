#!/usr/bin/env python3
"""Read-only chain/address/interface and monetary parameter validation."""
import asyncio
import json
from app.blockchain import Chain
from app.config import get_settings


async def main():
    chain = Chain(get_settings())
    try:
        await chain.validate()
        token, market = chain.contract('token'), chain.contract('marketplace')
        assert (await token.functions.collateral().call()).lower() == chain.manifest['contracts']['collateral'].lower()
        assert (await market.functions.token().call()).lower() == token.address.lower()
        assert (await market.functions.oracle().call()).lower() == chain.manifest['contracts']['oracle'].lower()
        assert (await token.functions.config().call()).lower() == chain.manifest['contracts']['config'].lower()
        assert (await token.functions.treasury().call()).lower() == chain.manifest['contracts']['treasury'].lower()
        assert await token.functions.collateralDecimals().call() == chain.manifest['collateralDecimals']
        assert await token.functions.reserveHealthy().call()
        oracle = await chain.contract('oracle').functions.read().call()
        root = await chain.contract('airdrop').functions.merkleRoot().call()
        assert '0x'+root.hex() == chain.manifest['merkleRoot']
        print(json.dumps({'chain_id': chain.settings.chain_id, 'code_and_links_verified': True,
                          'reserve_healthy': True, 'oracle_usd8': str(oracle[0]), 'oracle_updated_at': oracle[1]}))
    finally:
        await chain.close()


if __name__ == '__main__':
    asyncio.run(main())
