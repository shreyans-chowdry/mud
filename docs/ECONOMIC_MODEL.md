# Monetary specification (ABI v1)

S is **total outstanding ERC-20 supply**, including airdrop escrow and merchant balances. There is no privileged genesis mint. Airdrops must be funded by a collateral-backed purchase. Curve-accounted supply equals totalSupply; circulating supply is reported with this definition, not a guess about free float. ERC20Burnable burns reduce S, including marketplace burns. No proxy or adjustable curve coefficients exist.

## Units and potential

W = 10^18; S is MUD atoms. Collateral has d decimals (6 initially, supported 6–18). P0 and k are collateral atoms per whole MUD and collateral atoms per MUD per sqrt(whole MUD), respectively. Bounds: 0 < P0 <= 10^18, 0 <= k <= 10^18; S <= 10^27. Additional k bound: k * maxSupply <= 10^33. This makes square-root approximation error < 0.000667 collateral atoms. Products S*W <= 10^45 and 2*k <= 2*10^18 cannot overflow uint256. All financial divisions use OpenZeppelin Math.mulDiv.

Continuous target: P(s)=P0+k sqrt(s), F(s)=P0*s+(2*k/3)*s^(3/2), with s in whole tokens. The on-chain **discrete reserve potential** is:

r(S)=floor(sqrt(S*W)) (sqrt(whole tokens) scaled by W)
t(S)=floor(S*r(S)/W) (whole tokens^(3/2) scaled by W)
V(S)=floor(P0*S/W)+floor(2*k*t(S)/(3*W)) (collateral atoms).

V is monotone and V(0)=0. Its distance below continuous F is less than 2 + 2*k/(3*W) + 2*k*maxSupply/(3*W^2) atoms (<2.668 atoms under enforced bounds). Interval discretization is explicitly V(S1)-V(S0), rather than independently rounding each interval. Both directions use the SAME potential, so errors telescope. Spot uses P0+floor(k*r(S)/W), in collateral atoms / MUD. A spot quote is NOT an integrated trade quote.

A bounded upper-midpoint binary search (at most 90 steps, supply <2^90) finds the greatest S1 <= cap with V(S1)-V(S0) <= net budget. The lower bound is feasible, upper bound decreases when infeasible, and termination returns a feasible maximum. The full net budget is deposited; any unspent atom dust is reserve surplus. A budget larger than the remaining potential to the supply cap is rejected, avoiding unlimited overpayment at the cap. Input must be positive, output must be positive, and zero gross redemptions revert. No zero-cost buy exists. Fee divisions round down. Redemptions transfer V(S)-V(S-x)-fee; the fee remains in reserve. Marketplace conversion rounds upward twice and transfers exactly the required payment; maxMudAmount is a cap, not an amount debited.

## Solvency invariant

B = actual collateral balance, A = accrued unwithdrawn fees, L = V(S). Required invariant B >= L + A. Net full-redemption liability is L-floor(L*exitFeeBps/10000), an estimate at a snapshot, not a promise of future execution. Economic price depends on S and immutable coefficients, not reserve donations or net fees. Buy adds net budget + buy fee; L rises by at most net budget. Sell reduces B by gross-fee, L by gross, increases A by fee. External burn decreases L while B and A stay fixed. Fee sweep decreases B and A equally and checks the post-transfer invariant. Donations increase surplus, which cannot be withdrawn. Gross coverage = (B-A)/L when L>0; undefined for zero liability. Reserve fees and treasury balances are separate.

For a no-burn closed trade cycle, sums of potential increases equal decreases, so collateral proceeds cannot exceed collateral inputs; all fees and rounding surplus favor reserves. With burns the trader destroys a claim and cannot increase aggregate proceeds. This is a reserve-asset solvency model, NOT USD solvency: collateral depeg changes purchasing power. Fee-on-transfer tokens are rejected by exact sender/recipient balance deltas. Rebasing tokens are unsupported; their behavior cannot be certified at runtime. A negative rebase makes reserve health fail and trading reverts. Only reviewed, non-rebasing collateral should be configured.

## Marketplace and oracle

Products store USD with 6 decimals. Chainlink-compatible collateral/USD answer is normalized to 8 decimals; supported feed precision is 1–18. Positive answer, round completeness, past timestamp, max age, and a configurable absolute range around $1 are enforced. This range is a circuit breaker, not a substitute for a trustworthy feed. L2 deployments require an uptime feed: sequencer up and >1 hour since restart. Local mocks are conspicuously local and manually settable; they never stand in for a real feed remotely.

For USD6 product price U and oracle Q (USD8 per whole collateral): collateral atoms = ceil(U*10^d*10^8/(10^6*Q)); MUD atoms = ceil(collateral atoms*W/spot). This is explicitly a **marginal reference conversion**, not a claim that liquidating those tokens produces U USD. It is manipulable through changes in outstanding supply and transaction ordering. Merchants accept this model; buyers set max payment and a deadline. Mainnet review should decide whether to replace it with independent MUD/USD price discovery or time-weighted pricing. A stronger claim of manipulation resistance is not made.

Merchant receives payment-floor(payment*500/10000); the remainder is genuinely burned using burn(), reducing totalSupply. No transfer tax exists. Inventory updates and nonce consumption precede transfers. Reverts roll back every effect.

## Privileges

Curve coefficients, collateral, supply cap, oracle feeds, treasury destination, and configuration contract are immutable. Config owner proposes bounded fee/transaction-limit updates, waits 48 hours, and executes. A guardian or owner can pause mint/redemption or marketplace purchasing; only owner unpauses. Transfers and voluntary burns remain available during pause. A treasury owner can collect accrued fees only and withdraw its own balance. Airdrop owner can replace the root only before the first claim and with no claim reset; after expiry it can recover remaining escrow. Use different multisigs for owners and guardian; ownership uses two-step transfer and renunciation is disabled on operational contracts.
