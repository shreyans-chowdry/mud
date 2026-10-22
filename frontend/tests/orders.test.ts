import { expect,it } from 'vitest';
import { orderFields,validatePreparedOrder } from '@/lib/orders';
import type { OrderView } from '@/lib/api';
it('rejects an API order with a modified domain or payment cap before wallet signing',()=>{
 const market='0x1111111111111111111111111111111111111111' as const;const buyer='0x2222222222222222222222222222222222222222' as const;
 const hash='0x'+ 'ab'.repeat(32);
 const order={id:'test',status:'AWAITING_PAYMENT',fulfillment_status:'NOT_READY',chain_id:31337,product_id:'1',buyer,max_mud_amount:'20',paid_amount:null,deadline:500,transaction_hash:null,order_hash:hash,typed_data:{primaryType:'Order',domain:{name:'MUD Marketplace',version:'1',chainId:31337,verifyingContract:market},types:{Order:orderFields},message:{orderId:hash,productId:'1',buyer,maxMudAmount:'20',deadline:'500',nonce:'0'}}} as OrderView;
 expect(validatePreparedOrder(order,31337,market,buyer,'1',20n,100n)).toBe(order);
 expect(()=>validatePreparedOrder(order,8453,market,buyer,'1',20n,100n)).toThrow();
 expect(()=>validatePreparedOrder(order,31337,market,buyer,'1',19n,100n)).toThrow();
});
