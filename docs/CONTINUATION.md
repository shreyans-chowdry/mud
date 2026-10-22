# Durable continuation record

## Active checkpoint — October 22, 2026

The original local implementation and Desktop delivery were completed October 18. The user subsequently requested Base, removal of public demo data, real configuration guidance, and coding that can continue with the Mac off. Current source is saved here; preserve user edits. Read README.md, docs/VERIFICATION.md, docs/LIVE_SETUP.md and docs/API_KEYS.md before changing it. No mainnet transaction is authorized.

Latest changes: public builds start without a deployment, reject test networks by default, verify API/chain/module agreement and suppress stale sample values. Eligibility is unavailable when no real dataset is configured. Test fixtures are isolated under tests/fixtures and require explicit local seeding. Base production Compose, read-only configuration/manifest checks and cloud setup/handoff instructions are supplied. Operator credentials and deployment metadata are excluded from distribution.

Current executed checks: 16 contract tests passed; 25 frontend unit tests passed; 18 backend tests passed, 2 real-chain tests skipped because no test chain was supplied. Frontend type checking, ESLint, production build, Ruff and shell syntax checks passed. These results do not establish mainnet readiness. Historical full-stack/browser/reorg evidence in VERIFICATION.md belongs to the October 18 local build; it has not been rerun for the new public build. Development dependency advisories and independent review remain release blockers.

GitHub repository: https://github.com/shreyans-chowdry/mud . Authenticated user has push access; repository was empty at the October 22 pre-push check. Publication and remote CI results must be recorded when actually completed. A local GitHub login does not start cloud AI execution. No Codex Cloud task has started. Follow docs/CLOUD_HANDOFF.md to create and publish a Cloud environment and start a task. GitHub Actions runs verification remotely; it is not autonomous AI development. The local heartbeat must stay paused. Neither local tasks nor local automations continue with the Mac off or bypass usage limits.

Clean package command: python3 scripts/manifest.py . Never include .env files, signing keys, node_modules, databases or runtime logs. Operator manifests and eligibility inputs are excluded; test-only fixtures remain available for verification. Preserve older Desktop deliveries. A new Desktop delivery needs filesystem authorization for /Users/shreyanschowdry/Desktop/MUD Protocol and should use a dated child folder.

## Historical checkpoint (October 18; runtime state may have changed)

# Durable continuation record

Request: implement the complete $MUD protocol from the attached specification, then place a clean deliverable in a Desktop folder named `MUD Protocol`.

Repository source is in this folder. README contains setup commands; docs/VERIFICATION.md records actual evidence and unresolved checks. Never restart from snippets, invent a passing test, or replace the arithmetic model without reading docs/ECONOMIC_MODEL.md. Source edits precede regenerated ABI, tests, package manifest and source bundle. No mainnet transaction is authorized by the default workflow.

If a usage limit interrupts a run, resume by reading this record, VERIFICATION.md and the latest chat. Inspect actual files and logs under ignored runtime/ before deciding which checks need repeating. Keep user changes. The environment may no longer have running local services; start only the services needed for a specific check. Runtime databases, node_modules, private .env and virtual environments are not distribution artifacts.

Cloud continuation is not configured. This checkout and Desktop live on the user's Mac; they are unavailable when the machine is off. Available handoff tooling does not migrate this running chat to cloud. A cloud worker would need an explicitly connected environment with this source and dependencies. Do not claim a local heartbeat can work while the laptop is off or bypass account usage limits. Current official guidance says tasks needing local files require the computer and app to remain running: https://developers.openai.com/training/walkthroughs/scheduled-tasks .

Desktop delivery must copy the clean packaged source and user-facing reports, excluding secrets, caches, installed dependencies, live databases and development-account key logs. Request narrowly scoped filesystem access to `/Users/shreyanschowdry/Desktop/MUD Protocol` only when the deliverable is concrete and ready. Preserve any existing Desktop contents; if a folder already exists, use a new dated delivery subfolder rather than overwrite it.

## Latest checkpoint

User requests continuation whenever capacity returns and says they are closing the laptop. Keep the heartbeat disabled after this completed delivery; cloud continuation is not configured. Preserve that distinction.

Implementation and all requested local acceptance flows are verified. Contract suite: 16 passed; backend: 16 passed on both SQLite and PostgreSQL 16.15, including real chain reorg; frontend unit suite: 17 passed; Linux Playwright: 4 passed against the full Compose stack (11.3s). Complete Docker builds and fresh-chain deployment passed. PostgreSQL 16.8 + Redis 7.4.3 HTTP lifecycle reached FULFILLED, including actual claim, redemption, merchant transfer and burn. Actual event replay retained 20 rows; duplicate signed callbacks retained one receipt/entitlement. Custom pg_dump/pg_restore verification passed on schema 0003, with ordered history [1,2,3,4]. All three monitoring targets are up. Slither: 0 high, 2 medium, 10 low, triaged in STATIC_REVIEW.md. Development dependency advisories remain real-fund release blockers, not a reason to rerun finished local implementation indefinitely.

New receiver safeguards: fenced lease acknowledgments, one entitlement per order, re-inclusion handling and retained compensation receipts prevent late orphan confirmations from activating delivery. Migration 0002 adds entitlements; 0003 adds persistent transition counters so same-second history remains ordered without fabricating legacy sequence values. All migrations/checks passed.

Implementation, packaging and refreshed Desktop delivery are complete. The new dated folder is /Users/shreyanschowdry/Desktop/MUD Protocol/Delivery-2026-10-18-115922. Archive integrity, copied artifact hashes and every extracted file were verified. Earlier Desktop contents were preserved. Source archive, full-content Markdown and selected browser evidence are also in the parent outputs directory. Pause heartbeat resume-unfinished-mud-build; do not rerun completed work unless the user requests changes or a new failure justifies it.

Runtime: complete Compose stack mud-local is running; app ports 3000/8000/8001/8545 and Prometheus 9090. Native unrelated PostgreSQL/Redis already occupy 5432/6379 and must not be stopped. Compose host overrides are MUD_POSTGRES_PORT=55433 and MUD_REDIS_PORT=16380; internal container ports are unchanged. Use these overrides for Compose commands. Task-scoped DOCKER_CONFIG=runtime/docker-public and BUILDX_CONFIG=runtime/buildx avoid unavailable host keychain and protected home cache writes. Never alter user Docker config. Old task-owned native app processes have been stopped through their original execution sessions; do not kill arbitrary processes by port.

Latest reports: runtime/lifecycle.json, postgres-integration.json, restore-verification.json, browser-tests.log, compose-health.json and compose-monitoring.json. Corresponding selected evidence is distributed in docs/evidence. Earlier native evidence is preserved in runtime/native-*.json and original SQLite claim evidence in docs/evidence/lifecycle-sqlite.json. Task-owned temporary verification containers mud-verify-postgres/mud-verify-redis are separate on 55432/16379 and can be stopped after final delivery; the Compose database volume must be retained. Do not distribute .env, dumps, chain logs, private credentials, node_modules or runtime databases.
