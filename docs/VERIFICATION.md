# Verification status

## October 22, 2026: public real-data configuration changes

The latest public build has no deployed protocol manifest or sample catalog. It does not display historical test values as current data. New checks cover test-network rejection, mismatched API/module addresses, stale cached sample suppression, remote environment validation and unavailable eligibility. Current local results: **16 contract tests passed; 25 frontend tests passed; 18 backend tests passed and 2 real-chain tests skipped** (no test chain supplied). TypeScript, ESLint, Ruff, shell syntax and the production frontend build passed. Selected execution logs are in docs/evidence/live-data-*. The blank production template correctly fails the read-only preflight with missing configuration fields. Production frontend build and production Compose configuration validation passed. Initial remote CI run 39770603090 failed before tests because GitHub runner parsing rejected the single-quoted PostgreSQL health check. The workflow now uses double quotes; its rerun result must be checked separately. No mainnet transaction or live deployment was made, and no Codex Cloud coding task is claimed started.

Historical local acceptance below describes the earlier explicitly seeded test environment. It is evidence of executed behavior, not current balances, listed real goods or production readiness. New code still requires its current checks; historical browser results must not be represented as a rerun of the new public build.

## Historical local acceptance evidence and production release blockers

This report distinguishes actual executions from supplied workflows. Results below were obtained on the local development chain 31337. No testnet/mainnet transaction was broadcast. Financial custody readiness is **not established**.

## Executed successfully

| Check | Observed result |
|---|---|
| Solidity compilation | 34 Solidity files compile with pinned solc 0.8.24; Paris EVM target, optimizer and viaIR |
| Smart-contract coverage suite | **16 tests passed**, including seeded fuzz, 30 one-atom cycles, nonzero-supply inversion and 70 stateful buy/sell/burn transitions |
| Solidity coverage | 94.06% lines, 95.97% statements, 50.33% branches, 87.72% functions over owned source excluding mocks |
| Backend on SQLite | **16 tests passed**, including actual local-chain backfill and actual snapshot/revert reorganization |
| Backend on PostgreSQL | **16 tests passed** against PostgreSQL **16.15** in the locally available postgres:16-alpine container, isolated disposable test DB |
| Backend coverage with PostgreSQL | About **79% statements** (1006 statements, 207 missed) over app modules |
| PostgreSQL migration | Alembic upgrade through 0003 succeeded; SQLite upgrade/downgrade/re-upgrade and metadata check passed |
| Frontend unit tests | **17 tests passed** across decimal math, canonical order constraints, wallet/network boundaries, swap validation/rejection, receipt states and order failures |
| Frontend coverage | 57.69% lines/statements over selected financial components; checkout modal remains uncovered by unit execution |
| Frontend type checking / lint | TypeScript noEmit and ESLint max-warnings=0 passed |
| Frontend production build | Next.js **15.5.28** build passed; all required routes emitted |
| Python static checks | Ruff and compileall passed |
| Merkle utilities | Generator plus independent root/proof/dataset-hash verifier agreed on deterministic local fixtures |
| Docker Compose stack | Complete image builds and fresh startup passed; 9 services running, migration 0003 complete, API/chain/PostgreSQL/Redis healthy |
| Monitoring | All three Prometheus scrape targets (API, indexer, outbox) were up |
| Fresh contract deployment | Local deployment succeeded with Hardhat **2.29.1**, explicit Cancun hardfork and 30M block gas limit |
| Contract-link validation | Chain ID, deployed bytecode, linked modules, collateral decimals, root, oracle validity and reserve health passed |
| Local purchase lifecycle | Actual approval, mint, redemption, valid claim, repeated-claim rejection, product settlement, merchant balance delta, supply burn, indexed order and signed webhook acknowledgment reached **FULFILLED** |
| Browser preview | The rebuilt terminal was opened in the in-app browser; live supply/reserve/oracle data and a live integrated buy quote were observed |
| Python dependency scan | pip-audit over the final lock reported **no known vulnerabilities** at scan time |
| Frontend production dependency scan | **0 high, 0 critical; 21 moderate** findings at scan time |
| Solidity development dependency scan | **7 high, 11 moderate, 10 low** transitive/development-tool findings remain; release security gate intentionally reports them |

