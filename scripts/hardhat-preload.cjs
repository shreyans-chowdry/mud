// Keep compiler/telemetry/config caches inside the checkout on every OS.
const path = require('node:path');
const resolved = require.resolve('env-paths');
const original = require(resolved);
function scoped(name, options) {
 if (!['hardhat', 'buidler'].includes(name)) return original(name, options);
 const root = path.resolve(__dirname, '../runtime/tool-cache');
 return Object.fromEntries(['config','cache','data','log','temp'].map(k => [k, path.join(root,k)]));
}
scoped.default = scoped;
require.cache[resolved].exports = scoped;
process.env.HARDHAT_DISABLE_TELEMETRY_PROMPT = 'true';
