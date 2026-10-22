'use client';
import { useState } from 'react';
import { ArrowDown, ArrowUpRight, Settings2, ShieldCheck } from 'lucide-react';
import { useAccount, usePublicClient, useReadContract } from 'wagmi';
import { erc20Abi, zeroAddress } from 'viem';
import { MudTokenAMMAbi } from '@/lib/abi';
import { amount, describeError, minimum, parseAmount, quoteIsStale } from '@/lib/format';
import { useProtocol } from '@/providers/Providers';
import { useClock } from '@/hooks/useClock';
import { useTransaction } from '@/hooks/useTransaction';
import { TransactionStatus } from './TransactionStatus';

export function BondingCurveSwap(){
 const {deployment:d}=useProtocol();const {address,chainId,isConnected}=useAccount();
 const [side,setSide]=useState<'buy'|'sell'>('buy');const [input,setInput]=useState('');const [bps,setBps]=useState(50);
 const [review,setReview]=useState(false); const now=useClock();
 const token=d?.contracts.token;const collateral=d?.contracts.collateral;const buy=side==='buy';
 const precision=buy?(d?.collateralDecimals || 6):18;const parsed=parseAmount(input,precision);
 const account=address || zeroAddress;
 const quote=useReadContract({address:token,abi:MudTokenAMMAbi,functionName:buy?'quoteBuy':'quoteSell',args:[parsed||0n],chainId:d?.chainId,query:{enabled:!!d&&!!parsed,refetchInterval:8000}});
 const tokenBalance=useReadContract({address:token,abi:erc20Abi,functionName:'balanceOf',args:[account],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:10000}});
 const collateralBalance=useReadContract({address:collateral,abi:erc20Abi,functionName:'balanceOf',args:[account],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:10000}});
 const symbol=useReadContract({address:collateral,abi:erc20Abi,functionName:'symbol',chainId:d?.chainId,query:{enabled:!!d}});
 const allowance=useReadContract({address:collateral,abi:erc20Abi,functionName:'allowance',args:[account,token||zeroAddress],chainId:d?.chainId,query:{enabled:!!d&&!!address,refetchInterval:10000}});
 const paused=useReadContract({address:token,abi:MudTokenAMMAbi,functionName:'paused',chainId:d?.chainId,query:{enabled:!!d,refetchInterval:8000}});
 const healthy=useReadContract({address:token,abi:MudTokenAMMAbi,functionName:'reserveHealthy',chainId:d?.chainId,query:{enabled:!!d,refetchInterval:8000}});
 const refresh=()=>{void tokenBalance.refetch();void collateralBalance.refetch();void allowance.refetch();void quote.refetch();setReview(false);};
 const tx=useTransaction(refresh);const publicClient=usePublicClient({chainId:d?.chainId});
 const mud=d?.tokenSymbol||'MUD';const col=symbol.data||'collateral';const inputSymbol=buy?col:mud;const outputSymbol=buy?mud:col;
 const balance=buy?collateralBalance.data:tokenBalance.data;const output=quote.data?.[0];
 const stale=quoteIsStale(quote.dataUpdatedAt,Math.max(now,Date.now()));const insufficient=!!parsed&&balance!==undefined&&parsed>balance;
 const unknownBalance=isConnected&&balance===undefined;const wrong=isConnected&&chainId!==d?.chainId;
 const needApproval=buy&&!!parsed&&allowance.data!==undefined&&allowance.data<parsed;
 const resetAllowance=needApproval&&!!allowance.data;
 const invalid=!d||!isConnected||wrong||!parsed||output===undefined||stale||insufficient||unknownBalance||paused.data!==false||healthy.data!==true||(buy&&allowance.data===undefined)||tx.pending;
 const min=output!==undefined?minimum(output,bps):undefined;
 async function execute(){
  if(invalid||!d||!address||!publicClient||!parsed||min===undefined)return;
  tx.reset();
  try{
   if(needApproval){
    tx.setOperation(resetAllowance?'Reset collateral allowance':'Approve collateral');
    const simulation=await publicClient.simulateContract({account:address,address:d.contracts.collateral,abi:erc20Abi,functionName:'approve',args:[d.contracts.token,resetAllowance?0n:parsed]});
    await tx.writer.writeContractAsync({...simulation.request,chainId:d.chainId});
   }else{
    tx.setOperation(buy?'Acquire tokens':'Redeem tokens');
    const block=await publicClient.getBlock();
    const simulation=await publicClient.simulateContract({account:address,address:d.contracts.token,abi:MudTokenAMMAbi,functionName:buy?'buyTokens':'sellTokens',args:[parsed,min,block.timestamp+300n]});
    await tx.writer.writeContractAsync({...simulation.request,chainId:d.chainId});
   }
  }catch(e){tx.setLocalError(describeError(e));}
 }
 function change(next:string){setInput(next);setReview(false);tx.reset();}
 return <section className="panel swap-panel"><div className="panel-heading"><div><span className="eyebrow">BONDING CURVE</span><h2>Make your next move.</h2></div><Settings2 size={18} className="muted"/></div><div className="segmented" aria-label="Trade direction">{(['buy','sell'] as const).map(s=><button key={s} className={side===s?'selected':''} disabled={tx.pending} onClick={()=>{setSide(s);change('');}}>{s==='buy'?'Buy '+mud:'Redeem '+mud}</button>)}</div><div className="amount-box"><div className="row"><label htmlFor="trade-input">You {buy?'pay':'redeem'}</label><span>Balance: {amount(balance,precision,4)}</span></div><div className="amount-input"><input id="trade-input" inputMode="decimal" value={input} onChange={e=>change(e.target.value)} placeholder="0.00" autoComplete="off" disabled={tx.pending}/><span className="token-chip"><span className={buy?'coin usdc':'coin'}>{buy?'$':'m'}</span>{inputSymbol}</span></div></div><div className="swap-divider"><span><ArrowDown size={16}/></span></div><div className="amount-box output"><div className="row"><span>Estimated receive</span><span>{quote.isFetching?'Quoting…':stale&&output!==undefined?'Quote expired':'Integrated curve'}</span></div><div className="amount-input"><output>{amount(output,buy?18:(d?.collateralDecimals||6),6)}</output><span className="token-chip"><span className={buy?'coin':'coin usdc'}>{buy?'m':'$'}</span>{outputSymbol}</span></div></div><div className="trade-details"><div><span>Slippage tolerance</span><select aria-label="Slippage tolerance" value={bps} disabled={tx.pending} onChange={e=>{setBps(Number(e.target.value));setReview(false);}}><option value={10}>0.10%</option><option value={50}>0.50%</option><option value={100}>1.00%</option></select></div><div><span>Minimum receive</span><strong>{amount(min,buy?18:(d?.collateralDecimals||6),6)} {outputSymbol}</strong></div><div><span>Protocol fee</span><strong>{amount(quote.data?.[1],d?.collateralDecimals||6,6)} {col}</strong></div><div><span>Transaction deadline</span><strong>5 minutes after chain snapshot</strong></div></div>{input&&!parsed&&<p className="error" role="alert">Enter a positive amount with at most {precision} decimal places.</p>}{insufficient&&<p className="error" role="alert">Insufficient confirmed {inputSymbol} balance.</p>}{wrong&&<p className="error">Switch to {d?.name} to trade.</p>}{quote.error&&<p className="error" role="alert">{describeError(quote.error)}</p>}{stale&&output!==undefined&&<button className="text-button" onClick={()=>void quote.refetch()}>Refresh expired quote ↻</button>}{review&&<div className="review" role="status"><strong>Review on {d?.name}</strong><p>{needApproval?(resetAllowance?'Reset the existing allowance to zero.':`Approve ${input} ${col}. Approval does not buy tokens.`):`${buy?'Pay':'Burn'} ${input} ${inputSymbol}; receive at least ${amount(min,buy?18:(d?.collateralDecimals||6),8)} ${outputSymbol}.`}</p></div>}<button className="button primary trade-button" disabled={invalid} onClick={()=>review?void execute():setReview(true)}>{!isConnected?'Connect wallet to trade':wrong?'Switch network':tx.pending?tx.stage:review?(needApproval?(resetAllowance?'Confirm allowance reset':'Confirm approval'):'Confirm transaction'):'Review '+(needApproval?'approval':buy?'purchase':'redemption')}<ArrowUpRight size={17}/></button><TransactionStatus stage={tx.stage} error={tx.error} hash={tx.writer.data} operation={tx.operation}/><p className="micro trust-line"><ShieldCheck size={14}/> Collateral stays in the protocol. Quotes can change before inclusion.</p></section>;
}
