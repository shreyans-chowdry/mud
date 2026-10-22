// Test container only: retain localhost origins while reaching the host's local services.
const net=require('node:net');
for(const port of [3000,8000,8001,8545])net.createServer(client=>{
 const upstream=net.connect(port,'host.docker.internal');
 client.on('error',()=>upstream.destroy());upstream.on('error',()=>client.destroy());
 client.pipe(upstream).pipe(client);
}).listen(port,'127.0.0.1');
