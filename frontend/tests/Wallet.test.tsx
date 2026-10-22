import { beforeEach,describe,it,expect,vi } from 'vitest';
import { fireEvent,render,screen } from '@testing-library/react';
import { Wallet } from '@/components/Wallet';
const state=vi.hoisted(()=>({connected:false,chainId:31337,connect:vi.fn(),disconnect:vi.fn(),switchChain:vi.fn(),error:null as Error|null}));
vi.mock('wagmi',()=>({useAccount:()=>({isConnected:state.connected,address:state.connected?'0x1111111111111111111111111111111111111111':undefined,chainId:state.chainId}),useConnect:()=>({connect:state.connect,connectors:[{id:'injected'}],isPending:false,error:state.error}),useDisconnect:()=>({disconnect:state.disconnect}),useSwitchChain:()=>({switchChain:state.switchChain,isPending:false,error:null})}));
vi.mock('@/providers/Providers',()=>({useProtocol:()=>({deployment:{name:'Local EVM',chainId:31337}})}));
describe('Wallet network and rejection boundaries',()=>{
 beforeEach(()=>{state.connected=false;state.chainId=31337;state.error=null;vi.clearAllMocks();});
 it('connects, exposes the connected wallet and disconnects',()=>{const r=render(<Wallet/>);fireEvent.click(screen.getByText('Connect wallet'));expect(state.connect).toHaveBeenCalled();state.connected=true;r.rerender(<Wallet/>);fireEvent.click(screen.getByTitle('Disconnect wallet'));expect(state.disconnect).toHaveBeenCalled();});
 it('requests the configured chain when wallet is on the wrong network',()=>{state.connected=true;state.chainId=8453;render(<Wallet/>);fireEvent.click(screen.getByText('Switch network'));expect(state.switchChain).toHaveBeenCalledWith({chainId:31337});});
 it('shows a wallet rejection instead of inventing connection success',()=>{state.error=Error('User rejected request');render(<Wallet/>);expect(screen.getByRole('alert')).toHaveTextContent('User rejected request');});
});
