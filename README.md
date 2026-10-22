# MUD Protocol

A collateral-backed EVM economy with integrated bonding-curve mint/redemption, funded Merkle distribution, signed marketplace orders, genuine token burns, canonical event indexing and durable fulfillment. The intended real-data network is **Base**.

**The public build starts unconfigured.** It contains no deployed MUD addresses, sample catalog, funded wallets or active eligibility dataset. It shows unavailable values until an actual deployment and matching API have been verified. No live MUD deployment, customer revenue, external product delivery or independent audit is claimed.

## Configure real data

Read [live setup](docs/LIVE_SETUP.md), [credential requirements](docs/API_KEYS.md) and [release blockers](docs/THREAT_MODEL.md). Copy `.env.example` to the ignored `.env.production` and fill it in your hosting secret manager. The separate [Base deployment template](infrastructure/docker-compose.production.yml) uses external RPC, PostgreSQL, Redis and your real delivery endpoint; it has no local test blockchain or mock receiver.

After a separately reviewed deployment, supply the actual manifest and run the read-only checks:

```bash
backend/.venv/bin/python scripts/check-live-config.py --env-file .env.production
backend/.venv/bin/python scripts/check-live-config.py --env-file .env.production --check-chain
backend/.venv/bin/python scripts/publish-manifest.py --env-file .env.production
```

Public frontend builds reject local/testnet manifests by default and compare the API's verified chain/module addresses before querying balances or listings. API failures and unconfigured eligibility do not invent zero balances, prices or membership decisions. Browser variables are public; never put signing keys there.

The default release script intentionally refuses mainnet broadcasting. Actual deployment, official asset/feed verification, pricing review, dependency remediation and independent security review remain prerequisites for real funds.

## Verify the implementation

Prerequisites: Node 22, Python 3.11+ and npm. Cloud setup is `bash infrastructure/scripts/cloud-setup.sh`; [cloud handoff](docs/CLOUD_HANDOFF.md) explains laptop-independent execution.

```bash
npm ci
npm --prefix frontend ci
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
backend/.venv/bin/pip install --no-deps -e backend
npm run compile
npm run test:contracts
backend/.venv/bin/python -m pytest backend/tests
backend/.venv/bin/ruff check backend scripts
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

`npm test` runs the contract, frontend and backend suites. Real-chain backend tests require MUD_LIVE_TEST=1 and an isolated local deployment; their default skip is explicit. Use MUD_TEST_DATABASE_URL for a disposable PostgreSQL test database. Never point fixtures at a customer database: tests create/drop projection tables.

## Explicit local testing only

```bash
MUD_SEED_FIXTURES=1 bash infrastructure/scripts/local-up.sh
npm run lifecycle
```

This opt-in creates local credentials from `.env.local.example` and uses samples under `tests/fixtures`. Mock collateral, sample goods and test wallets have no financial value. Fixture seeding is forbidden outside chain 31337. Existing environment files/databases are preserved; follow [deployment guidance](docs/DEPLOYMENT.md) for a fresh test environment. Public builds require NEXT_PUBLIC_ALLOW_TEST_NETWORKS=true to display an explicitly chosen test deployment, which remains labelled as test data.

## State and economics

Outstanding ERC-20 supply drives the shared discrete reserve potential. All burns reduce liability; there is no unbacked genesis mint. The AMM must retain collateral covering gross liability plus accrued fees. Only accrued fees can be collected by the treasury.

Marketplace payments send 95% to the merchant and burn 5%. The burn is not platform income. Conversion uses manipulable marginal MUD pricing and a validated collateral/USD feed; it is not a guaranteed liquidation value. Default buy fee is zero; default exit fee is 0.5%. Credentials do not guarantee demand or profit.

Source: `contracts/src`, `backend/app`, `frontend`, `infrastructure` and `scripts`. See [economic model](docs/ECONOMIC_MODEL.md), [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [verification evidence](docs/VERIFICATION.md), [recovery](docs/INCIDENT_RESPONSE.md) and the generated [file manifest](docs/MANIFEST.md).

`python3 scripts/manifest.py` builds the clean ZIP and complete source-content Markdown in the parent outputs directory. Installed dependencies, credentials, runtime databases, operator-owned deployment manifests and eligibility inputs are excluded.
