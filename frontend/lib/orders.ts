import type { Address } from 'viem';
import type { OrderView } from './api';
export const orderFields=[{name:'orderId',type:'bytes32'},{name:'productId',type:'uint256'},{name:'buyer',type:'address'},{name:'maxMudAmount',type:'uint256'},{name:'deadline',type:'uint256'},{name:'nonce',type:'uint256'}] as const;
export function validatePreparedOrder(order:OrderView,chainId:number,market:Address,buyer:Address,productId:string,cap:bigint,chainTime:bigint){
 const t=order.typed_data,m=t?.message,domain=t?.domain;
 if(t?.primaryType!=='Order'||domain?.name!=='MUD Marketplace'||domain.version!=='1'||domain.chainId!==chainId||domain.verifyingContract.toLowerCase()!==market.toLowerCase()||
  m?.buyer.toLowerCase()!==buyer.toLowerCase()||m.productId!==productId||m.orderId!==order.order_hash||!/^0x[0-9a-f]{64}$/i.test(m.orderId)||
  BigInt(m.maxMudAmount)!==cap||BigInt(m.deadline)<=chainTime||BigInt(m.deadline)>chainTime+900n||!/^\d+$/.test(m.nonce)||JSON.stringify(t.types.Order)!==JSON.stringify(orderFields))throw Error('Prepared order does not match the requested payment constraints.');
 return order;
}
