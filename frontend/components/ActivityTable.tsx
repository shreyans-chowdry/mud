'use client';
import { useQuery } from '@tanstack/react-query';
import { api,type Activity } from '@/lib/api';
import { useProtocol } from '@/providers/Providers';
import { amount,short } from '@/lib/format';
export function ActivityTable({limit=8}:{limit?:number}){
 const {deployment:d}=useProtocol();const query=useQuery({queryKey:['activity',d?.chainId,d?.contracts.token,limit],queryFn:()=>api<{events:Activity[]}>(`/activity?limit=${limit}`),enabled:!!d,refetchInterval:7000});
 if(!d)return <div className="empty"><strong>Activity unavailable</strong><p>Configure a verified deployment to read its canonical events.</p></div>;
 if(query.isPending)return <div className="skeleton-block" aria-label="Loading indexed events"/>;
 if(query.error)return <div className="empty"><strong>Indexer unavailable</strong><p>Indexed events will appear when the API is connected.</p><button className="text-button" onClick={()=>void query.refetch()}>Retry connection ↻</button></div>;
 if(!query.data?.events.length)return <div className="empty"><strong>A clean ledger.</strong><p>Canonical protocol events will appear here after your first transaction.</p></div>;
 return <div className="table-scroll"><table><thead><tr><th>EVENT / TRANSACTION</th><th>ACCOUNT</th><th>AMOUNT · {d?.tokenSymbol||'MUD'}</th><th>BLOCK</th><th>STATUS</th></tr></thead><tbody>{query.data.events.map(e=><tr key={`${e.tx_hash}:${e.log_index}`}><td><strong>{e.event_type}</strong>{d?.explorer?<a target="_blank" rel="noreferrer" href={`${d.explorer}/tx/${e.tx_hash}`}>{short(e.tx_hash)} ↗</a>:<span className="mono">{short(e.tx_hash)} / {e.log_index}</span>}</td><td className="mono">{e.user_address?short(e.user_address):'—'}</td><td className="mono">{amount(e.mud_amount,18,5)}</td><td className="mono">{e.block_number.toLocaleString()}</td><td><span className={`status-pill ${e.canonical?'':'bad'}`}><span className="dot"/>{e.finality_status.toLowerCase()}</span></td></tr>)}</tbody></table></div>;
}
