import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { FlatCompat } = require('@eslint/eslintrc');
const compat = new FlatCompat({baseDirectory:import.meta.dirname});
const config = [...compat.extends('next/core-web-vitals','next/typescript'), {ignores:['.next/**','coverage/**','playwright-report/**','test-results/**','next-env.d.ts','lib/abi.ts']}];
export default config;
