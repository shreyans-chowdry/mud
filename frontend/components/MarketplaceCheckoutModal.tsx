'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { X, ArrowUpRight } from 'lucide-react';
import { useAccount, usePublicClient, useReadContract, useSignTypedData } from 'wagmi';
import { erc20Abi, zeroAddress, type Hex } from 'viem';
import { useQuery } from '@tanstack/react-query';
import { MudMarketplaceAbi } from '@/lib/abi';
import { api, type OrderView, type Product } from '@/lib/api';
import { amount, describeError, maximum, quoteIsStale, short } from '@/lib/format';
import { orderFields,validatePreparedOrder } from '@/lib/orders';
import { useClock } from '@/hooks/useClock';
import { useTransaction } from '@/hooks/useTransaction';
import { useProtocol } from '@/providers/Providers';
import { TransactionStatus } from './TransactionStatus';

export function MarketplaceCheckoutModal({product,onClose}:{product:Product;onClose:()=>void}){
 const {deployment:d}=useProtocol();const {address,chainId,isConnected}=useAccount();const [bps,setBps]=useState(50);
 const [order,setOrder]=useState<OrderView>();const [signature,setSignature]=useState<Hex>();const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 const dialog=useRef<HTMLDialogElement>(null);const now=useClock();const signer=useSignTypedData();const publicClient=usePublicClient({chainId:d?.chainId});
 useEffect(()=>{const previous=document.activeElement as HTMLElement|null;dialog.current?.showModal();return()=>{previous?.focus();};},[]);
 const quote=useReadContract({address:d?.contracts.marketplace,abi:MudMarketplaceAbi,functionName:'quoteProduct',args:[BigInt(product.id)],chainId:d?.chainId,query:{enabled:!!d,refetchInterval:8000}});
 const listing=useReadContract({address:d?.contracts.marketplace,abi:MudMarketplaceAbi,functionName:'products',args:[BigInt(product.id)],chainId:d?.chainId,query:{enabled:!!d,refetchInterval:8000}});
 const purchased=useReadContract({address:d?.contracts.marketplace,abi:MudMarketplaceAbi,functionName:'purchased',args:[BigInt(product.id),address||zeroAddress],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:8000}});
 const balance=useReadContract({address:d?.contracts.token,abi:erc20Abi,functionName:'balanceOf',args:[address||zeroAddress],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:8000}});
 const allowance=useReadContract({address:d?.contracts.token,abi:erc20Abi,functionName:'allowance',args:[address||zeroAddress,d?.contracts.marketplace||zeroAddress],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:8000}});
 const tx=useTransaction(()=>{void allowance.refetch();void balance.refetch();void listing.refetch();void purchased.refetch();});
 const polled=useQuery({queryKey:['order',d?.chainId,d?.contracts.marketplace,order?.id],queryFn:()=>api<OrderView>(`/marketplace/order/${order!.id}/status`),enabled:!!order,refetchInterval:3000});
 const current=polled.data||order;const cap=order?BigInt(order.max_mud_amount):quote.data?maximum(quote.data[0],bps):undefined;
 const insufficient=cap!==undefined&&balance.data!==undefined&&balance.data<cap;
 const approval=cap!==undefined&&allowance.data!==undefined&&allowance.data<cap;
 const stale=quoteIsStale(quote.dataUpdatedAt,Math.max(now,Date.now()));const wrong=!!d&&isConnected&&chainId!==d.chainId;
 const expired=!!order&&now/1000>order.deadline;
 const purchasedLimit=listing.data&&purchased.data!==undefined?purchased.data>=listing.data[3]:false;
 const unavailable=!listing.data||!listing.data[4]||listing.data[2]===0n||purchasedLimit;
 const pending=busy||tx.pending||signer.isPending;
 const settled=!!current&&['PAYMENT_OBSERVED','CONFIRMED','FULFILLED','FULFILLMENT_RETRY','FULFILLMENT_FAILED'].includes(current.status);
 const submitted=tx.operation==='Marketplace payment'&&!!tx.writer.data&&tx.receipt.data?.status!=='reverted';
 const disabled=!d||!address||wrong||unavailable||stale||cap===undefined||balance.data===undefined||allowance.data===undefined||insufficient||pending||expired||settled||submitted;
 useEffect(()=>{setOrder(undefined);setSignature(undefined);setError('');},[address,chainId]);
 async function act(){
  if(disabled||!d||!address||!publicClient||cap===undefined)return;
  setError('');tx.reset();setBusy(true);
  try{
   if(!order){
    const value=await api<OrderView>('/marketplace/create-order',{method:'POST',body:JSON.stringify({product_id:product.id,buyer:address,max_mud_amount:cap.toString(),ttl_seconds:300})});
    const block=await publicClient.getBlock();
    validatePreparedOrder(value,d.chainId,d.contracts.marketplace,address,product.id,cap,block.timestamp);
    setOrder(value);return;
   }
   if(approval){
    tx.setOperation('Approve marketplace allowance');
    const simulation=await publicClient.simulateContract({account:address,address:d.contracts.token,abi:erc20Abi,functionName:'approve',args:[d.contracts.marketplace,cap]});
    await tx.writer.writeContractAsync({...simulation.request,chainId:d.chainId});return;
   }
   if(!signature){
    const t=order.typed_data;
    const sig=await signer.signTypedDataAsync({domain:t.domain,types:{Order:orderFields},primaryType:'Order',message:{...t.message,productId:BigInt(t.message.productId),maxMudAmount:BigInt(t.message.maxMudAmount),deadline:BigInt(t.message.deadline),nonce:BigInt(t.message.nonce)}});
    setSignature(sig);return;
   }
   const t=order.typed_data.message;
   tx.setOperation('Marketplace payment');
   const simulation=await publicClient.simulateContract({account:address,address:d.contracts.marketplace,abi:MudMarketplaceAbi,functionName:'purchaseOrder',args:[{orderId:t.orderId,productId:BigInt(t.productId),buyer:t.buyer,maxMudAmount:BigInt(t.maxMudAmount),deadline:BigInt(t.deadline),nonce:BigInt(t.nonce)},signature]});
   await tx.writer.writeContractAsync({...simulation.request,chainId:d.chainId});
  }catch(e){setError(describeError(e));}finally{setBusy(false);}
 }
 return <dialog ref={dialog} className="checkout-dialog" onCancel={e=>{if(pending)e.preventDefault();else onClose();}} aria-labelledby="checkout-title"><div className="dialog-inner"><div className="row"><span className="eyebrow">SECURE CHECKOUT</span><button className="icon-button" aria-label="Close checkout" onClick={onClose} disabled={pending}><X size={20}/></button></div><h2 id="checkout-title">{product.metadata_uri.replace('mud://','').replaceAll('-',' ')}</h2><p className="muted">Merchant <code>{short(product.merchant)}</code></p><div className="checkout-price">${amount(product.usd_price6,6,2)}<span> USD reference price</span></div><div className="trade-details"><div><span>Live payment estimate</span><strong>{amount(quote.data?.[0],18,6)} {d?.tokenSymbol}</strong></div><div><span>Slippage cap</span><select aria-label="Checkout slippage" value={bps} disabled={!!order||pending} onChange={e=>setBps(Number(e.target.value))}><option value={50}>0.50%</option><option value={100}>1.00%</option></select></div><div><span>Maximum authorized</span><strong>{amount(cap,18,6)} {d?.tokenSymbol}</strong></div><div><span>Merchant / burned</span><strong>95% / 5%</strong></div><div><span>Network</span><strong>{d?.name}</strong></div><div><span>Available</span><strong>{listing.data?.[2].toString()||'—'}</strong></div></div><p className="micro">Your wallet will transfer only the required payment. The maximum is a cap. The reference conversion uses marginal spot price; it is not a liquidation quote.</p>{!address&&<p className="notice">Connect your wallet to continue.</p>}{wrong&&<p className="error">Switch your wallet to {d?.name}.</p>}{insufficient&&<p className="error">Your balance is below the maximum authorized payment.</p>}{unavailable&&<p className="error">Listing unavailable or buyer limit reached.</p>}{expired&&<p className="error">Order expired. Close checkout and prepare a fresh order.</p>}{stale&&<button className="text-button" onClick={()=>void quote.refetch()}>Refresh quote ↻</button>}<div className="review"><strong>Review before each wallet action</strong><p>{!order?'Prepare an unsigned order.':approval?`Approve up to ${amount(cap,18,8)} ${d?.tokenSymbol} for this marketplace.`:!signature?'Sign the displayed EIP-712 order; signing alone does not pay.':`Pay at most ${amount(cap,18,8)} ${d?.tokenSymbol} on ${d?.name}.`}</p></div><button className="button primary trade-button" disabled={disabled} onClick={()=>void act()}>{pending?'Waiting…':settled?'Payment indexed':submitted?'Waiting for indexer':!order?'Prepare order':approval?'Approve '+d?.tokenSymbol:!signature?'Sign order':'Submit payment'}<ArrowUpRight size={17}/></button><TransactionStatus stage={tx.stage} error={error||tx.error||describeError(quote.error)} hash={tx.writer.data} operation={tx.operation}/>{current&&<div className="order-inline"><p>Settlement: <strong>{current.status}</strong></p><p>Delivery: <strong>{current.fulfillment_status}</strong></p><Link href={`/orders/${current.id}`} onClick={onClose}>Track this order <ArrowUpRight size={14}/></Link></div>}{polled.error&&<p className="error">Order tracking unavailable. The receipt can still be checked on chain.</p>}<p className="micro">A confirmed payment and delivery of digital goods are separate events.</p></div></dialog>;
}
