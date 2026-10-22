import json
from functools import cached_property
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3._utils.events import get_event_data
from .config import ROOT


def hexstr(value):
    return Web3.to_hex(value) if not isinstance(value, str) else value


def serializable(value):
    if isinstance(value, (bytes, bytearray)):
        return Web3.to_hex(value)
    if isinstance(value, dict) or hasattr(value, 'items'):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


class Chain:
    def __init__(self, settings):
        self.settings = settings
        self.w3 = AsyncWeb3(AsyncHTTPProvider(settings.rpc_http, request_kwargs={'timeout': 15}))

    @cached_property
    def manifest(self):
        data = json.loads(self.settings.manifest_path.read_text())
        if data['chainId'] != self.settings.chain_id or data['abiVersion'] != 1:
            raise ValueError('deployment chain or ABI version mismatch')
        expected_environment = 'local' if self.settings.chain_id == 31337 else ('testnet' if self.settings.chain_id in (84532, 421614) else 'mainnet')
        if data.get('environment') != expected_environment:
            raise ValueError('deployment environment mismatch')
        if self.settings.chain_id != 31337 and data.get('dataSource') != 'onchain':
            raise ValueError('remote deployment must declare onchain data provenance')
        for name in ('token', 'collateral', 'marketplace', 'oracle', 'airdrop', 'config', 'treasury', 'feed', 'sequencer'):
            address = data['contracts'].get(name)
            if not Web3.is_address(address) or (int(address, 16) == 0 and not (name == 'sequencer' and self.settings.chain_id == 31337)):
                raise ValueError('invalid deployment address')
        return data

    def contract(self, name):
        mapping = {'token': 'MudTokenAMM', 'marketplace': 'MudMarketplace', 'oracle': 'MudPriceOracle',
                   'config': 'MudProtocolConfig', 'airdrop': 'MudAirdrop', 'treasury': 'MudTreasury'}
        abi = json.loads((ROOT / 'abi' / f'{mapping[name]}.json').read_text())
        return self.w3.eth.contract(address=Web3.to_checksum_address(self.manifest['contracts'][name]), abi=abi)

    async def validate(self):
        if await self.w3.eth.chain_id != self.settings.chain_id:
            raise ValueError('RPC chain ID mismatch')
        for name in ('token', 'collateral', 'marketplace', 'oracle', 'airdrop', 'config', 'treasury', 'feed', 'sequencer'):
            if name == 'sequencer' and self.settings.chain_id == 31337:
                continue
            if not await self.w3.eth.get_code(self.manifest['contracts'][name]):
                raise ValueError(f'no code at {name}')

    async def head(self):
        return await self.w3.eth.block_number

    async def block(self, number):
        b = await self.w3.eth.get_block(number)
        return {'number': b['number'], 'hash': hexstr(b['hash']), 'parent_hash': hexstr(b['parentHash']), 'timestamp': b['timestamp']}

    async def events(self, start, end):
        addresses = [self.manifest['contracts'][k] for k in ('token', 'marketplace', 'config', 'airdrop', 'treasury')]
        logs = await self.w3.eth.get_logs({'fromBlock': start, 'toBlock': end, 'address': addresses})
        codecs = {}
        for name in ('token', 'marketplace', 'config', 'airdrop', 'treasury'):
            c = self.contract(name)
            for abi in c.abi:
                if abi.get('type') == 'event':
                    signature = abi['name']+'('+','.join(i['type'] for i in abi['inputs'])+')'
                    codecs[(c.address.lower(), Web3.keccak(text=signature))] = abi
        result = []
        for log in logs:
            if log.get('removed'):
                raise RuntimeError('removed log requires canonical reconciliation')
            abi = codecs.get((log['address'].lower(), log['topics'][0]))
            if not abi:
                continue
            decoded = get_event_data(self.w3.codec, abi, log)
            args, event = serializable(dict(decoded['args'])), decoded['event']
            if event == 'Transfer' and int(args['from'], 16) != 0 and int(args['to'], 16) != 0:
                continue
            result.append({'tx_hash': hexstr(log['transactionHash']), 'log_index': log['logIndex'],
                           'block_number': log['blockNumber'], 'block_hash': hexstr(log['blockHash']),
                           'transaction_index': log['transactionIndex'], 'event_type': event, 'args': args,
                           'contract': log['address'], 'raw_log': serializable(dict(log))})
        return sorted(result, key=lambda e: (e['block_number'], e['transaction_index'], e['log_index']))

    async def close(self):
        await self.w3.provider.disconnect()
