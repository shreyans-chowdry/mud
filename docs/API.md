# HTTP API v1

Start FastAPI on port 8000. Open `/docs` for generated OpenAPI. Every financial integer is a decimal string; timestamps and bounded block/chain IDs are JSON integers. API data is a quote or projection, never authorization to spend funds. Error bodies are `{ "error": { "code", "message", "request_id" } }` with 4xx validation or 503 dependency failures. CORS accepts only configured exact origins. Requests have X-Request-Id and no-store caching. Rate limit uses the direct peer IP; proxy forwarding is disabled by default.

| Method and path | Input | Result |
|---|---|---|
| GET /api/v1/deployment | none | RPC-verified chain, environment, module addresses and data provenance for browser handshake |
| GET /api/v1/curve/spot-price | none | Chain, token/collateral, outstanding/accounted supply, reserves, price units, fees/liabilities, oracle validity, timestamp, block hash, cache age |
| GET /api/v1/curve/quote-buy | collateral_amount (positive collateral atoms) | Integrated MUD output, fee, curve cost, block snapshot, 15s display TTL |
| GET /api/v1/curve/quote-sell | mud_amount (positive MUD atoms) | Net collateral output, fee, gross potential reduction, block snapshot |
| GET /api/v1/airdrop/eligibility/{address} | nonzero address | Actual dataset membership, claim proof, dataset hash, chain-root match, expiry and claimed state |
| POST /api/v1/airdrop/verify-proof | address,index,allocation,proof | Dataset and on-chain-root verification, never syntactic-address eligibility |
| GET /api/v1/marketplace/products | cursor>=1,limit<=50 | Live on-chain listings and quote availability at a fixed block |
| POST /api/v1/marketplace/create-order | product_id,buyer,max_mud_amount,ttl_seconds (30–900) | Durable unsigned order with canonical EIP-712 data |
| GET /api/v1/marketplace/order/{id}/status | UUID | Payment projection, fulfillment state, typed intent and durable transition history |
| GET /api/v1/activity | limit<=100, optional address/before_block | Natural-key indexed events, including explicitly orphaned records |
| GET /api/v1/transaction/{hash} | real tx hash | Actual receipt status and confirmation count, or NOT_MINED |
| GET /health | none | Process alive |
| GET /ready | none | DB/migration table, RPC chain, deployed code and configured Redis verified |
| GET /metrics | internal scrape | Prometheus process metrics; indexer/outbox CLI expose ports 9101/9102 |

Example order request:

```json
{"product_id":"1","buyer":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8","max_mud_amount":"100000000000000000000","ttl_seconds":300}
```

Buyer signs `Order(bytes32 orderId,uint256 productId,address buyer,uint256 maxMudAmount,uint256 deadline,uint256 nonce)` under name `MUD Marketplace`, version `1`, configured chain ID and marketplace contract. Buyer calls purchaseOrder with that message/signature after allowance approval. Backend does not sign or custody user keys. Multiple intents can share the current on-chain nonce; only the first can settle. Signatures are not saved by the API. Anonymous intent creation is rate limited; it conveys no fulfillment entitlement.

Lifecycle: CREATED → AWAITING_PAYMENT → PAYMENT_OBSERVED → CONFIRMED → FULFILLED. FULFILLMENT_RETRY / FULFILLMENT_FAILED distinguish merchant delivery failures. EXPIRED and REORGED are explicit. On-chain event state can supersede an off-chain expiry projection if a valid transaction was mined before its deadline. History includes an order-local sequence counter, so transitions in the same second remain in commit order. Migration 0003 preserves unknown legacy sequences as null rather than inventing their chronology. The client cannot set status. An unsubmitted/reverted transaction is not a payment; a failed receipt is shown as failed by the client and receipt endpoint, not falsely associated with an arbitrary order ID.

Fulfillment outbox is created only after FINALIZED depth policy. HMAC header is `v1=hex(HMAC-SHA256(secret, timestamp+'.'+requestId+'.'+idempotencyKey+'.'+rawBody))`. JSON body encoding is sorted keys, compact separators, UTF-8. Headers: X-Mud-Timestamp, X-Request-Id, Idempotency-Key, X-Mud-Signature. Verify signature before JSON parsing or effects. Enforce ±300s replay window, then atomically deduplicate key/payload with actual fulfillment. Respond 2xx only after committing effects. Retries reuse the key; request ID and timestamp change. A lease attempt number fences acknowledgments, so an expired attempt cannot overwrite a newer delivery result. Non-2xx and timeouts retry up to configured attempts with exponential backoff capped at one hour. Redirects are not followed. A timed-out success can be resent; the receiver must deduplicate.

A reorg after delivery queues payment.reorged; receivers must treat it as a review/compensation event. The local receiver keeps one entitlement per order, protected by a PostgreSQL advisory transaction lock, plus separate notification receipts. Re-inclusion updates that same entitlement; compensation carries the former block hash so a late notification cannot invalidate a newer settlement. Retained compensation receipts also prevent activation when an orphan confirmation arrives after its compensation. Migration 0002 adds this table. This record is not a claim that external digital content was delivered. Webhook destinations are operator configuration, never a client-provided URL.

When no operator eligibility dataset is configured, eligibility/proof endpoints return 503 with an explicit unavailable message. They do not claim the address is ineligible or silently read test fixtures.
