import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
export default defineConfig({plugins:[react()],resolve:{alias:{'@':fileURLToPath(new URL('.',import.meta.url))}},test:{environment:'jsdom',include:['tests/**/*.test.{ts,tsx}'],setupFiles:['./tests/setup.ts'],coverage:{provider:'v8',include:['lib/format.ts','components/Wallet.tsx','components/BondingCurveSwap.tsx','components/OrderTracking.tsx','components/MarketplaceCheckoutModal.tsx']}}});