The initial lifecycle used SQLite and included the actual genesis claim. It is retained in docs/evidence/lifecycle-sqlite.json. A subsequent native HTTP lifecycle ran on PostgreSQL 16.15 + Redis. The final run deployed a fresh chain inside the complete Compose stack using pinned PostgreSQL 16.8 + Redis 7.4.3, separate indexer/outbox containers, API, receiver and frontend, and reached FULFILLED with an actual genesis claim. Actual block-log replay preserved 20 event rows, and two duplicate signed webhook requests retained exactly one receipt and one entitlement for that order. See evidence/postgres-integration.json. A custom-format pg_dump was restored with pg_restore --no-owner --exit-on-error into an isolated database; the same settlement/replay verification passed on that restored database, at schema head 0003, including verified transition sequences [1,2,3,4] (evidence/restore-verification.json).

Reports contain real local development hashes, not explorer links to a live network. The local receiver records an entitlement, not delivery of external goods. New regressions cover expired attempt acknowledgments, re-inclusion without duplicate entitlements, late old-block compensation, and compensation arriving before an orphan confirmation. Migration 0003 adds a persistent transition sequence; same-second state history ordering is tested across sessions and the HTTP endpoint. Legacy ambiguous sequence values remain null. Test settings are isolated from the runtime Redis rate bucket.

## Browser automation: passed on Linux

All **4 Playwright journeys passed** in the pinned Playwright 1.56.1 Linux container against the complete Compose stack (11.3 seconds): desktop/mobile real dashboard without document overflow; wrong-network switching, disconnect and reconnect; rejected approval followed by actual approval and mint; marketplace approval, buyer EIP-712 signature, actual payment receipt, finalized indexed order and FULFILLED tracking. Screenshots and HTML report are retained under runtime/browser-evidence. Browser test selectors were corrected to distinguish header wallet controls from trading controls and wait for asynchronous order preparation.

The native macOS launch failed before page execution; Linux browser execution resolved that environment limitation. The corrected helper installs native build tools. No real wallet or live funds were used: a test-only EIP-1193 provider forwards to unlocked chain-31337 accounts and rejects live RPCs.

## Supplied but not executed end to end

- Remote CI workflow, actual testnet deployment, explorer source publication, production feed configuration, cloud continuation and mainnet release.
- Fault schedules such as killing an outbox process precisely after external fulfillment but before acknowledgment, multi-process load, L1 finality/reorg semantics and production key management.

## Security status

Slither 0.11.3 completed 100 detectors over 36 contracts: **0 high, 2 medium, 10 low** findings. See STATIC_REVIEW.md and evidence/slither.json for unsuppressed findings and engineering triage. This is not an independent audit.

Next.js was updated within the requested major to the patched 15.5.28 release, consistent with the [official October 2026 security update](https://nextjs.org/blog/nextjs-security-update-october-14-2026). Sharp, PostCSS, ws and several Solidity-tool transitive dependencies were pinned to available fixes. FastAPI/Starlette and pytest were updated after Python advisories were found. Functional checks were rerun after those changes.

Development-tool findings include the braces/globbing/coverage/Mocha dependency chain. They remain visible rather than being suppressed or “fixed” by an unsafe incompatible downgrade. Dependency scans are point-in-time registry reports, not a guarantee about unknown defects. Independent professional smart-contract, economic and application review remains required before any real-fund deployment. See THREAT_MODEL.md for the complete privilege and assumption checklist.

## Delivery and remaining release work

All requested local acceptance flows have execution evidence. The clean source archive, complete source-content bundle and browser evidence archive are generated beside this repository. The refreshed Desktop delivery is in /Users/shreyanschowdry/Desktop/MUD Protocol/Delivery-2026-10-18-115922. Copied artifact hashes and every extracted source file were verified; earlier Desktop contents were preserved.

Remote CI has not run here. Remaining real-fund release blockers are development-tool dependency advisories, independent professional contract/economic/application review, official external feed/collateral configuration, production key management, L1-aware finality and infrastructure hardening. The supplied CI keeps independent scans running after another security gate fails; it does not suppress the failure. Cloud execution while the Mac is off is not configured.
