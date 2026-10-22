import { describe,it,expect } from 'vitest';
import { amount,maximum,minimum,parseAmount,quoteIsStale } from '@/lib/format';
describe('Decimal-safe execution constraints',()=>{
 it('never passes amounts through Number or accepts precision it cannot represent',()=>{
  expect(parseAmount('9007199254740993.123456',6)).toBe(9007199254740993123456n);
  for(const s of ['-1','1e6','0','1.1234567',' 1','NaN','01'])expect(parseAmount(s,6)).toBeNull();
 });
 it('rounds minimum down and maximum up without floating-point drift',()=>{
  expect(minimum(101n,50)).toBe(100n);expect(maximum(101n,50)).toBe(102n);
  expect(amount(9007199254740993123456n,6,6)).toBe('9,007,199,254,740,993.123456');
 });
 it('rejects old and future-dated quote metadata',()=>{
  expect(quoteIsStale(1000,17000)).toBe(true);expect(quoteIsStale(1000,15000)).toBe(false);expect(quoteIsStale(20000,10000)).toBe(true);
 });
});
