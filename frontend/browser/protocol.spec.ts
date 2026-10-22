import { expect,test } from '@playwright/test';
import { encodeFunctionData, parseAbi } from 'viem';
import { localWallet } from './wallet';

async function rpc(method:string,params:unknown[]=[]){const r=await fetch('http://127.0.0.1:8545',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method,params})}).then(r=>r.json());if(r.error)throw Error(r.error.message);return r.result;}
test.beforeAll(async()=>{
 if(await rpc('eth_chainId')!=='0x7a69')throw Error('Local chain required');
 await rpc('evm_mine');
 const m=await fetch('http://127.0.0.1:3000/deployment.json').then(r=>r.json());
 const block=await rpc('eth_getBlockByNumber',['latest',false]);const stamp=BigInt(block.timestamp);
 await rpc('eth_sendTransaction',[{from:'0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',to:m.contracts.feed,data:encodeFunctionData({abi:parseAbi(['function set(int256,uint256,uint256,uint80,uint80)']),functionName:'set',args:[100000000n,stamp,stamp,1n,1n]})}]);
});
test('desktop and mobile dashboard render real chain data without overflow',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:/Built on real reserves/})).toBeVisible();await expect(page.getByText('RESERVE CHECK PASSED')).toBeVisible();
 await page.screenshot({path:'test-results/terminal-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await expect(page.getByRole('heading',{name:'Make your next move.'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/terminal-mobile.png',fullPage:true});
});
test('wrong network is visible and the wallet can switch and disconnect',async({page})=>{
 await localWallet(page,8453);await page.goto('/swap');await page.getByRole('button',{name:'Connect wallet',exact:true}).click();
 await expect(page.getByRole('banner').getByRole('button',{name:'Switch network',exact:true})).toBeVisible();await page.getByRole('banner').getByRole('button',{name:'Switch network',exact:true}).click();
 await expect(page.getByRole('banner').getByRole('button',{name:'Switch network',exact:true})).not.toBeVisible();await page.getByTitle('Disconnect wallet').click();await expect(page.getByRole('button',{name:'Connect wallet',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Connect wallet',exact:true}).click();await expect(page.getByTitle('Disconnect wallet')).toBeVisible();
});
test('wallet approval rejection stays failed, then actual approval and buy confirm',async({page})=>{
 await localWallet(page);await page.goto('/swap');await page.getByRole('button',{name:'Connect wallet',exact:true}).click();
 await page.getByLabel('You pay').fill('not-a-number');await expect(page.getByRole('main').getByRole('alert')).toContainText('positive amount');
 await page.getByLabel('You pay').fill('10');
 await page.getByRole('button',{name:'Review approval'}).click();
 await page.evaluate(()=>{(window as unknown as {rejectNextTransaction:boolean}).rejectNextTransaction=true;});
 await page.getByRole('button',{name:'Confirm approval',exact:true}).click();await expect(page.getByRole('main').getByRole('alert')).toContainText(/rejected/i);
 await page.getByRole('button',{name:'Confirm approval',exact:true}).click();
 await expect(page.getByText('Receipt confirmed',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Review purchase'}).click();await page.getByRole('button',{name:'Confirm transaction'}).click();
 await expect(page.getByText('Acquire tokens · Receipt confirmed')).toBeVisible();
});
test('checkout approves, signs, submits and displays indexed settlement separately from fulfillment',async({page})=>{
 await localWallet(page);await page.goto('/marketplace');await page.getByRole('button',{name:'Connect wallet',exact:true}).click();
 await page.getByRole('button',{name:'Review purchase'}).first().click();const dialog=page.getByRole('dialog');
 await expect(dialog).toBeVisible();await dialog.getByRole('button',{name:'Prepare order'}).click();
 await expect(dialog.getByRole('button',{name:/^(Approve MUD|Sign order)$/})).toBeVisible();
 const approve=dialog.getByRole('button',{name:'Approve MUD',exact:true});if(await approve.isVisible())await approve.click();
 await dialog.getByRole('button',{name:'Sign order'}).click();await dialog.getByRole('button',{name:'Submit payment'}).click();
 await expect(dialog.getByText('Marketplace payment · Receipt confirmed')).toBeVisible();
 await rpc('hardhat_mine',['0x4']);await expect(dialog.getByText('FULFILLED',{exact:true})).toBeVisible({timeout:30000});
 await dialog.getByRole('link',{name:'Track this order'}).click();await expect(page.getByRole('heading',{name:'FULFILLED',exact:true})).toBeVisible();
 await page.screenshot({path:'test-results/verified-order.png',fullPage:true});
});
