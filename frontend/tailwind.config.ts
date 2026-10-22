import type { Config } from 'tailwindcss';
export default { content:['./app/**/*.{ts,tsx}','./components/**/*.{ts,tsx}','./providers/**/*.{ts,tsx}'], theme:{extend:{colors:{amber:'#edc36b',graphite:'#101213'}}}, plugins:[] } satisfies Config;
