const fs=require('node:fs');
const assert=require('node:assert/strict');
const {ethers,network}=require('hardhat');
const api=process.env.MUD_API_URL||'http://127.0.0.1:8000';
async function json(path,body){const r=await fetch(api+'/api/v1'+path,body?{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}:undefined);const data=await r.json();if(!r.ok)throw Error(JSON.stringify(data));return data;}
async function poll(id,target){for(let i=0;i<60;i++){const o=await json(`/marketplace/order/${id}/status`);if(target.includes(o.status))return o;if(o.status==='FULFILLMENT_FAILED')throw Error('Fulfillment exhausted retries');await new Promise(r=>setTimeout(r,1000));}throw Error('Indexer/fulfillment timeout');}
async function main(){
 if(Number((await ethers.provider.getNetwork()).chainId)!==31337)throw Error('Lifecycle only broadcasts to local chain 31337');
 await network.provider.send('evm_mine');
 const m=JSON.parse(fs.readFileSync('deployments/31337.json'));const [admin,buyer]=await ethers.getSigners();
 const c=await ethers.getContractAt('MockCollateral',m.contracts.collateral);
 const token=await ethers.getContractAt('MudTokenAMM',m.contracts.token);
 const market=await ethers.getContractAt('MudMarketplace',m.contracts.marketplace);
 const drop=await ethers.getContractAt('MudAirdrop',m.contracts.airdrop);
 const feed=await ethers.getContractAt('MockFeed',m.contracts.feed);
 let timestamp=(await ethers.provider.getBlock('latest')).timestamp;
 await(await feed.set(100000000,timestamp,timestamp,1,1)).wait();
 await(await c.mint(buyer.address,10000000000n)).wait();
 await(await c.connect(buyer).approve(token.target,1000000000n)).wait();
 const mint=await token.quoteBuy(1000000000n);const before=await token.balanceOf(buyer.address);
 const buyReceipt=await(await token.connect(buyer).buyTokens(1000000000n,mint[0],timestamp+600)).wait();
 assert.equal(await token.balanceOf(buyer.address),before+mint[0]);
 const sellAmount=mint[0]/10n;const sell=await token.quoteSell(sellAmount);const balance=await c.balanceOf(buyer.address);
 const sellReceipt=await(await token.connect(buyer).sellTokens(sellAmount,sell[0],timestamp+600)).wait();
 assert.equal(await c.balanceOf(buyer.address),balance+sell[0]);
 const claim=JSON.parse(fs.readFileSync('tests/fixtures/eligibility.local.json')).claims.find(r=>r.address.toLowerCase()===buyer.address.toLowerCase());
 let claimTx=null;
 if(!await drop.isClaimed(claim.index)){
  const r=await(await drop.claim(claim.index,claim.address,claim.allocation,claim.proof)).wait();claimTx=r.hash;
  await assert.rejects(()=>drop.claim(claim.index,claim.address,claim.allocation,claim.proof));
 }
 const [payment]=await market.quoteProduct(1);const max=payment*101n/100n+1n;
 const o=await json('/marketplace/create-order',{buyer:buyer.address,product_id:'1',max_mud_amount:max.toString(),ttl_seconds:600});
 const t=o.typed_data;const signature=await buyer.signTypedData(t.domain,{Order:t.types.Order},t.message);
 await(await token.connect(buyer).approve(market.target,max)).wait();
 const product=await market.products(1);const supply=await token.totalSupply();const merchantBefore=await token.balanceOf(product.merchant);
 const receipt=await(await market.connect(buyer).purchaseOrder(t.message,signature)).wait();
 const event=receipt.logs.map(l=>{try{return market.interface.parseLog(l);}catch{return null;}}).find(e=>e?.name==='ItemPurchased');
 assert(event);assert.equal(await token.totalSupply(),supply-event.args.mudBurned);
 assert.equal(await token.balanceOf(product.merchant),merchantBefore+event.args.mudPaid-event.args.mudBurned);
 assert(await token.reserveHealthy());
 await network.provider.send('hardhat_mine',['0x4']);
 const complete=await poll(o.id,['FULFILLED']);
 const activity=await json('/activity?limit=100');
 assert(activity.events.some(e=>e.tx_hash.toLowerCase()===receipt.hash.toLowerCase()&&e.event_type==='OrderSettled'));
 const report={chainId:31337,generatedAt:new Date().toISOString(),buyTx:buyReceipt.hash,sellTx:sellReceipt.hash,claimTx,purchaseTx:receipt.hash,orderId:o.id,status:complete.status,
  mudPaid:event.args.mudPaid.toString(),mudBurned:event.args.mudBurned.toString(),reserveHealthy:await token.reserveHealthy(),
  note:'Real local EVM receipts; fulfillment acknowledges a durable LOCAL entitlement record. PostgreSQL usage depends on runtime database configuration.'};
 fs.mkdirSync('runtime',{recursive:true});fs.writeFileSync('runtime/lifecycle.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
