'use client';
import { useEffect, useRef, useState } from 'react';
import { useWaitForTransactionReceipt, useWriteContract } from 'wagmi';
import { describeError } from '@/lib/format';
import { useProtocol } from '@/providers/Providers';
export function useTransaction(onConfirmed?:()=>void){
 const {deployment:d}=useProtocol(); const writer=useWriteContract();
 const [operation,setOperation]=useState(''); const [localError,setLocalError]=useState('');
 const receipt=useWaitForTransactionReceipt({hash:writer.data,chainId:d?.chainId,confirmations:d?.confirmations || 1, query:{enabled:!!writer.data}});
 const callback=useRef(onConfirmed); const handled=useRef<string|undefined>(undefined);
 useEffect(()=>{callback.current=onConfirmed;},[onConfirmed]);
 useEffect(()=>{if(receipt.data?.status==='success'&&writer.data!==handled.current){handled.current=writer.data;callback.current?.();}},[receipt.data,writer.data]);
 const error=localError||describeError(writer.error)||describeError(receipt.error)||(receipt.data?.status==='reverted'?'Transaction reverted on chain.':'');
 const pending=writer.isPending||receipt.isLoading;
 const stage=writer.isPending?'Confirm in wallet':writer.data&&!receipt.data?'Awaiting on-chain receipt':receipt.data?.status==='success'?'Receipt confirmed':receipt.data?.status==='reverted'?'Transaction reverted':'Ready';
 return {writer,receipt,operation,setOperation,localError,setLocalError,error,pending,stage,reset:()=>{writer.reset();setLocalError('');setOperation('');}};
}
