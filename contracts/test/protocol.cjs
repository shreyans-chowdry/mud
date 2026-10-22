const { expect } = require('chai');
const { ethers, network } = require('hardhat');
const fc = require('fast-check');
const W = 10n ** 18n;
async function deployed(name, ...args) { const c = await (await ethers.getContractFactory(name)).deploy(...args); await c.waitForDeployment(); return c; }
async function setup(opts={}) {
 const [owner, buyer, merchant, attacker] = await ethers.getSigners();
 const collateral = await deployed('MockCollateral', opts.decimals || 6);
 const config = await deployed('MudProtocolConfig', owner.address, 10n**15n);
 const treasury = await deployed('MudTreasury', owner.address, collateral.target);
 const token = await deployed('MudTokenAMM','Mud','MUD',collateral.target,config.target,treasury.target,owner.address,owner.address,100000n,1000n,10n**27n);
 const feed = await deployed('MockFeed',8,100000000);
 const oracle = await deployed('MudPriceOracle',feed.target,ethers.ZeroAddress,3600,95000000,105000000);
 const market = await deployed('MudMarketplace',owner.address,owner.address,token.target,oracle.target);
 const now = (await ethers.provider.getBlock('latest')).timestamp;
 await collateral.mint(buyer.address,10n**15n);
 await collateral.connect(buyer).approve(token.target,ethers.MaxUint256);
 return {owner,buyer,merchant,attacker,collateral,config,treasury,token,feed,oracle,market,deadline: now+3600};
}
async function buy(f, amount=1000000000n) { const q=await f.token.quoteBuy(amount); await f.token.connect(f.buyer).buyTokens(amount,q[0],f.deadline); return q[0]; }
function sqrt(n) { if(n<2n)return n; let x=n,y=(x+1n)/2n; while(y<x){x=y;y=(x+n/x)/2n;}return x; }
function potential(s) { return 100000n*s/W+2000n*(s*sqrt(s*W)/W)/(3n*W); }
const types={Order:[{name:'orderId',type:'bytes32'},{name:'productId',type:'uint256'},{name:'buyer',type:'address'},{name:'maxMudAmount',type:'uint256'},{name:'deadline',type:'uint256'},{name:'nonce',type:'uint256'}]};

