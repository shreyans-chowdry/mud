export const API = process.env.NEXT_PUBLIC_API_URL || '';
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api/v1${path}`, {...init, cache:'no-store',headers:{'Content-Type':'application/json',...init?.headers}, signal:init?.signal || AbortSignal.timeout(15000)});
  const body = await response.json();
  if (!response.ok) throw Error(body.error?.message || `Service returned ${response.status}`);
  return body as T;
}
export type Spot = {kind:string; chain_id:number; total_supply:string; curve_accounted_supply:string; reserve_balance:string; spot_price:string;
  collateral_decimals:number; accrued_fees:string; gross_redemption_liability:string; net_redemption_liability:string; coverage_bps:string|null;
  reserve_healthy:boolean; paused:boolean; oracle:{valid:boolean; price_usd8?:string; updated_at?:number; age_seconds?:number};block_number:number;quote_timestamp:number; cache_age_seconds:number};
export type Product = {id:string; merchant:`0x${string}`;usd_price6:string;remaining:string;per_buyer_limit:string;listed:boolean;metadata_uri:string;mud_required:string|null;quote_error:string|null};
export type TypedOrder = {domain:{name:string;version:string;chainId:number;verifyingContract:`0x${string}`};primaryType:'Order';types:{Order:readonly {name:string;type:string}[]};message:{orderId:`0x${string}`;productId:string;buyer:`0x${string}`;maxMudAmount:string;deadline:string;nonce:string}};
export type OrderView = {id:string;order_hash:string;status:string;fulfillment_status:string;chain_id:number;product_id:string;buyer:string;max_mud_amount:string;paid_amount:string|null;deadline:number;transaction_hash:`0x${string}`|null;typed_data:TypedOrder;history?:{state:string;reason:string;timestamp:number}[]};
export type Activity = {tx_hash:`0x${string}`;log_index:number;block_number:number;event_type:string;mud_amount:string;collateral_amount:string;user_address:string|null;timestamp:number;canonical:boolean;finality_status:string};
