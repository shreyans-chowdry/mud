'use client';
import { useAccount, usePublicClient } from 'wagmi';
import { useQuery } from '@tanstack/react-query';
import { Gift, ArrowUpRight } from 'lucide-react';
import { useProtocol } from '@/providers/Providers';
import { api } from '@/lib/api';
import { MudAirdropAbi } from '@/lib/abi';
import { amount,describeError } from '@/lib/format';
import { useTransaction } from '@/hooks/useTransaction';
import { useClock } from '@/hooks/useClock';
import { TransactionStatus } from './TransactionStatus';
type Eligibility={eligible:boolean;root_matches_chain:boolean;expiry:number;claimed:boolean;root:string;dataset_version:string;dataset_hash:string;claim:null|{index:number;address:`0x${string}`;allocation:string;proof:`0x${string}`[]}};
export function Airdrop(){
 const {deployment:d}=useProtocol();const {address,chainId}=useAccount();const now=useClock();const client=usePublicClient({chainId:d?.chainId});
 const q=useQuery({queryKey:['eligibility',d?.chainId,d?.contracts.airdrop,address],queryFn:()=>api<Eligibility>(`/airdrop/eligibility/${address}`),enabled:!!address&&!!d,refetchInterval:15000});
 const tx=useTransaction(()=>void q.refetch());const e=d&&!q.isError?q.data:undefined;const expired=!!e&&e.expiry<=now/1000;
 async function claim(){if(!e?.claim||!d||!client||!address)return;tx.reset();tx.setOperation('Claim genesis allocation');try{
  const verified=await api<{valid:boolean}>('/airdrop/verify-proof',{method:'POST',body:JSON.stringify({index:e.claim.index,address:e.claim.address,allocation:e.claim.allocation,proof:e.claim.proof})});
  if(!verified.valid)throw Error('Dataset proof no longer matches the on-chain root.');
  const simulation=await client.simulateContract({account:address,address:d.contracts.airdrop,abi:MudAirdropAbi,functionName:'claim',args:[BigInt(e.claim.index),e.claim.address,BigInt(e.claim.allocation),e.claim.proof]});
  await tx.writer.writeContractAsync({...simulation.request,chainId:d.chainId});
 }catch(error){tx.setLocalError(describeError(error));}}
 return <><div className="page-heading"><div><span className="eyebrow">GENESIS DISTRIBUTION</span><h1>A place in<br/><span>the first chapter.</span></h1><p>Verify committed eligibility. Claim your collateral-backed allocation.</p></div></div><section className="panel airdrop-panel"><div className="airdrop-icon"><Gift size={34}/></div><h2>{!d?'Eligibility unavailable':!address?'Connect to verify eligibility':q.error?'Eligibility unavailable':q.isPending?'Checking committed dataset…':e?.claimed?'Allocation already claimed':e?.eligible?'Your allocation is committed.':'No allocation found'}</h2><p className="muted">An address is eligible only when it is included in the published Merkle dataset.</p>{e?.claim&&<><div className="airdrop-amount">{amount(e.claim.allocation,18,2)} <span>{d?.tokenSymbol}</span></div><dl className="details-list"><div><dt>Dataset version</dt><dd>{e.dataset_version}</dd></div><div><dt>Claim index</dt><dd>{e.claim.index}</dd></div><div><dt>Commitment matches chain</dt><dd>{e.root_matches_chain?'Verified':'Mismatch — claims disabled'}</dd></div><div><dt>Expiry</dt><dd>{new Date(e.expiry*1000).toLocaleString()}</dd></div></dl><p className="micro hash">Dataset SHA-256: {e.dataset_hash}</p></>}{q.error&&<p className="error">{describeError(q.error)}</p>}{expired&&<p className="error">The claim window has expired.</p>}<div className="review"><strong>Review on {d?.name||'configured chain'}</strong><p>Claim {e?.claim?amount(e.claim.allocation,18,8):'—'} {d?.tokenSymbol||'tokens'} to your connected wallet. A valid commitment is required.</p></div><button className="button primary trade-button" disabled={!e?.eligible||!e.root_matches_chain||e.claimed||expired||chainId!==d?.chainId||tx.pending} onClick={()=>void claim()}>{tx.pending?tx.stage:'Claim allocation'}<ArrowUpRight size={16}/></button><TransactionStatus stage={tx.stage} error={tx.error} hash={tx.writer.data} operation={tx.operation}/><p className="micro">Merkle inclusion does not prove unique identity or Sybil resistance.</p></section></>;
}