describe('Integrated curve: executable mathematics and conservation',function(){
 it('quotes the greatest affordable integrated output, not a spot division',async()=>{
  const f=await setup(); const q=await f.token.quoteBuy(1000000000n); const s=q[0];
  expect(potential(s)).lte(1000000000n); expect(potential(s+1n)).gt(1000000000n);
  expect(s).lt(1000000000n*W/100000n);
  expect(await f.token.calculateMintTarget(1000000000n)).eq(s);
  expect(await f.token.getSpotPrice()).eq(100000n);
  await buy(f); expect(await f.token.totalSupply()).eq(s); expect(await f.token.getCirculatingSupply()).eq(s);
  expect(await f.token.curveAccountedSupply()).eq(s);
 });
 it('fuzzes mint/burn and no-profit roundtrips with independent integer arithmetic',async()=>{
  const f=await setup();
  await fc.assert(fc.asyncProperty(fc.bigInt({min:1n,max:10n**11n}),async amount=>{
   const before=await f.collateral.balanceOf(f.buyer.address); const out=await buy(f,amount);
   expect(potential(out)).lte(amount); expect(potential(out+1n)).gt(amount);
   const [refund,fee,gross]=await f.token.quoteSell(out);
   expect(gross).eq(potential(out)); expect(refund+fee).eq(gross);
   expect(await f.token.calculateBurnRefund(out)).eq(refund);
   await f.token.connect(f.buyer).sellTokens(out,refund,f.deadline);
   expect(await f.collateral.balanceOf(f.buyer.address)).lte(before);
   expect(await f.token.totalSupply()).eq(0); expect(await f.token.reserveHealthy()).eq(true);
  }),{numRuns:40,seed:424242});
 });
 it('preserves reserve coverage across deterministic adversarial buy/sell/burn sequences',async()=>{
  const f=await setup(); let supply=0n;
  for(let i=1;i<=70;i++) {
   if(i%3===0 && supply>0n){const a=supply/7n; await f.token.connect(f.buyer).burn(a); supply-=a;}
   else if(i%4===0 && supply>0n){const a=supply/5n; await f.token.connect(f.buyer).sellTokens(a,0,f.deadline); supply-=a;}
   else {supply+=await buy(f,BigInt(i)*100003n);}
   expect(await f.token.totalSupply()).eq(supply);
   expect(await f.token.grossRedemptionLiability()).eq(potential(supply));
   expect(await f.token.getReserveBalance()).gte(potential(supply)+await f.token.accruedFees());
  }
 });
 it('rejects zero, dust redemption, over-redemption, oversized input, slippage and expired deadlines',async()=>{
  const f=await setup();
  await expect(f.token.quoteBuy(0)).revertedWithCustomError(f.token,'InvalidTrade');
  await expect(f.token.quoteBuy(10n**15n+1n)).reverted;
  await expect(f.token.quoteSell(1)).reverted;
  await expect(f.token.connect(f.buyer).buyTokens(100,ethers.MaxUint256,f.deadline)).revertedWithCustomError(f.token,'Slippage');
  await expect(f.token.connect(f.buyer).buyTokens(100,0,0)).revertedWithCustomError(f.token,'Expired');
  await buy(f);
  await expect(f.token.quoteSell(1)).reverted;
  await expect(f.token.quoteSell((await f.token.totalSupply())+1n)).reverted;
  await expect(f.token.connect(f.buyer).sellTokens(W,ethers.MaxUint256,f.deadline)).revertedWithCustomError(f.token,'Slippage');
  await expect(f.token.connect(f.buyer).sellTokens(W,0,0)).revertedWithCustomError(f.token,'Expired');
 });
 it('rejects transfer taxes, failing transfers, negative rebases and reentrant callbacks',async()=>{
  const f=await setup(); await f.collateral.setTax(100);
  await expect(f.token.connect(f.buyer).buyTokens(1000000,0,f.deadline)).revertedWithCustomError(f.token,'UnsupportedCollateral');
  expect(await f.token.totalSupply()).eq(0);
  await f.collateral.setTax(0); await f.collateral.setFail(true);
  await expect(f.token.connect(f.buyer).buyTokens(1000000,0,f.deadline)).reverted;
  await f.collateral.setFail(false);
  await f.collateral.setCallback(f.token.target,f.token.interface.encodeFunctionData('buyTokens',[1,0,f.deadline]));
  const amount=await buy(f); expect(await f.collateral.callbackSucceeded()).eq(false);
  await f.collateral.setTax(100);
  await expect(f.token.connect(f.buyer).sellTokens(amount,0,f.deadline)).revertedWithCustomError(f.token,'UnsupportedCollateral');
  await f.collateral.setTax(0); await f.collateral.confiscate(f.token.target,1000);
  expect(await f.token.reserveHealthy()).eq(false);
  await expect(f.token.connect(f.buyer).sellTokens(amount,0,f.deadline)).revertedWithCustomError(f.token,'Insolvent');
 });
 it('separates fees and allows treasury collection without reducing claim coverage',async()=>{
  const f=await setup(); const out=await buy(f); await f.token.connect(f.buyer).sellTokens(out/2n,0,f.deadline);
  const fees=await f.token.accruedFees(); expect(fees).gt(0);
  await expect(f.token.connect(f.attacker).collectFees()).revertedWithCustomError(f.token,'Unauthorized');
  await f.treasury.collect(f.token.target); expect(await f.collateral.balanceOf(f.treasury.target)).eq(fees);
  expect(await f.token.accruedFees()).eq(0); expect(await f.token.totalFeesCollected()).eq(fees);
  expect(await f.token.reserveHealthy()).eq(true);
  await expect(f.treasury.connect(f.attacker).withdraw(f.attacker.address,fees)).reverted;
  await f.treasury.withdraw(f.owner.address,fees);
  expect(await f.treasury.withdrawn()).eq(fees);
 });
 it('bounds extreme supply and enforces immutable parameter constraints',async()=>{
  const f=await setup(); const cap=10n**27n; const cost=await f.token.curvePotential(cap);
  await f.collateral.mint(f.buyer.address,cost);
  const small=await deployed('MudTokenAMM','Mud','MUD',f.collateral.target,f.config.target,f.treasury.target,f.owner.address,f.owner.address,1,0,10n**22n);
  await f.collateral.connect(f.buyer).approve(small.target,ethers.MaxUint256);
  await small.connect(f.buyer).buyTokens(10000,0,f.deadline);
  expect(await small.totalSupply()).eq(10n**22n);
  await expect(small.quoteBuy(1)).reverted;
  expect(await f.token.curvePotential(cap)).eq(potential(cap));
  await expect(f.token.curvePotential(cap+1n)).reverted;
  await expect(deployed('MudTokenAMM','Mud','MUD',f.collateral.target,f.config.target,f.treasury.target,f.owner.address,f.owner.address,1,10n**18n,cap)).reverted;
 });
 it('tests guardian pause, two-step ownership and delayed bounded config',async()=>{
  const f=await setup(); await expect(f.token.connect(f.attacker).pause()).reverted;
  await f.token.pause(); await expect(f.token.connect(f.buyer).buyTokens(1,0,f.deadline)).reverted;
  await expect(f.token.connect(f.attacker).unpause()).reverted; await f.token.unpause();
  await expect(f.config.propose(101,50,1000)).reverted;
  await f.config.propose(10,75,1000000000);
  await expect(f.config.execute(10,75,1000000000)).reverted;
  await network.provider.send('evm_increaseTime',[172801]); await network.provider.send('evm_mine');
  await f.config.execute(10,75,1000000000); expect(await f.config.exitFeeBps()).eq(75);
  await expect(f.config.execute(10,75,1000000000)).reverted;
  await f.token.transferOwnership(f.attacker.address); expect(await f.token.owner()).eq(f.owner.address);
  await f.token.connect(f.attacker).acceptOwnership(); expect(await f.token.owner()).eq(f.attacker.address);
 });
});

