import { describe,it,expect } from 'vitest';
import { validateDeployment,verifyBackendDeployment } from '@/lib/deployment';
const address='0x1111111111111111111111111111111111111111';
const live={abiVersion:1,chainId:8453,name:'Base',environment:'mainnet',dataSource:'onchain',explorer:'https://basescan.org',confirmations:20,finalityDepth:128,collateralDecimals:6,tokenName:'Mud',tokenSymbol:'MUD',contracts:Object.fromEntries(['token','collateral','marketplace','airdrop','oracle','config','treasury','feed','sequencer'].map(k=>[k,address]))};
describe('Public deployment provenance',()=>{
 it('accepts explicit Base on-chain metadata',()=>expect(validateDeployment(live).chainId).toBe(8453));
 it('rejects local fixtures and testnet deployments in the default build',()=>{
  expect(()=>validateDeployment({...live,chainId:31337,environment:'local',dataSource:'test-fixtures'})).toThrow(/Test-network deployment is disabled/);
  expect(()=>validateDeployment({...live,chainId:84532,environment:'testnet'})).toThrow(/Test-network deployment is disabled/);
 });
 it('accepts explicitly opted-in local tests while retaining test provenance',()=>expect(validateDeployment({...live,chainId:31337,environment:'local',dataSource:'test-fixtures'},true).environment).toBe('local'));
 it('rejects fixture data labelled as mainnet and contradictory chain identities',()=>{
  expect(()=>validateDeployment({...live,dataSource:'test-fixtures'})).toThrow(/data source/);
  expect(()=>validateDeployment({...live,environment:'testnet'})).toThrow(/environment/);
 });
 it('rejects zero contracts and weak remote confirmation policies',()=>{
  expect(()=>validateDeployment({...live,contracts:{...live.contracts,token:'0x0000000000000000000000000000000000000000'}})).toThrow(/address/);
  expect(()=>validateDeployment({...live,confirmations:1,finalityDepth:3})).toThrow(/too weak/);
 });
 it('requires the API to verify the same chain and every configured contract',()=>{
  const d=validateDeployment(live);const status={status:'verified',chain_id:8453,abi_version:1,environment:'mainnet',data_source:'onchain',contracts:live.contracts};
  expect(()=>verifyBackendDeployment(d,status)).not.toThrow();
  expect(()=>verifyBackendDeployment(d,{...status,chain_id:31337})).toThrow(/does not match/);
  expect(()=>verifyBackendDeployment(d,{...status,contracts:{...live.contracts,marketplace:'0x2222222222222222222222222222222222222222'}})).toThrow(/do not match/);
 });
});
