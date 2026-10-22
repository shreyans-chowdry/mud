# Credentials for a real Base deployment

API credentials connect infrastructure. They do not create users, sales, collateral backing or guaranteed profit. This repository has no deployed live MUD contracts or real goods configured. It displays unavailable values until a verified deployment is supplied.

| Item | Obtain from / configure | Variable or use | Secret? |
|---|---|---|---|
| Server Base RPC HTTP + WebSocket endpoints | An RPC provider such as Alchemy; enable Base mainnet | MUD_RPC_HTTP, MUD_RPC_WS | Treat provider credentials as server secrets |
| Browser Base RPC endpoint | A separate provider app with domain restrictions and quotas | NEXT_PUBLIC_BASE_RPC | Public browser credential; never reuse a privileged server key |
| Hosted PostgreSQL connection URL | Your database host; use TLS per its connection instructions | MUD_DATABASE_URL | Yes |
| Hosted Redis connection URL | Your Redis host; use TLS per its connection instructions | MUD_REDIS_URL | Yes |
| Fulfillment signing secret | Generate randomly; configure the same value in sender and your merchant receiver | MUD_WEBHOOK_SECRET | Yes; at least 32 random characters |
| Real delivery service credentials | The product/service you actually sell, configured only in your merchant receiver | Provider-specific; no generic delivery integration is claimed | Usually yes |
| Contract owner, guardian, treasury administration | Your reviewed wallet/multisig setup | PROTOCOL_OWNER, PROTOCOL_GUARDIAN and contract ownership | Addresses public; signing keys private |
| Deployment signing key | Your secure deployment signer; needs Base ETH for gas | DEPLOYER_KEY only in the deployment session | Yes; not an API key; never put in website/worker runtime |
| Explorer API key | The explorer's verification service, if automating source verification | Separate release tooling; not consumed by current runtime | Yes; optional for runtime |
| Hosting access | Your chosen always-on hosting service | Hosting dashboard/CI secret store | Yes; no universal hosting key |

You do **not** need an OpenAI API key, CoinGecko key, exchange trading key, Chainlink account key, or Stripe key for the implemented wallet-to-contract payment flow. Chainlink-compatible feeds are read through RPC; configuring their correct contract addresses is required. Card payments, email delivery, object storage and external services need their own integrations and credentials only if you add those features. No unused provider key fields have been added.

Generate a webhook secret with `python3 -c 'import secrets; print(secrets.token_hex(32))'` on your own computer, then save it directly in your hosting secret manager. Do not paste secret values into this chat, commit them, or put them in NEXT_PUBLIC variables. NEXT_PUBLIC values are embedded in downloaded browser JavaScript.

The mainnet collateral address and oracle addresses are public configuration, not API keys. Select Base addresses from the official registries, then verify their code, decimals and feed behavior before deployment. Do not copy an address from a test network or assume a mock token is USDC.

Revenue currently comes from merchant sales in MUD and configured AMM fees. Default buy fee is zero; default exit fee is 0.5%. The marketplace's 5% burn is not platform income. Customer collateral remains backing, and only accrued fees may be collected by the treasury. Real delivery, customer demand, costs, taxes and independent security review are still necessary.

Official references, checked October 22, 2026:
- [Alchemy API key and endpoint setup](https://www.alchemy.com/docs/create-an-api-key)
- [Alchemy browser/domain and server/IP restrictions](https://www.alchemy.com/docs/how-to-add-allowlists-to-your-apps-for-enhanced-security)
- [Circle official USDC addresses](https://developers.circle.com/stablecoins/usdc-contract-addresses)
- [Chainlink Base feed directory](https://docs.chain.link/data-feeds/price-feeds/addresses?network=base)
- [Chainlink sequencer uptime feeds](https://docs.chain.link/data-feeds/l2-sequencer-feeds)
