require('./hardhat-preload.cjs');
const preload = require('node:path').resolve(__dirname, 'hardhat-preload.cjs');
process.env.NODE_OPTIONS = [process.env.NODE_OPTIONS || '', '--require ' + JSON.stringify(preload)].join(' ').trim();
require('hardhat/internal/cli/bootstrap');
