'use client';
import { useProtocol } from '@/providers/Providers';
export function TransactionStatus({stage,error,hash,operation}:{stage:string;error:string;hash?:string;operation?:string}){
 const {deployment:d}=useProtocol();
 return <div className="tx-status" aria-live="polite"><div><span className={error?'dot danger':'dot'}/>{operation ? `${operation} · `:''}{error?'Action failed':stage}</div>{error&&<p role="alert" className="error">{error}</p>}{hash&&(d?.explorer?<a target="_blank" rel="noreferrer" href={`${d.explorer}/tx/${hash}`}>View transaction ↗</a>:<code className="hash">{hash}</code>)}</div>;
}
