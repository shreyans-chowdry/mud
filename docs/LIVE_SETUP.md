# Real-data Base configuration

The default source package contains no sample deployment, preloaded catalog, funded test wallets or active airdrop dataset. Metrics remain unavailable until contracts are deployed and verified. Test fixtures exist only under tests/fixtures and explicit local testing paths. Test executions and historical evidence are not current market data.

## What changed

- Browser builds reject local and testnet manifests unless NEXT_PUBLIC_ALLOW_TEST_NETWORKS=true is explicitly set.
- The deployment handshake verifies the API's actual chain, data source and every contract address before enabling queries and wallet operations.
- Missing data is unavailable, not a zero balance, a $1 collateral assumption, or a fabricated eligibility rejection.
- Public builds use a configured API origin or a same-origin reverse proxy; they do not silently contact a visitor's localhost backend.
- Local fixture seeding requires MUD_SEED_FIXTURES=1 and is prohibited on remote chains.
- A separate Base production Compose file uses external RPC, PostgreSQL, Redis and a real merchant endpoint; it has no local blockchain or mock fulfillment receiver.

## Operator sequence

1. Choose the actual digital product or service and implement its delivery endpoint. The built-in local receiver is intentionally disabled outside local mode; it is not a production delivery service. No sample listings are published automatically.
2. Create a server RPC app and a separate restricted browser RPC app. Obtain managed PostgreSQL and Redis URLs, your HTTPS app/API domains and a merchant delivery endpoint. Follow API_KEYS.md.
3. Copy `.env.example` to the ignored `.env.production`. Fill the blank required values in your hosting secret manager. The template targets Base mainnet, chain 8453. Keep NEXT_PUBLIC_ALLOW_TEST_NETWORKS=false. Never include DEPLOYER_KEY in application runtime configuration.
4. Select official collateral, USD feed and sequencer uptime addresses for Base. Confirm feed precision, heartbeat/max-age policy and token behavior. Chainlink's published uptime feed listings do not establish Sepolia availability; a testnet policy must be reviewed separately. Never turn a test feed into a mainnet fallback.
5. Resolve dependency advisories, independent security/economic review, operational ownership and L1-aware finality policy. The marketplace conversion uses manipulable marginal token pricing; this design still needs a release decision. Mainnet broadcasting remains intentionally disabled in the default deployment script.
6. After a separately reviewed deployment, supply its actual ABI-v1 manifest at the operator-owned deployments/8453.json path. It must declare environment=mainnet and dataSource=onchain; all token/collateral/module/feed addresses must be genuine deployed contracts. A signing key alone does not create this configuration.
7. Run the read-only checks below, then publish the verified manifest. If validation fails, the public application stays unconfigured. These checks do not bypass the mainnet release gate or constitute an audit.
8. Configure HTTPS reverse proxies, backups, secret rotation, private database networking and alert delivery. Build the frontend with the public API and browser RPC values. Start API, indexer and outbox as separate services.
9. Register real merchants and listings through the actual contract interfaces; fund any airdrop through a collateral-backed purchase. Use a real reviewed dataset, or leave eligibility unconfigured. There is no finished merchant administration dashboard yet.
10. Run a restricted acceptance/recovery drill before inviting customers or accepting real funds. Inspect actual explorer receipts, merchant balances, totalSupply burn, finalized orders, receiver idempotency and restored data.

```bash
backend/.venv/bin/python scripts/check-live-config.py --env-file .env.production
backend/.venv/bin/python scripts/check-live-config.py --env-file .env.production --check-chain
backend/.venv/bin/python scripts/publish-manifest.py --env-file .env.production
```

On a configured server, use `docker compose --env-file .env.production -f infrastructure/docker-compose.production.yml up -d --build`. This template binds web ports to loopback and requires an HTTPS reverse proxy. Fill the managed-service connection settings before running migrations. Do not use the local Compose file as a production deployment.

For the preflight script on your Mac, MUD_DEPLOYMENT_FILE must name your Mac's real manifest path; the production container template uses /app/deployments/8453.json. Browser builds require the verified manifest at frontend/public/deployment.json, or the production container's read-only mount. Never replace it with an example address to make checks appear green.

## Explicit isolated local testing

Only for local test assets, use `MUD_SEED_FIXTURES=1 bash infrastructure/scripts/local-up.sh`. This creates local credentials from .env.local.example, and only creates frontend/.env.local if it is absent. It never overwrites existing operator configuration; existing env files may need MUD_ELIGIBILITY_FILE=tests/fixtures/eligibility.local.json and NEXT_PUBLIC_ALLOW_TEST_NETWORKS=true for local test execution.

The local chain, dataset, mocks, seed balances and catalog are test fixtures. They cannot be used to earn money. Preserve existing databases and use a fresh isolated environment for redeployment; an empty restarted chain must not be paired with stale order projections.
