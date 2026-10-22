const fs=require('node:fs');
const {ethers}=require('ethers');
async function main(){
 const path=process.argv[2];if(!path)throw Error('Usage: node scripts/verify-chain.cjs deployments/CHAIN.json');
 const m=JSON.parse(fs.readFileSync(path));const provider=new ethers.JsonRpcProvider(process.env.RPC_HTTP||'http://127.0.0.1:8545');
 if(Number((await provider.getNetwork()).chainId)!==m.chainId)throw Error('Wrong chain');
 for(const [name,address] of Object.entries(m.contracts)){
  if(name==='sequencer'&&m.chainId===31337&&address===ethers.ZeroAddress)continue;
  if(!ethers.isAddress(address)||await provider.getCode(address)==='0x')throw Error(`Missing contract: ${name}`);
 }
 console.log('Verified chain ID and deployed bytecode presence; use validate_deployment.py for interface/accounting checks.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
