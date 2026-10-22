'use client';
import { useReadContract } from 'wagmi';
import { MudTokenAMMAbi } from '@/lib/abi';
import { useProtocol } from '@/providers/Providers';
import { amount } from '@/lib/format';
const W=10n**18n;
function sqrt(n:bigint){if(n<2n)return n;let x=n,y=(x+1n)/2n;while(y<x){x=y;y=(x+n/x)/2n;}return x;}
export function CurveChart(){
 const {deployment:d}=useProtocol();
 const supply=useReadContract({address:d?.contracts.token,abi:MudTokenAMMAbi,functionName:'totalSupply',chainId:d?.chainId,query:{enabled:!!d,refetchInterval:10000}});
 const base=useReadContract({address:d?.contracts.token,abi:MudTokenAMMAbi,functionName:'basePrice',chainId:d?.chainId,query:{enabled:!!d}});
 const slope=useReadContract({address:d?.contracts.token,abi:MudTokenAMMAbi,functionName:'slope',chainId:d?.chainId,query:{enabled:!!d}});
 const cap=useReadContract({address:d?.contracts.token,abi:MudTokenAMMAbi,functionName:'maxSupply',chainId:d?.chainId,query:{enabled:!!d}});
 const ready=supply.data!==undefined&&base.data!==undefined&&slope.data!==undefined&&cap.data!==undefined;
 if(!ready)return <div className="chart-empty"><div className="chart-grid"/><span>Connect to deployed contracts to view the curve.</span></div>;
 const s=supply.data!,p=base.data!,k=slope.data!,c=cap.data!;
 const range=s===0n?(1000n*W<c?1000n*W:c):(s*2n<c?s*2n:c);
 const price=(v:bigint)=>p+k*sqrt(v*W)/W;
 const max=price(range),min=p;
 const y=(v:bigint)=>205-Number((v-min)*16000n/(max-min||1n))/100;
 const points=Array.from({length:65},(_,i)=>{const v=range*BigInt(i)/64n;return `${40+i*8.75},${y(price(v))}`;}).join(' ');
 const marker=40+Number(s*56000n/range)/100;
 return <div className="chart-wrap"><div className="chart-axis"><span>{amount(max,d?.collateralDecimals||6,4)}</span><span>{amount((max+min)/2n,d?.collateralDecimals||6,4)}</span><span>{amount(min,d?.collateralDecimals||6,4)}</span></div><svg viewBox="0 0 650 250" role="img" aria-label="Marginal bonding curve model. Price rises with the square root of outstanding supply; this is not historical performance."><defs><linearGradient id="curve-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#edc36b" stopOpacity=".20"/><stop offset="100%" stopColor="#edc36b" stopOpacity="0"/></linearGradient></defs>{[45,85,125,165,205].map(v=><line key={v} x1="40" x2="600" y1={v} y2={v} stroke="#292c2c" strokeDasharray="3 5"/>)}{[40,180,320,460,600].map(v=><line key={v} x1={v} x2={v} y1="25" y2="205" stroke="#232626"/>)}<polygon points={`40,205 ${points} 600,205`} fill="url(#curve-fill)"/><polyline points={points} fill="none" stroke="#edc36b" strokeWidth="2.5"/><line x1={marker} x2={marker} y1="30" y2="205" stroke="#8d784e" strokeDasharray="4 5"/><circle cx={marker} cy={y(price(s))} r="5" fill="#edc36b" stroke="#161919" strokeWidth="3"/><text x="40" y="236" fill="#727977" fontSize="10">0</text><text x="320" y="236" fill="#727977" fontSize="10" textAnchor="middle">{amount(range/2n,18,0)}</text><text x="600" y="236" fill="#727977" fontSize="10" textAnchor="end">{amount(range,18,0)} {d?.tokenSymbol}</text></svg><p className="chart-caption"><span><i/> Marginal price model</span><span>Outstanding supply →</span></p></div>;
}
