import { describe,it,expect,vi } from 'vitest';
import { render,screen } from '@testing-library/react';
import { OrderTracking } from '@/components/OrderTracking';
const state=vi.hoisted(()=>({status:'REORGED',fulfillment:'REORG_REVIEW'}));
vi.mock('@/providers/Providers',()=>({useProtocol:()=>({deployment:{chainId:31337,tokenSymbol:'MUD',explorer:'',contracts:{marketplace:'0x1111111111111111111111111111111111111111'}}})}));
vi.mock('@tanstack/react-query',()=>({useQuery:()=>({isPending:false,error:null,data:{id:'one',status:state.status,fulfillment_status:state.fulfillment,buyer:'0x1111111111111111111111111111111111111111',product_id:'1',max_mud_amount:'1000000000000000000',paid_amount:null,chain_id:31337,transaction_hash:null,history:[]}})}));
describe('Durable order state',()=>{
 it('shows reorgs explicitly and never represents an orphaned payment as delivered',()=>{render(<OrderTracking id="one"/>);expect(screen.getByText(/payment was removed/)).toBeInTheDocument();expect(screen.getByText('REORG_REVIEW')).toBeInTheDocument();});
 it('keeps fulfillment failure distinct from settlement',()=>{state.status='FULFILLMENT_FAILED';state.fulfillment='FAILED';render(<OrderTracking id="one"/>);expect(screen.getByText(/digital delivery failed/)).toBeInTheDocument();});
});
