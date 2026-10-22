import type { Metadata } from 'next';
import { Providers } from '@/providers/Providers';
import { Shell } from '@/components/Shell';
import './globals.css';
export const metadata:Metadata={title:'MUD — Economic Protocol',description:'A verifiable, collateral-backed on-chain economy. Trade, exchange and track every movement.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><Providers><Shell>{children}</Shell></Providers></body></html>;}
