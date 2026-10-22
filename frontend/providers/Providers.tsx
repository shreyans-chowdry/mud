'use client';
import { createContext, useContext, useState } from 'react';
import { WagmiProvider } from 'wagmi';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { wagmiConfig } from '@/lib/wagmi';
import { api } from '@/lib/api';
import { validateDeployment, verifyBackendDeployment, type Deployment } from '@/lib/deployment';
export type { Deployment } from '@/lib/deployment';
const Context = createContext<{deployment:Deployment|undefined;error:Error|null;loading:boolean}>({deployment:undefined,error:null,loading:true});
function DeploymentProvider({children}:{children:React.ReactNode}) {
 const query=useQuery({queryKey:['deployment'],queryFn:async()=>{
  const r=await fetch('/deployment.json',{cache:'no-store'});
  if(!r.ok)throw Error('Live deployment is not configured. No prices, balances or listings are available.');
  const d=validateDeployment(await r.json(),process.env.NEXT_PUBLIC_ALLOW_TEST_NETWORKS==='true');
  verifyBackendDeployment(d,await api<unknown>('/deployment'));
  return d;
 },retry:false,staleTime:60000});
 return <Context.Provider value={{deployment:query.data,error:query.error,loading:query.isPending}}>{children}</Context.Provider>;
}
export function useProtocol(){return useContext(Context);}
export function Providers({children}:{children:React.ReactNode}) {
 const [client]=useState(()=>new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:true}}}));
 return <WagmiProvider config={wagmiConfig}><QueryClientProvider client={client}><DeploymentProvider>{children}</DeploymentProvider></QueryClientProvider></WagmiProvider>;
}
