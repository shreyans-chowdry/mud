# Reproducible development and deployment

Use Node **22** (Docker pins 22.23.3), Python 3.11+ (verified 3.12.4; image pins 3.12.10), npm and Docker Compose v2. Network access is needed only to install/build dependencies and contact configured RPCs. Direct dependency versions and complete npm/Python lockfiles are committed. Use `npm ci`, not an unreviewed install/update, for reproduction. solc-js 0.8.24 is resolved locally; compiler downloads are not required. Build caches are scoped to ignored runtime/tool-cache so the toolchain does not need home-directory writes.

## One-command local stack

From repository root:

```bash
MUD_SEED_FIXTURES=1 bash infrastructure/scripts/local-up.sh
npm run lifecycle
```

The script generates ignored random LOCAL credentials, starts chain/PostgreSQL/Redis, installs locked dependencies, compiles/exports ABI, constructs the deterministic eligibility fixture, deploys fresh local contracts and seeds backed airdrop + three listings, then builds/starts API, workers, local fulfillment, frontend and monitoring. It needs a working Docker daemon. It does not broadcast outside chain 31337. Wait for API readiness before running lifecycle. Services: terminal http://127.0.0.1:3000, OpenAPI http://127.0.0.1:8000/docs, health http://127.0.0.1:8000/ready, Prometheus http://127.0.0.1:9090. Exposed host ports bind loopback. If native PostgreSQL/Redis already use 5432/6379, set MUD_POSTGRES_PORT and MUD_REDIS_PORT to free host ports. Container connections still use internal postgres:5432 and redis:6379; update MUD_DATABASE_URL/MUD_REDIS_URL for host-run tools to match the chosen host ports. Verification used 55433/16380 and preserved the existing host database services.

`local-up.sh` deploys new contracts on every invocation. Stop workers before redeploying, or use a fresh stack; do not point an old order database at a new manifest. Restarting an ephemeral chain while retaining PostgreSQL is a new deployment/environment, not a meaningful production reorg. Preserve old audit data separately. `docker compose --env-file .env -f infrastructure/docker-compose.yml down` stops services. It retains database volumes; removing volumes is deliberately not the default.

## Individual commands

```bash
npm ci
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
backend/.venv/bin/pip install --no-deps -e backend
npm --prefix frontend ci
python3 scripts/init-local.py
npm run compile
backend/.venv/bin/python scripts/generate_merkle_tree.py tests/fixtures/eligibility.dataset.json tests/fixtures/eligibility.local.json
backend/.venv/bin/python scripts/verify_merkle_tree.py tests/fixtures/eligibility.local.json
```

Start one local chain (`CHOKIDAR_USEPOLLING=true npm run chain`), then `npm run deploy:local`. Poll readiness rather than assuming startup timing. The deployment output contains actual addresses, chain ID, start block, ABI version and confirmation policy. It writes deployments/31337.json and frontend/public/deployment.json. Generated local addresses in the distributed source are evidence of a development run, not deployed live-network addresses. Always regenerate on your own fresh chain.

