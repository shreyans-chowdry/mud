#!/usr/bin/env python3
"""Read-only Base configuration checks. Reports field names, never credential values."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values
from pydantic import ValidationError
from app.config import Settings
from app.blockchain import Chain


def check(values):
    required = ['MUD_RPC_HTTP', 'MUD_RPC_WS', 'MUD_DATABASE_URL', 'MUD_REDIS_URL', 'MUD_DEPLOYMENT_FILE',
                'MUD_WEBHOOK_URL', 'MUD_WEBHOOK_SECRET', 'MUD_WEBHOOK_ALLOW_HOSTS', 'MUD_CORS_ORIGINS',
                'NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_BASE_RPC']
    issues = [f'{key}: required' for key in required if not values.get(key)]
    if values.get('MUD_CHAIN_ID') != '8453' or values.get('MUD_ENVIRONMENT') != 'production':
        issues.append('Base requires MUD_CHAIN_ID=8453 and MUD_ENVIRONMENT=production')
    if values.get('NEXT_PUBLIC_ALLOW_TEST_NETWORKS', 'false') != 'false':
        issues.append('NEXT_PUBLIC_ALLOW_TEST_NETWORKS must be false')
    for key in ['MUD_RPC_HTTP', 'MUD_WEBHOOK_URL', 'NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_BASE_RPC']:
        parsed = urlparse(values.get(key) or '')
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            issues.append(f'{key}: a valid HTTPS origin/endpoint is required')
    for key in ['MUD_CORS_ORIGINS', 'MUD_WEBHOOK_ALLOW_HOSTS']:
        try:
            entries = json.loads(values.get(key) or '[]')
            if not isinstance(entries, list) or not entries or not all(isinstance(x, str) for x in entries):
                raise ValueError()
            if key == 'MUD_CORS_ORIGINS' and any(urlparse(x).scheme != 'https' or '*' in x for x in entries):
                raise ValueError()
        except (ValueError, TypeError):
            issues.append(f'{key}: a nonempty explicit JSON allowlist is required')
    if values.get('DEPLOYER_KEY'):
        issues.append('DEPLOYER_KEY must not be supplied to application/worker runtime configuration')
    if len(values.get('MUD_WEBHOOK_SECRET') or '') < 32:
        issues.append('MUD_WEBHOOK_SECRET: generate at least 32 random characters')
    return issues


async def check_chain(settings):
    chain = Chain(settings)
    try:
        await chain.validate()
        token = chain.contract('token')
        assert await token.functions.reserveHealthy().call(), 'reserve accounting check failed'
        await chain.contract('oracle').functions.read().call()
    finally:
        await chain.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('.env.production'))
    parser.add_argument('--check-chain', action='store_true', help='Also perform read-only public RPC checks')
    args = parser.parse_args()
    values = {**dotenv_values(args.env_file), **os.environ}
    issues = check(values)
    if issues:
        print(json.dumps({'configured': False, 'issues': issues}, indent=2))
        return 1
    try:
        settings = Settings(_env_file=args.env_file)
    except ValidationError as error:
        print(json.dumps({'configured': False, 'issues': ['.'.join(map(str, e['loc']))+': invalid configuration'
            for e in error.errors(include_input=False)]}, indent=2))
        return 1
    if not settings.manifest_path.is_file():
        print(json.dumps({'configured': False, 'issues': ['MUD_DEPLOYMENT_FILE: verified deployed manifest is missing']}))
        return 1
    if args.check_chain:
        try:
            asyncio.run(check_chain(settings))
        except Exception as error:
            print(json.dumps({'configured': False, 'issues': ['chain verification failed: '+type(error).__name__]}))
            return 1
    print(json.dumps({'configured': True, 'chain_id': settings.chain_id, 'chain_checks_performed': args.check_chain,
                      'note': 'Configuration checks do not establish security audit or production readiness.'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
