# Incident response and recovery

1. Establish chain ID, affected deployment and last canonical block from an independent RPC. Preserve logs and backup database before modifying projections.
2. Guardian pauses AMM mint/redemption and marketplace purchasing when monetary correctness is uncertain. Owner is required to unpause. Do not publish new curve coefficients as a repair; they are immutable.
3. Stop outbox before indexer surgery. A payment may already have caused delivery: retain all delivery records, notify merchants through the established incident process and use compensating reorg notifications.
4. Compare reserve B, accrued fees A and V(totalSupply). A negative rebase/freeze is a collateral-issuer incident; pausing cannot restore collateral. Do not sweep donations or backfill reserves with invented values.
5. Resolve oracle validity and sequencer uptime from official sources. Feeds are immutable; wrong-feed configuration requires a new reviewed deployment. Local mock setters must never exist remotely.

## Database restoration

Use `bash infrastructure/scripts/backup.sh` for pg_dump custom-format backups. Test restores into an isolated database before an incident. Keep encrypted copies and access audit logs. For restoration, stop API, indexer and outbox, create a fresh database with the correct owner, and run `pg_restore --no-owner --exit-on-error --dbname=... backup.dump`. Never interpolate an untrusted path or put credentials in shell arguments; use a restricted PGPASSFILE. Run `alembic current` / `alembic upgrade head`, compare schema and checkpoints, verify chain ID, and reconcile before enabling outbox. Restore delivery/idempotency records, order-unique entitlements and transition counters together with orders; restoring old delivery state without merchant reconciliation can duplicate external effects.

## Indexer rewind

Stop all indexer/outbox instances for that environment. `python backend/scripts/recover.py --rewind-to BLOCK --acknowledge` marks later events orphaned, marks affected orders REORGED, cancels unsent outbox work and queues compensation for acknowledged/in-flight work. It retains order/delivery audit history. Restart indexer alone; it backfills from the rewound checkpoint and validates hash continuity. Inspect affected orders and external merchant state before restarting outbox. Do not delete orders or delivered outbox rows to resynchronize.

If the fork exceeds max_reorg_depth, automatic reconciliation stops. Select a verified common ancestor, increase the bound only with memory/RPC limits understood, or use explicit rewind. Expiring leases allow crashed outbox processes to retry after 60 seconds. Retry one exhausted delivery with `python backend/scripts/recover.py --retry-outbox OUTBOX_UUID --acknowledge` only after verifying the receiver is idempotent and checking canonical payment. This command never resets the receiver's deduplication records.

## Observability

Scrape API :8000/metrics, indexer :9101 and outbox :9102. Watch indexer lag, last-success time, RPC retries, quote cache age, order transition states, reverted-receipt observations and webhook failures. Each process owns its metrics; API counters alone do not describe separate workers. Structured logs expose error types/request IDs rather than secrets or arbitrary webhook response bodies. Configure external notification routing before production; sample Prometheus rules do not send notifications by themselves.

Rotate leaked signing/secret material through a documented key-management process; current webhook protocol supports one active shared secret, so coordinate receiver/sender restarts. Take incident notes, reproduce the fault with regression tests, and require independent review before unpausing financial operations.