describe('Airdrop: double-hash leaves, sorted pairs and one-way claims',function(){
 it('requires full backing, checks proofs/amount/index, prevents replay and freezes root',async()=>{
  const f=await setup(); const amount=10n*W;
  const leaf=ethers.keccak256(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(['uint256','address','uint256'],[9999,f.buyer.address,amount])));
  const drop=await deployed('MudAirdrop',f.owner.address,f.token.target,leaf,amount,f.deadline);
  await expect(drop.claim(9999,f.buyer.address,amount,[])).reverted;
  await buy(f); await f.token.connect(f.buyer).transfer(drop.target,amount);
  await expect(drop.claim(9999,f.buyer.address,amount-1n,[])).reverted;
  await expect(drop.claim(10000,f.buyer.address,amount,[])).reverted;
  await expect(drop.claim(9999,f.attacker.address,amount,[])).reverted;
  await drop.claim(9999,f.buyer.address,amount,[]); expect(await drop.isClaimed(9999)).eq(true);
  await expect(drop.claim(9999,f.buyer.address,amount,[])).reverted;
  await expect(drop.setRoot(ethers.id('changed'))).reverted;
  await expect(drop.recover(f.owner.address)).reverted;
  await network.provider.send('evm_increaseTime',[3601]); await network.provider.send('evm_mine');
  await drop.recover(f.owner.address);
 });
});

