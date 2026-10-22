#!/usr/bin/env python3
"""Verify a remote deployment by read-only RPC before publishing browser metadata."""
import argparse
import asyncio
import json
from pathlib import Path
from app.blockchain import Chain
from app.config import Settings


async def publish(settings, output):
    if settings.environment == 'local' or settings.chain_id == 31337:
        raise ValueError('This publisher accepts remote deployments only; local fixtures stay in explicit test workflows')
    chain = Chain(settings)
    try:
        await chain.validate()
        manifest = chain.manifest
        token, market = chain.contract('token'), chain.contract('marketplace')
        block = await chain.block('latest')
        async def call(contract, method):
            return await getattr(contract.functions, method)().call(block_identifier=block['number'])
        for method, expected in [('collateral', 'collateral'), ('config', 'config'), ('treasury', 'treasury')]:
            if (await call(token, method)).lower() != manifest['contracts'][expected].lower():
                raise ValueError('deployed AMM links do not match manifest')
        for method, expected in [('token', 'token'), ('oracle', 'oracle')]:
            if (await call(market, method)).lower() != manifest['contracts'][expected].lower():
                raise ValueError('deployed marketplace links do not match manifest')
        if await call(token, 'collateralDecimals') != manifest['collateralDecimals']:
            raise ValueError('collateral precision mismatch')
        if await call(token, 'name') != manifest['tokenName'] or await call(token, 'symbol') != manifest['tokenSymbol']:
            raise ValueError('token identity mismatch')
        if not await call(token, 'reserveHealthy'):
            raise ValueError('reserve accounting check failed')
        await call(chain.contract('oracle'), 'read')
        root = await call(chain.contract('airdrop'), 'merkleRoot')
        if '0x'+root.hex() != manifest['merkleRoot']:
            raise ValueError('airdrop commitment mismatch')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps({'published': True, 'chain_id': settings.chain_id, 'verified_block': block['number'],
                          'note': 'Read-only deployment verification; no transaction was broadcast.'}))
    finally:
        await chain.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('.env.production'))
    parser.add_argument('--output', type=Path, default=Path('frontend/public/deployment.json'))
    args = parser.parse_args()
    try:
        asyncio.run(publish(Settings(_env_file=args.env_file), args.output))
    except Exception as error:
        # Avoid printing provider URLs or connection credentials contained in exception text.
        print(json.dumps({'published': False, 'error_type': type(error).__name__,
                          'message': 'Deployment verification failed. Check configuration and read-only RPC access.'}))
        raise SystemExit(1)
