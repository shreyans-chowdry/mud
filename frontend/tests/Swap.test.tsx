import { beforeEach,expect,it,vi } from 'vitest';
import { fireEvent,render,screen,waitFor } from '@testing-library/react';
import { BondingCurveSwap } from '@/components/BondingCurveSwap';
const state=vi.hoisted(()=>({connected:true,chain:31337,balance:100000000n,allowance:0n,stale:false,pending:false,write:vi.fn(),simulate:vi.fn()}));
vi.mock('@/providers/Providers',()=>({useProtocol:()=>({deployment:{chainId:31337,name:'Local EVM',tokenSymbol:'MUD',collateralDecimals:6,confirmations:1,contracts:{token:'0x1111111111111111111111111111111111111111',collateral:'0x2222222222222222222222222222222222222222'}}})}));
vi.mock('@/hooks/useClock',()=>({useClock:()=>Date.now()}));
vi.mock('wagmi',()=>({
 useAccount:()=>({isConnected:state.connected,address:state.connected?'0x3333333333333333333333333333333333333333':undefined,chainId:state.chain}),
 usePublicClient:()=>({simulateContract:state.simulate,getBlock:async()=>({timestamp:100n})}),
 useReadContract:(config:{functionName:string;query?:{enabled?:boolean}})=>{
  const values:Record<string,unknown>={quoteBuy:[100n*10n**18n,0n,10000000n],quoteSell:[9950000n,50000n,10000000n],balanceOf:state.balance,allowance:state.allowance,symbol:'mUSD',paused:false,reserveHealthy:true};
  return {data:config.query?.enabled===false?undefined:values[config.functionName],dataUpdatedAt:Date.now()-(state.stale?20000:0),isFetching:false,error:null,refetch:vi.fn()};
 },
 useWriteContract:()=>({writeContractAsync:state.write,reset:vi.fn(),isPending:state.pending,data:undefined,error:null}),
 useWaitForTransactionReceipt:()=>({data:undefined,isLoading:false,error:null})
}));
beforeEach(()=>{state.connected=true;state.chain=31337;state.balance=100000000n;state.allowance=0n;state.stale=false;state.pending=false;state.write.mockReset();state.simulate.mockReset().mockResolvedValue({request:{}});});
it('cannot trade disconnected or on the wrong chain',()=>{state.connected=false;const r=render(<BondingCurveSwap/>);expect(screen.getByRole('button',{name:/Connect wallet to trade/})).toBeDisabled();state.connected=true;state.chain=8453;r.rerender(<BondingCurveSwap/>);expect(screen.getByText(/Switch to Local EVM/)).toBeInTheDocument();expect(screen.getByRole('button',{name:/Switch network/})).toBeDisabled();});
it('rejects imprecise decimal input and insufficient balances before a wallet write',()=>{render(<BondingCurveSwap/>);const input=screen.getByLabelText('You pay');fireEvent.change(input,{target:{value:'1.0000001'}});expect(screen.getByRole('alert')).toHaveTextContent('at most 6 decimal');fireEvent.change(input,{target:{value:'1000'}});expect(screen.getByRole('alert')).toHaveTextContent('Insufficient');expect(state.write).not.toHaveBeenCalled();});
it('disables stale quotes and asks for refresh',()=>{state.stale=true;render(<BondingCurveSwap/>);fireEvent.change(screen.getByLabelText('You pay'),{target:{value:'10'}});expect(screen.getByRole('button',{name:/Review approval/})).toBeDisabled();expect(screen.getByRole('button',{name:/Refresh expired quote/})).toBeVisible();});
it('keeps approval rejection in an error state without claiming a purchase',async()=>{state.write.mockRejectedValue(Object.assign(Error('User rejected approval'),{shortMessage:'User rejected approval'}));render(<BondingCurveSwap/>);fireEvent.change(screen.getByLabelText('You pay'),{target:{value:'10'}});fireEvent.click(screen.getByRole('button',{name:/Review approval/}));fireEvent.click(screen.getByRole('button',{name:'Confirm approval'}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('User rejected approval'));expect(screen.queryByText(/Receipt confirmed/)).not.toBeInTheDocument();});
it('uses an explicit minimum output and deadline in simulated purchase execution',async()=>{state.allowance=100000000n;render(<BondingCurveSwap/>);fireEvent.change(screen.getByLabelText('You pay'),{target:{value:'10'}});fireEvent.click(screen.getByRole('button',{name:/Review purchase/}));fireEvent.click(screen.getByRole('button',{name:'Confirm transaction'}));await waitFor(()=>expect(state.simulate).toHaveBeenCalledWith(expect.objectContaining({functionName:'buyTokens',args:[10000000n,99500000000000000000n,400n]})));});
it('shows the wallet-pending phase and prevents duplicate submissions',()=>{state.pending=true;render(<BondingCurveSwap/>);expect(screen.getByRole('button',{name:/Confirm in wallet/})).toBeDisabled();});
