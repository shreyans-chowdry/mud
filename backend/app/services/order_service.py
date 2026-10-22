import time
import uuid
from web3 import Web3
from ..models import Order, OrderTransition
from ..metrics import ORDER_TRANSITIONS

ORDER_FIELDS = [{'name': name, 'type': type_} for name, type_ in [
    ('orderId', 'bytes32'), ('productId', 'uint256'), ('buyer', 'address'),
    ('maxMudAmount', 'uint256'), ('deadline', 'uint256'), ('nonce', 'uint256')]]


def transition(session, order, state, reason):
    if order.status == state:
        return
    order.transition_sequence = (order.transition_sequence or 0) + 1
    session.add(OrderTransition(order_id=order.id, previous=order.status, current=state, reason=reason,
                                sequence=order.transition_sequence))
    order.status = state
    order.updated_at = int(time.time())
    ORDER_TRANSITIONS.labels(state=state).inc()


def typed_data(chain_id, contract, order_hash, product_id, buyer, max_mud, deadline, nonce):
    return {'types': {'EIP712Domain': [
        {'name': 'name', 'type': 'string'}, {'name': 'version', 'type': 'string'},
        {'name': 'chainId', 'type': 'uint256'}, {'name': 'verifyingContract', 'type': 'address'}], 'Order': ORDER_FIELDS},
        'primaryType': 'Order', 'domain': {'name': 'MUD Marketplace', 'version': '1', 'chainId': chain_id, 'verifyingContract': contract},
        'message': {'orderId': order_hash, 'productId': str(product_id), 'buyer': buyer,
                    'maxMudAmount': str(max_mud), 'deadline': str(deadline), 'nonce': str(nonce)}}


async def create_order(session, chain, request):
    market = chain.contract('marketplace')
    block = await chain.block('latest')
    quote = await market.functions.quoteProduct(int(request.product_id)).call(block_identifier=block['number'])
    if int(request.max_mud_amount) < quote[0]:
        raise ValueError('maximum payment below current quote')
    product = await market.functions.products(int(request.product_id)).call(block_identifier=block['number'])
    bought = await market.functions.purchased(int(request.product_id), request.buyer).call(block_identifier=block['number'])
    if bought >= product[3]:
        raise ValueError('buyer purchase limit reached')
    nonce = await market.functions.nonces(request.buyer).call(block_identifier=block['number'])
    id_ = str(uuid.uuid4())
    order_hash = Web3.to_hex(Web3.keccak(text=id_))
    deadline = block['timestamp']+request.ttl_seconds
    data = typed_data(chain.settings.chain_id, market.address, order_hash, request.product_id, request.buyer,
                      request.max_mud_amount, deadline, nonce)
    order = Order(id=id_, order_hash=order_hash, chain_id=chain.settings.chain_id, verifying_contract=market.address,
                  product_id=request.product_id, buyer=request.buyer, max_mud_amount=request.max_mud_amount,
                  nonce=str(nonce), deadline=deadline, status='CREATED', fulfillment_status='NOT_READY', typed_data=data)
    session.add(order)
    transition(session, order, 'AWAITING_PAYMENT', 'buyer must sign and submit on chain')
    await session.flush()
    return order


def order_view(order):
    return {'id': order.id, 'order_hash': order.order_hash, 'status': order.status, 'fulfillment_status': order.fulfillment_status,
            'chain_id': order.chain_id, 'product_id': order.product_id, 'buyer': order.buyer, 'max_mud_amount': order.max_mud_amount,
            'paid_amount': order.paid_amount, 'deadline': order.deadline, 'transaction_hash': order.settlement_tx,
            'typed_data': order.typed_data, 'updated_at': order.updated_at, 'authoritative_payment_source': 'canonical indexed OrderSettled event'}
