'use client';
import { useAccount, useConnect, useDisconnect, useSwitchChain } from 'wagmi';
import { useProtocol } from '@/providers/Providers';
import { describeError,short } from '@/lib/format';
export function Wallet(){
 const account=useAccount();const connect=useConnect();const disconnect=useDisconnect();const switcher=useSwitchChain();const {deployment:d}=useProtocol();
 const wrong=account.isConnected&&d&&account.chainId!==d.chainId;
 return <div className="wallet"><span className="chain-pill"><span className="dot"/>{d?.name || 'No deployment'}</span>{account.isConnected?<>{wrong&&<button className="button primary small" onClick={()=>switcher.switchChain({chainId:d.chainId})} disabled={switcher.isPending}>Switch network</button>}<button className="button small" onClick={()=>disconnect.disconnect()} title="Disconnect wallet">{short(account.address)} <span aria-hidden>↗</span></button></>:<button className="button primary small" disabled={!d||connect.isPending||!connect.connectors[0]} onClick={()=>connect.connect({connector:connect.connectors[0]})}>{connect.isPending?'Connecting…':'Connect wallet'}</button>}{(connect.error||switcher.error)&&<span role="alert" className="wallet-error">{describeError(connect.error||switcher.error)}</span>}</div>;
}
