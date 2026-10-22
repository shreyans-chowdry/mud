# Tested properties and why they matter

| Property | Test evidence | Meaning / limit |
|---|---|---|
| Greatest affordable integrated output | protocol.cjs independently recomputes V(x)<=budget<V(x+1) | Guards inverse-quote over-mint and accidental spot-price division |
| Roundtrip cannot print collateral | 40 seeded fast-check amount trials | Shared potential telescopes; fees/rounding cannot benefit trader in tested range |
| Reserve conservation through burns | 70 stateful buy/sell/burn steps | B>=V(S)+fees and supply changes reconcile after every operation |
| Redemption burn/payout | Independent before/after balances and quoted gross/fee | Transfer success alone does not establish correct payout |
| Boundaries and protections | Zero, dust, cap, over-redemption, slippage, deadline | Invalid values revert rather than silently producing misleading trades |
| Hostile collateral | Tax, transfer failure, confiscation, callback mocks | Rejects measurable unsupported semantics; cannot certify future issuer behavior |
| Treasury privilege | Unauthorized collect/withdraw and fee reconciliation | Admin fee collection cannot intentionally consume curve backing |
| Admin config/pause | 48h delay, fee caps, ownership acceptance, guardian boundaries | Limits tested privileged actions, not key compromise |
| Merkle correctness | Double hash leaf, invalid account/amount/index, replay, funding and expiry | Membership/bitmap safety; does not test Sybil screening |
| Settlement | Buyer balance, exact merchant amount, burn delta, ItemPurchased | Proves actual totalSupply reduction and retained reserve coverage |
| Signature replay | Wrong domain chain/contract, stale nonce, repeated order | Authorization is bound to actual deployment and constraints |
| Oracle correctness | Stale/future/zero/negative/depeg/incomplete rounds and uptime grace | Rejects bad reference snapshots; not protection against all economic manipulation |
| Merchant containment | Owner block followed by attempted re-registration | Deactivation cannot be bypassed by the same merchant self-registering |
| Event identity | Two logs from same tx, replay and worker restart | Unique chain+tx+log key preserves distinct events without duplication |
| Reorg rollback | Simulated fork plus actual Hardhat snapshot/revert/mine | Hash reconciliation retains orphan evidence and rolls back payment projections |
| Finality/outbox | Increasing depth, one outbox record, compensating deep reorg | Delivery waits for policy; block depth is not L1 finality |
| RPC/WS outages | Failed read rolls back batch; failed subscription reconnects/backfills | No checkpoint is committed for incomplete data |
| Orders | Concurrent preparation, unique IDs, typed-data recovery/domain tamper | No off-chain nonce reservation or backend signature is mistaken for settlement |
| Webhooks | HMAC tamper/window, retry request IDs/stable key, durable receiver duplicate | Acknowledgment loss, expired leases, re-inclusion and reordered compensation preserve one local entitlement and fence stale results |
| API | Schema, uint256, request limits, rate guard and health | Anonymous intents cannot write payment status |
| Client financial constraints | Large exact decimal parsing, rounding, stale quote, min output/deadline, wrong chain, rejection/pending receipts | Unit tests assert user-visible safety boundaries without inventing receipts |
| Browser journey | Playwright test source covers actual local injected approval/buy/order/fulfillment | All four journeys passed in the official Linux Playwright container |

Contract coverage includes all owned source excluding mocks. Branch coverage is materially lower than line coverage: constructor rejection combinations, every administrative revert, and extreme parameter combinations need broader fuzzing and independent review. Backend coverage is measured over app modules, including RPC adapter, API, workers and receiver; not every network/process-failure schedule is covered. Frontend V8 coverage is intentionally limited to financial utility/wallet/swap/checkout/order components and exposes untested checkout lines. Do not interpret uncovered code as safe, or unit mocks as a replacement for browser acceptance.
