import { isAddress, zeroAddress, type Address } from 'viem';
export type Deployment = {
 abiVersion:number;chainId:number;name:string;environment:'local'|'testnet'|'mainnet';dataSource:'onchain'|'test-fixtures';
 explorer:string;confirmations:number;finalityDepth:number;collateralDecimals:number;tokenName:string;tokenSymbol:string;
 contracts:Record<'token'|'collateral'|'marketplace'|'airdrop'|'oracle'|'config'|'treasury'|'feed'|'sequencer',Address>;
};
const environments:Record<number,string>={31337:'local',8453:'mainnet',84532:'testnet',42161:'mainnet',421614:'testnet'};
const modules=['token','collateral','marketplace','airdrop','oracle','config','treasury','feed','sequencer'] as const;
function record(value:unknown):value is Record<string,unknown>{return !!value&&typeof value==='object'&&!Array.isArray(value);}
export function validateDeployment(value:unknown,allowTestNetworks=false):Deployment{
 if(!record(value)||value.abiVersion!==1||typeof value.chainId!=='number'||!environments[value.chainId]||value.environment!==environments[value.chainId])throw Error('Deployment chain or environment is invalid.');
 const local=value.chainId===31337;
 if(value.environment!=='mainnet'&&!allowTestNetworks)throw Error('Test-network deployment is disabled in this build. Configure a live deployment.');
 if(value.dataSource!==(local?'test-fixtures':'onchain'))throw Error('Deployment data source is invalid.');
 if(!Number.isInteger(value.confirmations)||Number(value.confirmations)<1||!Number.isInteger(value.finalityDepth)||Number(value.finalityDepth)<Number(value.confirmations))throw Error('Deployment confirmation policy is invalid.');
 if(!local&&(Number(value.confirmations)<5||Number(value.finalityDepth)<64))throw Error('Remote confirmation policy is too weak.');
 if(!Number.isInteger(value.collateralDecimals)||Number(value.collateralDecimals)<6||Number(value.collateralDecimals)>18)throw Error('Collateral precision is invalid.');
 for(const field of ['name','tokenName','tokenSymbol'])if(typeof value[field]!=='string'||!String(value[field]).trim())throw Error('Deployment token identity is missing.');
 if(typeof value.explorer!=='string'||(!local&&!/^https:\/\//.test(value.explorer)))throw Error('Deployment explorer must use HTTPS.');
 if(!record(value.contracts))throw Error('Deployment contract addresses are missing.');
 for(const name of modules){const address=value.contracts[name];if(typeof address!=='string'||!isAddress(address)||(address.toLowerCase()===zeroAddress&&!(local&&name==='sequencer')))throw Error('Deployment has an invalid contract address.');}
 return value as Deployment;
}
export function verifyBackendDeployment(d:Deployment,value:unknown):void{
 if(!record(value)||value.status!=='verified'||value.chain_id!==d.chainId||value.abi_version!==d.abiVersion||value.environment!==d.environment||value.data_source!==d.dataSource||!record(value.contracts))throw Error('The API does not match the configured deployment.');
 for(const name of modules)if(typeof value.contracts[name]!=='string'||String(value.contracts[name]).toLowerCase()!==d.contracts[name].toLowerCase())throw Error('The API contract addresses do not match the configured deployment.');
}
