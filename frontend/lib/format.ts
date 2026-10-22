import { formatUnits, parseUnits } from 'viem';
export function parseAmount(input: string, decimals: number): bigint | null {
  if (!new RegExp(`^(?:0|[1-9]\\d*)(?:\\.\\d{0,${decimals}})?$`).test(input)) return null;
  try { const value = parseUnits(input, decimals); return value > 0n && value < 2n**256n ? value : null; } catch { return null; }
}
export function amount(value: bigint | string | undefined, decimals=18, places=4): string {
  if (value === undefined) return '—';
  try {
    const [whole, fraction=''] = formatUnits(BigInt(value),decimals).split('.');
    return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')+(places && fraction ? '.'+fraction.slice(0,places).padEnd(places,'0') : '');
  } catch { return '—'; }
}
export function minimum(output: bigint, bps: number): bigint { return output*BigInt(10000-bps)/10000n; }
export function maximum(output: bigint, bps: number): bigint { return (output*BigInt(10000+bps)+9999n)/10000n; }
export function short(address?: string) { return address ? `${address.slice(0,6)}…${address.slice(-4)}` : 'Disconnected'; }
export function describeError(error: unknown): string {
  if (!error) return '';
  if (typeof error === 'object' && 'shortMessage' in error) return String(error.shortMessage).slice(0,250);
  return (error instanceof Error ? error.message : String(error)).slice(0,250);
}
export function quoteIsStale(updatedAt: number, now=Date.now(), ttl=15000) { return !updatedAt || now-updatedAt > ttl || updatedAt>now; }
