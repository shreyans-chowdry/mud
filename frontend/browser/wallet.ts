import type { Page } from '@playwright/test';
/** Test-only EIP-1193 adapter. Uses unlocked LOCAL RPC accounts, never embeds a private key. */
export async function localWallet(page:Page,initialChain=31337){
 await page.addInitScript(({initialChain})=>{
  type Listener=(value:unknown)=>void;
  const listeners=new Map<string,Set<Listener>>();let chain=initialChain;let enabled=false;
  const address='0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
  let id=0;
  const provider={isMetaMask:false,
   on(event:string,listener:Listener){if(!listeners.has(event))listeners.set(event,new Set());listeners.get(event)!.add(listener);return provider;},
   removeListener(event:string,listener:Listener){listeners.get(event)?.delete(listener);return provider;},
   async request({method,params=[]}:{method:string;params?:unknown[]}){
    if(method==='eth_chainId')return '0x'+chain.toString(16);
    if(method==='eth_accounts')return enabled?[address]:[];
    if(method==='eth_requestAccounts'){enabled=true;return [address];}
    if(method==='wallet_switchEthereumChain'){
     chain=Number((params[0] as {chainId:string}).chainId);if(chain!==31337)throw Error('Local test wallet cannot switch to a live chain');
     for(const l of listeners.get('chainChanged')||[])l('0x7a69');return null;
    }
    if(method==='wallet_requestPermissions')return [{parentCapability:'eth_accounts'}];
    if(method==='wallet_getPermissions')return enabled?[{parentCapability:'eth_accounts'}]:[];
    if(method==='wallet_watchAsset')return true;
    const url='http://127.0.0.1:8545';
    const check=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:++id,method:'eth_chainId',params:[]})}).then(r=>r.json());
    if(check.result!=='0x7a69')throw Error('Refusing non-local RPC');
    const reject=(window as unknown as {rejectNextTransaction?:boolean});
    if(method==='eth_sendTransaction'&&reject.rejectNextTransaction){reject.rejectNextTransaction=false;throw Object.assign(Error('User rejected request'),{code:4001});}
    const result=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:++id,method,params})}).then(r=>r.json());
    if(result.error)throw Object.assign(Error(result.error.message),{code:result.error.code});return result.result;
   }
  };
  Object.defineProperty(window,'ethereum',{value:provider,writable:false});
 },{initialChain});
}
