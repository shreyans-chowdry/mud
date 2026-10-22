const fs=require('node:fs');
const hre=require('hardhat');
const {ethers}=hre;
async function main(){
 const chain=Number((await ethers.provider.getNetwork()).chainId);
 const policy=require('../../config/chains.json')[String(chain)];
 if(!policy)throw Error('Unsupported chain');
 const local=chain===31337;
 if(!local && (!process.env.EXPECTED_CHAIN_ID || Number(process.env.EXPECTED_CHAIN_ID)!==chain))throw Error('Explicit EXPECTED_CHAIN_ID required');
 if(policy.environment==='mainnet')throw Error('Mainnet broadcasting intentionally disabled: independent review and separate release workflow required');
 const fixtures=process.env.MUD_SEED_FIXTURES==='1';
 if(fixtures&&!local)throw Error('Test fixture seeding is forbidden outside chain 31337');
 const merkleFile=process.env.MERKLE_FILE||(fixtures?'tests/fixtures/eligibility.local.json':undefined);
 if(!merkleFile)throw Error('MERKLE_FILE must name an explicit reviewed manifest; test fixtures require MUD_SEED_FIXTURES=1');
 const merkle=JSON.parse(fs.readFileSync(merkleFile));
 if(!/^0x[0-9a-fA-F]{64}$/.test(merkle.root)||BigInt(merkle.totalAllocation)<=0n)throw Error('Invalid Merkle manifest');
 const [signer]=await ethers.getSigners(); if(!signer)throw Error('No configured deployer');
 const owner=local?signer.address:process.env.PROTOCOL_OWNER;
 const guardian=local?signer.address:process.env.PROTOCOL_GUARDIAN;
 for(const a of [owner,guardian])if(!ethers.isAddress(a)||a===ethers.ZeroAddress)throw Error('Owner and guardian required');
 async function deploy(name,...args){ const c=await(await ethers.getContractFactory(name)).deploy(...args); await c.waitForDeployment(); return c; }
 let collateral=process.env.COLLATERAL_ADDRESS,feed=process.env.ORACLE_FEED,seq=process.env.SEQUENCER_FEED;
 if(local){collateral=(await deploy('MockCollateral',6)).target; feed=(await deploy('MockFeed',8,100000000)).target; seq=ethers.ZeroAddress;}
 else for(const a of [collateral,feed,seq])if(!ethers.isAddress(a)||a===ethers.ZeroAddress||await ethers.provider.getCode(a)==='0x')throw Error('Chain-specific collateral, price feed and sequencer required');
 const decimals=await new ethers.Contract(collateral,['function decimals() view returns(uint8)'],signer).decimals();
 if(Number(decimals)!==policy.collateralDecimals)throw Error('Unexpected collateral decimals');
 const startBlock=await ethers.provider.getBlockNumber();
 const treasury=await deploy('MudTreasury',owner,collateral);
 const config=await deploy('MudProtocolConfig',owner,BigInt(process.env.MAX_TRANSACTION||'1000000000000'));
 const token=await deploy('MudTokenAMM',process.env.TOKEN_NAME||'Mud',process.env.TOKEN_SYMBOL||'MUD',collateral,config.target,treasury.target,owner,guardian,BigInt(process.env.BASE_PRICE||'100000'),BigInt(process.env.SLOPE||'1000'),BigInt(process.env.MAX_SUPPLY||'1000000000000000000000000000'));
 const oracle=await deploy('MudPriceOracle',feed,seq,Number(process.env.ORACLE_MAX_AGE||3600),95000000,105000000);
 await oracle.read();
 const market=await deploy('MudMarketplace',owner,guardian,token.target,oracle.target);
 const expiry=(await ethers.provider.getBlock('latest')).timestamp+30*86400;
 const airdrop=await deploy('MudAirdrop',owner,token.target,merkle.root,BigInt(merkle.totalAllocation),expiry);
 if(local&&fixtures){
  const [admin,buyer,merchant]=await ethers.getSigners();
  const col=await ethers.getContractAt('MockCollateral',collateral);
  await (await col.mint(admin.address,100000000000n)).wait();
  await (await col.mint(buyer.address,100000000000n)).wait();
  await(await col.approve(token.target,ethers.MaxUint256)).wait();
  await(await token.buyTokens(10000000000n,0,expiry)).wait();
  await(await token.transfer(airdrop.target,BigInt(merkle.totalAllocation))).wait();
  await(await market.connect(merchant).registerMerchant()).wait();
  for(const p of [{usd:12000000,uri:'mud://research-pass'},{usd:5000000,uri:'mud://compute-credit'},{usd:25000000,uri:'mud://design-library'}])
   await(await market.connect(merchant).createProduct(p.usd,1000,100,p.uri)).wait();
 }
 const manifest={abiVersion:1,dataSource:local?'test-fixtures':'onchain',chainId:chain,startBlock,environment:policy.environment,tokenName:await token.name(),tokenSymbol:await token.symbol(),collateralDecimals:Number(decimals),...policy,
  contracts:{collateral,token:token.target,config:config.target,treasury:treasury.target,oracle:oracle.target,marketplace:market.target,airdrop:airdrop.target,feed,sequencer:seq},merkleRoot:merkle.root};
 fs.mkdirSync('deployments',{recursive:true});fs.writeFileSync(`deployments/${chain}.json`,JSON.stringify(manifest,null,2)+'\n');
 fs.writeFileSync('frontend/public/deployment.json',JSON.stringify(manifest,null,2)+'\n');
 console.log(JSON.stringify(manifest,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
