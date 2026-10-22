import { OrderTracking } from '@/components/OrderTracking';
export default async function Page({params}:{params:Promise<{orderId:string}>}){const {orderId}=await params;return <OrderTracking id={orderId}/>;}
