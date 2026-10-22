import { createConfig, http } from 'wagmi';
import { injected } from '@wagmi/core';
import { hardhat, base, baseSepolia, arbitrum, arbitrumSepolia } from 'wagmi/chains';
export const wagmiConfig = createConfig({
  chains:[hardhat,baseSepolia,arbitrumSepolia,base,arbitrum], connectors:[injected()], ssr:true,
  transports:{[hardhat.id]:http(process.env.NEXT_PUBLIC_LOCAL_RPC || 'http://127.0.0.1:8545'),
    [base.id]:http(process.env.NEXT_PUBLIC_BASE_RPC),[baseSepolia.id]:http(process.env.NEXT_PUBLIC_BASE_SEPOLIA_RPC),
    [arbitrum.id]:http(process.env.NEXT_PUBLIC_ARBITRUM_RPC),[arbitrumSepolia.id]:http(process.env.NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC)}
});
