import { act,renderHook } from '@testing-library/react';
import { beforeEach,expect,it,vi } from 'vitest';
import { useTransaction } from '@/hooks/useTransaction';
const state=vi.hoisted(()=>({pending:false,hash:undefined as `0x${string}`|undefined,receipt:undefined as {status:string}|undefined,receiptLoading:false,error:null as Error|null}));
vi.mock('@/providers/Providers',()=>({useProtocol:()=>({deployment:{chainId:31337,confirmations:1}})}));
vi.mock('wagmi',()=>({useWriteContract:()=>({isPending:state.pending,data:state.hash,error:state.error,reset:vi.fn()}),useWaitForTransactionReceipt:()=>({data:state.receipt,isLoading:state.receiptLoading,error:null})}));
beforeEach(()=>{state.pending=false;state.hash=undefined;state.receipt=undefined;state.receiptLoading=false;state.error=null;});
it('never advances a pending transaction to confirmed without a successful receipt',()=>{
 state.hash='0xabc';state.receiptLoading=true;const confirmed=vi.fn();const r=renderHook(()=>useTransaction(confirmed));
 expect(r.result.current.pending).toBe(true);expect(confirmed).not.toHaveBeenCalled();
 act(()=>{state.receiptLoading=false;state.receipt={status:'reverted'};});r.rerender();expect(r.result.current.error).toContain('reverted');expect(confirmed).not.toHaveBeenCalled();
 act(()=>{state.receipt={status:'success'};});r.rerender();expect(confirmed).toHaveBeenCalledTimes(1);r.rerender();expect(confirmed).toHaveBeenCalledTimes(1);
});
it('renders rejected wallet requests as errors',()=>{state.error=Error('User rejected request');const r=renderHook(()=>useTransaction());expect(r.result.current.error).toContain('rejected');});
