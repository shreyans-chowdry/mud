'use client';
export default function ErrorPage({reset}:{error:Error;reset:()=>void}){return <div className="panel empty"><h1>This view is unavailable.</h1><p>Your wallet and blockchain state remain independent of this page.</p><button className="button" onClick={reset}>Reload view</button></div>;}
