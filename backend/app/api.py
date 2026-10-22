from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select
from web3 import Web3
from .models import Event, Order, OrderTransition
from .schemas import CreateOrder, VerifyProof, parse_amount
from .services.order_service import create_order, order_view
from .metrics import FAILED_TRANSACTIONS

router = APIRouter(prefix='/api/v1')


@router.get('/deployment')
async def deployment(request: Request):
    chain = request.app.state.chain
    await chain.validate()
    manifest = chain.manifest
    block = await chain.block('latest')
    return {'status': 'verified', 'chain_id': request.app.state.settings.chain_id,
            'abi_version': manifest['abiVersion'], 'environment': manifest['environment'],
            'data_source': manifest.get('dataSource', 'test-fixtures'), 'contracts': manifest['contracts'],
            'block_number': block['number'], 'block_hash': block['hash']}


@router.get('/curve/spot-price')
async def spot(request: Request):
    return await request.app.state.curve.spot()


@router.get('/curve/quote-buy')
async def buy(request: Request, collateral_amount: str = Query(min_length=1, max_length=78)):
    return await request.app.state.curve.quote('buy', parse_amount(collateral_amount))


@router.get('/curve/quote-sell')
async def sell(request: Request, mud_amount: str = Query(min_length=1, max_length=78)):
    return await request.app.state.curve.quote('sell', parse_amount(mud_amount))


@router.get('/airdrop/eligibility/{address}')
async def eligibility(address: str, request: Request):
    if not Web3.is_address(address):
        raise ValueError('invalid Ethereum address')
    if request.app.state.settings.eligibility_file is None:
        raise HTTPException(503, 'Eligibility dataset is not configured; no claim decision is available')
    result = request.app.state.airdrop.eligibility(address)
    contract = request.app.state.chain.contract('airdrop')
    root = await contract.functions.merkleRoot().call()
    result['root_matches_chain'] = Web3.to_hex(root) == result['root']
    result['expiry'] = await contract.functions.expiry().call()
    result['claimed'] = await contract.functions.isClaimed(result['claim']['index']).call() if result['claim'] else False
    return result


@router.post('/airdrop/verify-proof')
async def proof(body: VerifyProof, request: Request):
    if request.app.state.settings.eligibility_file is None:
        raise HTTPException(503, 'Eligibility dataset is not configured; no proof decision is available')
    result = request.app.state.airdrop.verify(body)
    root = await request.app.state.chain.contract('airdrop').functions.merkleRoot().call()
    result['root_matches_chain'] = Web3.to_hex(root) == result['root']
    result['valid'] = result['eligible'] = result['valid'] and result['root_matches_chain']
    return result


@router.post('/marketplace/create-order', status_code=201)
async def prepare(body: CreateOrder, request: Request):
    async with request.app.state.sessions() as session, session.begin():
        order = await create_order(session, request.app.state.chain, body)
        return order_view(order)


@router.get('/marketplace/order/{order_id}/status')
async def order_status(order_id: str, request: Request):
    async with request.app.state.sessions() as session:
        order = await session.get(Order, order_id)
        if not order:
            raise HTTPException(404, 'order not found')
        history = (await session.scalars(select(OrderTransition).where(OrderTransition.order_id == order_id)
            .order_by(OrderTransition.sequence.asc().nulls_first(), OrderTransition.timestamp, OrderTransition.id))).all()
        return {**order_view(order), 'history': [{'state': h.current, 'reason': h.reason, 'timestamp': h.timestamp, 'sequence': h.sequence} for h in history]}


@router.get('/marketplace/products')
async def products(request: Request, cursor: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=50)):
    chain = request.app.state.chain
    market = chain.contract('marketplace')
    block = await chain.block('latest')
    next_id = await market.functions.nextProductId().call(block_identifier=block['number'])
    result = []
    for id_ in range(cursor, min(next_id, cursor+limit)):
        p = await market.functions.products(id_).call(block_identifier=block['number'])
        try:
            quote = await market.functions.quoteProduct(id_).call(block_identifier=block['number'])
            required, error = str(quote[0]), None
        except Exception:
            required, error = None, 'not quotable: listing, merchant, inventory or oracle unavailable'
        result.append({'id': str(id_), 'merchant': p[0], 'usd_price6': str(p[1]), 'remaining': str(p[2]),
                       'per_buyer_limit': str(p[3]), 'listed': p[4], 'metadata_uri': p[5], 'mud_required': required, 'quote_error': error})
    return {'products': result, 'next_cursor': cursor+limit if cursor+limit < next_id else None, 'block_number': block['number']}


@router.get('/activity')
async def activity(request: Request, before_block: int | None = Query(default=None, ge=0),
                   address: str | None = None, limit: int = Query(default=50, ge=1, le=100)):
    query = select(Event).where(Event.chain_id == request.app.state.settings.chain_id)
    if before_block is not None:
        query = query.where(Event.block_number < before_block)
    if address:
        if not Web3.is_address(address):
            raise ValueError('invalid address')
        from sqlalchemy import func
        query = query.where(func.lower(Event.user_address) == address.lower())
    async with request.app.state.sessions() as session:
        rows = (await session.scalars(query.order_by(Event.block_number.desc(), Event.log_index.desc()).limit(limit))).all()
        return {'events': [{'tx_hash': e.tx_hash, 'log_index': e.log_index, 'chain_id': e.chain_id,
                            'block_number': e.block_number, 'block_hash': e.block_hash, 'user_address': e.user_address,
                            'mud_amount': e.mud_amount, 'collateral_amount': e.collateral_amount, 'event_type': e.event_type,
                            'timestamp': e.timestamp, 'finality_status': e.finality_status, 'canonical': e.canonical} for e in rows]}


@router.get('/transaction/{tx_hash}')
async def transaction_receipt(tx_hash: str, request: Request):
    import re
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', tx_hash):
        raise ValueError('transaction hash required')
    chain = request.app.state.chain
    from web3.exceptions import TransactionNotFound
    try:
        receipt = await chain.w3.eth.get_transaction_receipt(tx_hash)
    except TransactionNotFound:
        return {'status': 'NOT_MINED', 'transaction_hash': tx_hash}
    block = await chain.block(receipt['blockNumber'])
    canonical = block['hash'].lower() == Web3.to_hex(receipt['blockHash']).lower()
    if receipt['status'] == 0:
        FAILED_TRANSACTIONS.inc()
    return {'status': 'REORGED' if not canonical else ('REVERTED' if receipt['status'] == 0 else 'MINED'),
            'transaction_hash': tx_hash, 'block_number': receipt['blockNumber'], 'block_hash': Web3.to_hex(receipt['blockHash']),
            'confirmations': (await chain.head())-receipt['blockNumber']+1 if canonical else 0,
            'required_confirmations': request.app.state.settings.confirmations}