describe('Oracle and marketplace: authentic settlement and replay boundaries',function(){
 async function listed(){ const f=await setup(); await buy(f,10000000000n); await f.market.connect(f.merchant).registerMerchant();
  await f.market.connect(f.merchant).createProduct(1000000,10,3,'ipfs://product');
  await f.token.connect(f.buyer).approve(f.market.target,ethers.MaxUint256); return f; }
 it('pays exactly 95%, burns 5%, lowers liability and respects inventory/limits',async()=>{
  const f=await listed(); const [payment]=await f.market.quoteProduct(1); const burned=payment*500n/10000n;
  const s=await f.token.totalSupply(),r=await f.token.getReserveBalance(),l=await f.token.grossRedemptionLiability();
  await expect(f.market.connect(f.buyer).purchaseItem(1,payment-1n,f.deadline)).reverted;
  await expect(f.market.connect(f.buyer).purchaseItem(1,payment,f.deadline)).emit(f.market,'ItemPurchased').withArgs(1,f.buyer.address,f.merchant.address,payment,burned);
  expect(await f.token.balanceOf(f.merchant.address)).eq(payment-burned);
  expect(await f.token.totalSupply()).eq(s-burned); expect(await f.token.getReserveBalance()).eq(r);
  expect(await f.token.grossRedemptionLiability()).lt(l); expect(await f.token.reserveHealthy()).eq(true);
  await f.token.connect(f.buyer).sellTokens((await f.token.balanceOf(f.buyer.address))/2n,0,f.deadline);
  expect(await f.token.reserveHealthy()).eq(true);
  for(let i=0;i<2;i++) await f.market.connect(f.buyer).purchaseItem(1,ethers.MaxUint256,f.deadline);
  await expect(f.market.connect(f.buyer).purchaseItem(1,ethers.MaxUint256,f.deadline)).reverted;
  await expect(f.market.connect(f.attacker).updateProduct(1,1,1,1,true,'x')).reverted;
  await f.market.connect(f.merchant).delistProduct(1); await expect(f.market.quoteProduct(1)).reverted;
 });
 it('verifies buyer-signed EIP-712 orders and rejects reuse and wrong chain/contract/nonce',async()=>{
  const f=await listed(); const domain={name:'MUD Marketplace',version:'1',chainId:31337,verifyingContract:f.market.target};
  const order={orderId:ethers.id('order-1'),productId:1,buyer:f.buyer.address,maxMudAmount:10n**24n,deadline:f.deadline,nonce:0};
  for(const bad of [{...domain,chainId:8453},{...domain,verifyingContract:f.token.target}]){
   const sig=await f.buyer.signTypedData(bad,types,order);
   await expect(f.market.connect(f.buyer).purchaseOrder(order,sig)).reverted;
  }
  const sig=await f.buyer.signTypedData(domain,types,order);
  expect(await f.market.hashOrder(order)).eq(ethers.TypedDataEncoder.hash(domain,types,order));
  await expect(f.market.connect(f.buyer).purchaseOrder(order,sig)).emit(f.market,'OrderSettled');
  await expect(f.market.connect(f.buyer).purchaseOrder(order,sig)).reverted;
  await expect(f.market.connect(f.attacker).purchaseOrder(order,sig)).reverted;
  const stale={...order,orderId:ethers.id('other')};
  await expect(f.market.connect(f.buyer).purchaseOrder(stale,await f.buyer.signTypedData(domain,types,stale))).reverted;
 });
 it('rejects invalid, future, stale, depegged and incomplete oracle answers',async()=>{
  const f=await listed(); const now=(await ethers.provider.getBlock('latest')).timestamp;
  for(const [a,t,r,ar] of [[0,now,2,2],[-1,now,2,2],[100000000,now-3601,2,2],[100000000,now+999,2,2],[80000000,now,2,2],[100000000,now,3,2]]){
   await f.feed.set(a,now,t,r,ar); await expect(f.market.quoteProduct(1)).reverted;
  }
  await f.feed.set(100000000,now,now,2,2); const [price]=await f.oracle.read(); expect(price).eq(100000000);
  await f.market.pause(); await expect(f.market.connect(f.buyer).purchaseItem(1,ethers.MaxUint256,f.deadline)).reverted;
 });
 it('guards L2 sequencer downtime and restart grace period, and normalizes decimals',async()=>{
  const f=await setup(); const seq=await deployed('MockFeed',0,1); const feed=await deployed('MockFeed',6,1000000);
  const oracle=await deployed('MudPriceOracle',feed.target,seq.target,10000,95000000,105000000);
  await expect(oracle.read()).reverted;
  const now=(await ethers.provider.getBlock('latest')).timestamp;
  await seq.set(0,now,now,1,1); await expect(oracle.read()).reverted;
  await network.provider.send('evm_increaseTime',[3601]); await network.provider.send('evm_mine');
  expect((await oracle.read())[0]).eq(100000000);
 });
});

describe('Administrative merchant containment',function(){
 it('prevents a merchant from bypassing administrative deactivation by registering again',async()=>{
  const f=await setup();await f.market.connect(f.merchant).registerMerchant();
  await f.market.setMerchant(f.merchant.address,false);
  await expect(f.market.connect(f.merchant).registerMerchant()).revertedWithCustomError(f.market,'Unauthorized');
  await f.market.setMerchant(f.merchant.address,true);
  await f.market.connect(f.merchant).deactivateMerchant();
  await f.market.connect(f.merchant).registerMerchant();
  expect(await f.market.merchants(f.merchant.address)).eq(true);
 });
});

describe('Dust cycles and nonzero-supply inversion',function(){
 it('cannot extract collateral through repeated one-atom roundtrips',async()=>{
  const f=await setup();const initial=await f.collateral.balanceOf(f.buyer.address);
  for(let i=0;i<30;i++){
   const minted=await buy(f,1n);const [refund]=await f.token.quoteSell(minted);
   expect(refund).lte(1n);await f.token.connect(f.buyer).sellTokens(minted,refund,f.deadline);
  }
  expect(await f.collateral.balanceOf(f.buyer.address)).lte(initial);
  expect(await f.token.totalSupply()).eq(0);expect(await f.token.reserveHealthy()).eq(true);
 });
 it('fuzzes integrated inversion from changing supply and validates min-output protection',async()=>{
  const f=await setup();
  await fc.assert(fc.asyncProperty(fc.bigInt({min:1n,max:1000000000n}),async input=>{
   const start=await f.token.totalSupply();const [out,,cost]=await f.token.quoteBuy(input);
   expect(potential(start+out)-potential(start)).eq(cost);expect(cost).lte(input);
   expect(potential(start+out+1n)-potential(start)).gt(input);
   await expect(f.token.connect(f.buyer).buyTokens(input,out+1n,f.deadline)).revertedWithCustomError(f.token,'Slippage');
   await buy(f,input);
  }),{numRuns:25,seed:20261017});
 });
});
