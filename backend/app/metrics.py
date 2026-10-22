from prometheus_client import Counter, Gauge

INDEXER_LAG = Gauge('mud_indexer_lag_blocks', 'Observed head minus committed indexer checkpoint')
RPC_FAILURES = Counter('mud_rpc_failures_total', 'Indexer RPC failures')
CACHE_AGE = Gauge('mud_cache_age_seconds', 'Age of most recently returned cache entry')
ORDER_TRANSITIONS = Counter('mud_order_transitions_total', 'Durable order state transitions', ['state'])
WEBHOOK_RETRIES = Counter('mud_webhook_retries_total', 'Webhook delivery failures')
REORGS = Counter('mud_reorganizations_total', 'Canonical reconciliation operations')
FAILED_TRANSACTIONS = Counter('mud_failed_transactions_total', 'Reverted submitted transactions reported by receipt endpoint')

INDEXER_HEARTBEAT = Gauge('mud_indexer_last_success_timestamp_seconds', 'Last successful canonical indexer commit')
OUTBOX_HEARTBEAT = Gauge('mud_outbox_last_poll_timestamp_seconds', 'Last successful outbox poll')