For host-native services, start PostgreSQL 16 and Redis 7 on loopback, load `.env` through your process manager, then run:

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
backend/.venv/bin/python -m app.workers.indexer
backend/.venv/bin/python -m app.workers.outbox_worker
backend/.venv/bin/uvicorn app.fulfillment:app --host 127.0.0.1 --port 8001
npm --prefix frontend run build
npm --prefix frontend start
```

The editable Python package makes `app` importable from root. Alternatively set MUD_RUN_WORKERS=true in a **single** API process and omit the separate workers; do not combine both patterns. Dedicated worker CLIs expose their own metrics. Frontend .env.local can be copied from frontend/.env.example; only NEXT_PUBLIC values reach the browser. Do not insert backend secrets there.

SQLite may be selected explicitly via MUD_DATABASE_URL=sqlite+aiosqlite:///absolute/path.db and MUD_REDIS_URL='' for a single-process local smoke run. It is not the PostgreSQL deployment and does not verify multi-worker row/advisory locking. The checked verification report identifies which database was actually used.

## Wallet acceptance

Use an isolated development browser profile and local chain 31337, RPC http://127.0.0.1:8545. A wallet must support an injected EIP-1193 provider; WalletConnect/permit are intentionally not advertised. Hardhat's local accounts are public development accounts and must never hold live funds. No private key is embedded in the client or source. Import a local-only account using your own dev tool's displayed credentials if testing manually. The seeder funds account #1 with mock collateral. The browser test adapter instead forwards to unlocked **local** RPC accounts, rejects non-31337 RPCs and contains no key.

Run `npx --prefix frontend playwright install chromium` if your package-manager version supports it; universally, `cd frontend` then `npx playwright install chromium`. With API/chain running and frontend built, `npm --prefix frontend run test:browser` launches or reuses the terminal server and exercises rejection, network switching, actual approval/buy, signed checkout and fulfillment. Run the tests sequentially against a disposable chain/database. The test suite does not access a real wallet.

## Base / Arbitrum testnets

Supported configs are chain 84532 and 421614; manifests for 8453 and 42161 define intended production policies but default scripts refuse mainnet broadcasting. Obtain RPC endpoints and independently reviewed collateral, price feed and sequencer feed addresses for the selected chain. Do not assume cross-chain identity. Provide EXPECTED_CHAIN_ID, PROTOCOL_OWNER, PROTOCOL_GUARDIAN, COLLATERAL_ADDRESS, ORACLE_FEED, SEQUENCER_FEED, ORACLE_MAX_AGE and MERKLE_FILE. Supply DEPLOYER_KEY only via an authorized secret environment. Economic overrides BASE_PRICE, SLOPE, MAX_SUPPLY and MAX_TRANSACTION are integer atomic units within enforced bounds. Custom token name/symbol require no business-logic edits.

The remote deployment preflight checks chain, addresses, code and collateral precision; constructor/feed checks may still fail and leave partial deployments. Review and simulate the entire deployment transaction sequence before broadcasting. The script requires an explicit Merkle dataset file before remote transactions. It does not automatically fund remote airdrops or list merchants. Purchase the genesis allocation through the AMM, then fund escrow and independently verify full backing before opening claims.

```bash
node scripts/hardhat.cjs run contracts/script/deploy.cjs --network baseSepolia
node scripts/verify-chain.cjs deployments/84532.json
backend/.venv/bin/python scripts/validate_deployment.py
```

The final command uses MUD_CHAIN_ID, MUD_RPC_HTTP and its corresponding manifest; set them for the selected environment. Network RPC deployment variable BASE_SEPOLIA_RPC is distinct from backend MUD_RPC_HTTP and browser NEXT_PUBLIC_BASE_SEPOLIA_RPC. For Arbitrum use arbitrumSepolia and the corresponding variables. Testnet/prod backend settings require PostgreSQL, Redis, >=5 confirmations and >=64 block-depth finality. Configure separate databases and secrets per chain.

Explorer publication of verified source is a separate operation: this repository provides exact solc version/settings and complete source imports, but no explorer API credential or invented verification receipt. Record real verification URLs after the chain's explorer accepts your compiled standard JSON. No mainnet transaction was sent during implementation.

## Linux browser helper

When native Chromium cannot launch, `docker build -f infrastructure/Dockerfile.browser -t mud-browser-verification .` builds the pinned official Playwright image with native dependency build tools. With host chain/API/frontend running on ports 8545/8000/3000, run `docker run --rm --init -v "$PWD/runtime/browser-evidence:/evidence" mud-browser-verification`. A test-only TCP relay preserves localhost origins while reaching Docker Desktop host services. This helper is not an application deployment and never connects to a live chain. The corrected helper built and all four journeys passed; see VERIFICATION.md.
