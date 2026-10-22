import { describe,it,expect,vi } from 'vitest';
import { render,screen } from '@testing-library/react';
import { QueryClient,QueryClientProvider } from '@tanstack/react-query';
import { Marketplace } from '@/components/Marketplace';
import { Dashboard } from '@/components/Dashboard';
import { Airdrop } from '@/components/Airdrop';
import { api } from '@/lib/api';
vi.mock('@/providers/Providers',()=>({useProtocol:()=>({deployment:undefined,error:null,loading:false})}));
vi.mock('@/lib/api',()=>({api:vi.fn()}));
vi.mock('wagmi',()=>({
 useAccount:()=>({isConnected:true,address:'0x1111111111111111111111111111111111111111',chainId:8453}),
 useReadContract:()=>({data:undefined,refetch:vi.fn()}),usePublicClient:()=>undefined,
 useWriteContract:()=>({reset:vi.fn(),data:undefined,isPending:false}),
 useWaitForTransactionReceipt:()=>({data:undefined,isLoading:false})
}));
function client(){return new QueryClient({defaultOptions:{queries:{retry:false}}});}
describe('An unconfigured public build never presents cached samples as live values',()=>{
 it('hides cached listings and financial snapshots and makes no API request',()=>{
  const q=client();q.setQueryData(['products',undefined,undefined,1],{products:[{id:'1',metadata_uri:'mud://cached-sample',merchant:'0x'+'11'.repeat(20),usd_price6:'999000000',remaining:'1',mud_required:'1000000000000000000',listed:true}],next_cursor:null});
  q.setQueryData(['spot',undefined,undefined],{total_supply:'999999000000000000000000',reserve_balance:'999999000000',spot_price:'999999000000',oracle:{valid:true,price_usd8:'100000000'}});
  render(<QueryClientProvider client={q}><Marketplace/><Dashboard/></QueryClientProvider>);
  expect(screen.getByText('Marketplace not connected')).toBeVisible();
  expect(screen.queryByText('cached sample')).not.toBeInTheDocument();
  expect(screen.queryByText(/999,999/)).not.toBeInTheDocument();
  expect(screen.queryByText('RESERVE CHECK PASSED')).not.toBeInTheDocument();
  expect(api).not.toHaveBeenCalled();
 });
 it('does not turn a stale cached airdrop allocation into an eligibility claim',()=>{
  const q=client();q.setQueryData(['eligibility',undefined,undefined,'0x1111111111111111111111111111111111111111'],{eligible:true,claim:{allocation:'12345000000000000000000'},claimed:false});
  render(<QueryClientProvider client={q}><Airdrop/></QueryClientProvider>);
  expect(screen.getByText('Eligibility unavailable')).toBeVisible();
  expect(screen.queryByText(/12,345/)).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:/Claim allocation/})).toBeDisabled();
  expect(api).not.toHaveBeenCalled();
 });
});
