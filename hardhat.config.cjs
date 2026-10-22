require('@nomicfoundation/hardhat-ethers');
require('@nomicfoundation/hardhat-chai-matchers');
require('solidity-coverage');
const { subtask } = require('hardhat/config');
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require('hardhat/builtin-tasks/task-names');
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }, _, runSuper) => {
  if (solcVersion === '0.8.24') return { compilerPath: require.resolve('solc/soljson.js'), isSolcJs: true, version: solcVersion, longVersion: require('solc').version() };
  return runSuper();
});
const remote = (chainId, key) => ({ chainId, url: process.env[key] || 'http://127.0.0.1:1', accounts: process.env.DEPLOYER_KEY ? [process.env.DEPLOYER_KEY] : [] });
module.exports = {
  solidity: { version: '0.8.24', settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: 'paris' } },
  paths: { sources: './contracts/src', tests: './contracts/test', cache: './contracts/cache', artifacts: './contracts/artifacts' },
  networks: { hardhat: { chainId: 31337, hardfork: 'cancun', blockGasLimit: 30000000, initialBaseFeePerGas: 0 }, localhost: { url: process.env.RPC_HTTP || 'http://127.0.0.1:8545', chainId: 31337 },
    baseSepolia: remote(84532, 'BASE_SEPOLIA_RPC'), arbitrumSepolia: remote(421614, 'ARBITRUM_SEPOLIA_RPC'),
    base: remote(8453, 'BASE_RPC'), arbitrum: remote(42161, 'ARBITRUM_RPC') },
  mocha: { timeout: 120000 }
};
