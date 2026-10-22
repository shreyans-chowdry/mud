# Threat model and independent review checklist

Status: implemented development system. **Not independently audited, certified, or approved for real funds.** Compiler/tests establish only the properties they exercise. See VERIFICATION.md for actual outcomes and remaining coverage.

Threat actors include arbitrary token holders, malicious collateral issuers, buyers/merchants, MEV searchers, compromised owner/guardian keys, RPC/feed operators, infrastructure administrators, malicious API clients, and an attacker with database write access. Web and backend are not trusted to authorize money movements; on-chain signatures, balances, deadlines, and caps enforce them.

| Attack surface | Mitigation implemented | Residual assumption / independent review |
|---|---|---|
| Reentrancy through collateral, token or merchant | ReentrancyGuard, state changes before external transfers, exact deltas, reverting subcalls | Malicious callback mock exercises AMM; audit entire call graph |
| Overflow / bad decimals | uint256 bounds, integer sqrt, full-precision mulDiv, decimals checked 6–18 | Parameter bounds intentionally restrict usable slopes at high decimals |
| Rounding arbitrage | Shared monotone discrete potential, binary search feasible maximum, positive inputs, reject zero gross refunds | Independently prove potential/error bounds and fuzz across full supported parameter space |
| Cap overpayment | Reject net budgets larger than remaining curve potential | User quotes can still shift before inclusion; min output/deadline enforced |
| Reserve insolvency | B >= V(S)+fees pre/post trade and fee collection | Collateral issuer can freeze or negatively rebase; no algorithm prevents that |
| Supply desynchronization | All burns reduce totalSupply; V(totalSupply) computed live, no stale issued-supply counter | Positive surplus cannot be withdrawn by admin |
| Oracle manipulation / depeg | Positive complete rounds, precision normalization, max age, immutable absolute deviation band | Feed operator and market quality trusted; reference range can halt useful commerce |
| Sequencer downtime | Uptime status, valid start time, 1-hour recovery grace | Supported real feed addresses must be independently checked per chain |
| Malicious collateral | SafeERC20, incoming/outgoing exact sender+recipient deltas; tests for tax, failure and confiscation | Rebasing/reflection/blocklisted tokens are unsupported even if a particular transfer passes |
| Front-running / MEV / flash liquidity | Buyer min output/max payment and deadline, transaction simulation | Marketplace uses manipulable marginal MUD reference price; not TWAP/manipulation resistant |
| Merkle replay / encoding | Double-hashed ABI leaves, sorted pairs, index<10000, 40-word bitmap, immutable-after-first-claim root | Dataset governance and Sybil screening remain off chain; root owner trusted pre-first-claim |
| Underfunded genesis | No privileged mint, remaining-allocation funding check every claim | Reviewed manifest total must equal committed allocations |
| EIP-712 replay | Domain chain+contract+version, buyer signature, nonce, unique order ID, on-chain verification | Multiple pending intents may share nonce; first settlement invalidates others |
| API signing deception | Client checks domain, buyer, product, cap, deadline, order ID and canonical field schema before signing | Compromised distributed frontend can still lie; use reproducible releases |
| Compromised merchant | Owner can block re-registration and delist; buyer sees merchant address | Goods quality/delivery is a merchant trust decision; merchant metadata is untrusted text |
| Unauthorized admin | Ownable2Step, immutable curve/feeds, delayed bounded config, guardian pause-only | Owner can pause indefinitely; multisig operational discipline required |
| Event duplication / RPC reorg | Natural unique key, hash/parent validation, checkpoints, atomic rollback and retained orphans | RPC canonical chain assumed; deploy redundant RPC monitoring before funds |
| Outbox crash / duplicate delivery | Durable outbox in settlement transaction, leased retries, stable idempotency keys, delivery audit | Exactly once requires merchant DB transaction; compensating delivery cannot undo already consumed goods |
| Webhook spoofing / replay | HMAC over timestamp, request ID, idempotency key and exact body; constant-time verify, 5-minute window | Rotate shared secrets in coordinated release; local receiver is not production fulfillment |
| SSRF / redirects | Only operator-configured allowlisted webhook hosts, HTTPS outside local, no redirects, timeouts | Allowlist DNS must be controlled; use network egress policy against DNS rebinding |
| API abuse / rate evasion | Strict schemas, uint256 bounds, 64 KiB body limit, Redis fixed-window limiter, exact CORS origins | Trust no proxy headers by default; authenticated merchant APIs and edge limits are future hardening |
| DB inconsistency | Migrations, transaction locks, order history, outbox audit, no client status setter | DB admin can corrupt projections; reconcile against chain and protect backups |
| Key / secret leakage | Runtime-generated local secrets, ignored envs, no browser secrets, remote deploy key from environment only | Use hardware-backed signer or secret manager; current script does not integrate an HSM |
| Dependency compromise | Lockfiles, pinned direct versions, CI dependency audit and static analysis | Audit findings may block CI; never suppress them as proof of safety |

## Privileges and release boundaries

Use separate owner multisigs for config, marketplace, treasury and airdrop, and a separate guardian. Current deployment uses one configured owner for simplicity; transfer owners individually with acceptOwnership after deployment. Owner-only unpause, setMerchant, delist and treasury withdrawals have no built-in delay; route them through a reviewed timelock/multisig policy before production. Fee/transaction changes have an enforced 48-hour delay, immutable hard caps, one pending proposal. Curve, feed, collateral and supply bounds cannot change. Operational contracts disable renunciation so emergency recovery is not accidentally destroyed. There is no upgrade key.

## Mainnet blockers / reviewer checklist

- [ ] Independently review mathematics, square-root approximation bounds, gas costs at maximum binary-search range and all privilege paths.
- [ ] Run complete PostgreSQL concurrency, process-crash, migration/restore and Redis fault-injection suites in deployment infrastructure.
- [ ] Configure/verify real collateral, USD feed and sequencer feed from official per-chain registries; never copy local mocks or addresses across chains.
- [ ] Review supply manipulation of marketplace reference pricing and whether merchant policy requires TWAP or independent price discovery.
- [ ] Resolve all relevant dependency advisories; review transitive wallet packages and the frontend bundle.
- [ ] Commission an independent professional smart-contract audit, economic review and penetration test; resolve findings.
- [ ] Enforce HSM/multisig signing, admin timelock policies, minimal egress, TLS, authenticated operational endpoints and key rotation.
- [ ] Establish merchant dispute/refund policy and the business process for consumed goods after a deep reorg.
- [ ] Establish L1-aware finality semantics for Base/Arbitrum. Block depth alone is not an L1 finality guarantee.
- [ ] Conduct recovery drills, RPC failover and data-restoration exercises; verify alert delivery.

## Library and feed references

Constructor ownership explicitly calls Ownable(initialOwner), consistent with [OpenZeppelin 5 access control](https://docs.openzeppelin.com/contracts/5.x/access-control). Genuine supply reduction uses [ERC20Burnable](https://docs.openzeppelin.com/contracts/5.x/api/token/erc20). Feed checks and sequencer grace are informed by [Chainlink L2 sequencer guidance](https://docs.chain.link/data-feeds/l2-sequencer-feeds). These references do not constitute endorsement or audit of this implementation.
