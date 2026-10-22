"""Public configuration boundaries must never silently serve test fixtures as live data."""
import json
from types import SimpleNamespace
import httpx
import pytest
from app.blockchain import Chain
from app.config import Settings
from app.main import create_app


def live_settings(**overrides):
    return Settings(_env_file=None, **{'environment': 'production', 'chain_id': 8453,
        'rpc_http': 'https://rpc.example.com', 'rpc_ws': 'wss://rpc.example.com',
        'database_url': 'postgresql+asyncpg://user:password@db.example.com/mud',
        'redis_url': 'rediss://cache.example.com', 'confirmations': 20, 'finality_depth': 128, **overrides})


def test_live_configuration_rejects_test_identity_and_fixtures():
    for fields in [{'chain_id': 31337}, {'environment': 'local'}, {'rpc_http': 'http://localhost:8545'},
                   {'rpc_ws': 'ws://localhost:8545'}, {'eligibility_file': 'tests/fixtures/eligibility.local.json'}]:
        with pytest.raises(ValueError):
            live_settings(**fields)
    assert live_settings().eligibility_file is None


def test_remote_manifest_rejects_missing_provenance_and_zero_addresses(tmp_path):
    path = tmp_path/'manifest.json'
    contracts = {key: '0x'+'11'*20 for key in ['token', 'collateral', 'marketplace', 'airdrop', 'oracle', 'config', 'treasury', 'feed', 'sequencer']}
    manifest = {'chainId': 8453, 'abiVersion': 1, 'environment': 'mainnet', 'contracts': contracts}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='provenance'):
        Chain(live_settings(deployment_file=path)).manifest
    manifest['dataSource'] = 'onchain'
    manifest['contracts']['collateral'] = '0x'+'00'*20
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='address'):
        Chain(live_settings(deployment_file=path)).manifest


@pytest.mark.asyncio
async def test_unconfigured_airdrop_returns_unavailable_not_ineligible(db):
    settings = Settings(_env_file=None, eligibility_file=None, redis_url=None, run_workers=False)
    chain = SimpleNamespace()
    app = create_app(settings, db, chain)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/v1/airdrop/eligibility/0x'+'11'*20)
            assert response.status_code == 503
            assert 'not configured' in response.json()['error']['message']
            assert 'eligible' not in response.json()


@pytest.mark.asyncio
async def test_deployment_status_is_verified_by_rpc_before_returning_metadata(db):
    calls = []

    class VerifiedChain:
        manifest = {'abiVersion': 1, 'environment': 'mainnet', 'dataSource': 'onchain', 'contracts': {'token': '0x'+'11'*20}}

        async def validate(self):
            calls.append('validated')

        async def block(self, number):
            return {'number': 100, 'hash': '0x'+'ab'*32}

    app = create_app(live_settings(), db, VerifiedChain())
    async with app.router.lifespan_context(app):
        # Unit boundary test: no external Redis connection is needed for the fake RPC.
        await app.state.redis.aclose()
        app.state.redis = None
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/v1/deployment')
            assert response.status_code == 200 and response.json()['chain_id'] == 8453
            assert response.json()['data_source'] == 'onchain' and calls == ['validated']
