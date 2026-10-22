import asyncio
import importlib.util
import json
import time
from types import SimpleNamespace
import httpx
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from sqlalchemy import func, select
from app.config import ROOT, Settings
from app.main import create_app
from app.models import Checkpoint, Delivery, Event, Order, Outbox
from app.schemas import CreateOrder, VerifyProof, parse_amount
from app.services.airdrop_service import AirdropService
from app.services.curve_service import CurveService
from app.services.order_service import create_order, typed_data
from app.services.webhook_service import encode_payload, signature, verify_signature
from app.workers.indexer import Indexer
from app.workers.outbox_worker import OutboxWorker

BUYER = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'
MARKET = '0x'+'11'*20
TX = '0x'+'ab'*32
ZERO = '0x'+'00'*32


def settings(**kwargs):
    return Settings(_env_file=None, **{'redis_url': None, 'run_workers': False, **kwargs})


class FakeChain:
    def __init__(self, n=5):
        self.settings = settings()
        self.manifest = {'startBlock': 0}
        self.blocks = {i: {'number': i, 'hash': '0x'+f'{i+1:064x}',
            'parent_hash': ZERO if i == 0 else '0x'+f'{i:064x}', 'timestamp': 100+i} for i in range(n)}
        self.logs = []
        self.offline = False

    async def head(self):
        if self.offline:
            raise OSError('RPC offline')
        return max(self.blocks)

    async def block(self, n):
        return self.blocks[max(self.blocks) if n == 'latest' else n]

    async def events(self, start, end):
        return [e for e in self.logs if start <= e['block_number'] <= end]

    async def validate(self):
        await self.head()


def log(block, index=1, order_hash=ZERO, kind='OrderSettled'):
    return {'tx_hash': TX, 'log_index': index, 'block_number': block['number'], 'block_hash': block['hash'],
            'transaction_index': 0, 'event_type': kind, 'contract': MARKET,
            'args': {'orderId': order_hash, 'productId': 1, 'buyer': BUYER, 'mudPaid': 10}}


async def seed_order(db, hash_='0x'+'77'*32):
    async with db() as s, s.begin():
        o = Order(id='order-1', order_hash=hash_, chain_id=31337, verifying_contract=MARKET, product_id='1',
            buyer=BUYER, max_mud_amount='20', nonce='0', deadline=1000, status='AWAITING_PAYMENT', typed_data={})
        s.add(o)
    return hash_


@pytest.mark.asyncio
async def test_checkpoint_duplicate_delivery_and_restart(db):
    chain = FakeChain()
    chain.logs = [log(chain.blocks[1], 1), log(chain.blocks[1], 2)]
    worker = Indexer(chain, db, settings(batch_size=2))
    await worker.catch_up()
    await Indexer(chain, db, settings()).catch_up()
    # Explicit duplicate block replay still preserves both logs from the same transaction.
    async with db() as s, s.begin():
        await worker._insert(s, chain.blocks[1], chain.logs)
    async with db() as s:
        assert await s.scalar(select(func.count()).select_from(Event)) == 2
        checkpoint = await s.get(Checkpoint, 31337)
        assert checkpoint.block_number == 4
        rows = (await s.scalars(select(Event))).all()
        assert all(e.finality_status == 'FINALIZED' for e in rows)


@pytest.mark.asyncio
async def test_reorg_rolls_back_order_and_reconciles_orphans(db):
    h = await seed_order(db)
    chain = FakeChain(3)
    chain.logs = [log(chain.blocks[2], order_hash=h)]
    worker = Indexer(chain, db, settings(confirmations=2, finality_depth=3))
    await worker.catch_up()
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'PAYMENT_OBSERVED'
    chain.blocks[2] = {**chain.blocks[2], 'hash': '0x'+'ff'*32}
    chain.logs = []
    await worker.catch_up()
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'REORGED'
        event = await s.scalar(select(Event))
        assert not event.canonical and event.finality_status == 'ORPHANED'
    # Same tx re-mined at the same log index updates, rather than duplicates, its canonical identity.
    chain.logs = [log(chain.blocks[2], order_hash=h)]
    async with db() as s, s.begin():
        await worker._insert(s, chain.blocks[2], chain.logs)
    async with db() as s:
        assert await s.scalar(select(func.count()).select_from(Event)) == 1
        assert (await s.get(Order, 'order-1')).status == 'PAYMENT_OBSERVED'


@pytest.mark.asyncio
async def test_confirmation_depth_outbox_and_fulfillment_retry(db):
    h = await seed_order(db)
    chain = FakeChain(2)
    chain.logs = [log(chain.blocks[1], order_hash=h)]
    worker = Indexer(chain, db, settings(confirmations=2, finality_depth=3))
    await worker.catch_up()
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'PAYMENT_OBSERVED'
        assert await s.scalar(select(func.count()).select_from(Outbox)) == 0
    for i in (2, 3):
        chain.blocks[i] = {'number': i, 'hash': '0x'+f'{i+1:064x}', 'parent_hash': chain.blocks[i-1]['hash'], 'timestamp': 100+i}
        await worker.catch_up()
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'CONFIRMED'
        assert await s.scalar(select(func.count()).select_from(Outbox)) == 1
    calls = []
    def handler(request):
        calls.append(request)
        assert verify_signature('x'*32, request.headers['X-Mud-Timestamp'], request.headers['X-Request-Id'],
            request.headers['Idempotency-Key'], request.content, request.headers['X-Mud-Signature'])
        return httpx.Response(503 if len(calls) == 1 else 200)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        outbox = OutboxWorker(db, settings(webhook_url='http://localhost/fulfill', webhook_secret='x'*32), client)
        assert await outbox.once()
        async with db() as s, s.begin():
            row = await s.scalar(select(Outbox))
            assert row.status == 'RETRY'
            row.next_attempt = 0
        assert await outbox.once()
        assert not await outbox.once()
    assert calls[0].headers['Idempotency-Key'] == calls[1].headers['Idempotency-Key']
    assert calls[0].headers['X-Request-Id'] != calls[1].headers['X-Request-Id']
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'FULFILLED'
        assert await s.scalar(select(func.count()).select_from(Delivery)) == 2
    # Deep reorg of an acknowledged delivery creates a compensating notification.
    chain.blocks[1] = {**chain.blocks[1], 'hash': '0x'+'ee'*32}
    for i in (2, 3):
        chain.blocks[i] = {**chain.blocks[i], 'hash': '0x'+f'{i+100:064x}', 'parent_hash': chain.blocks[i-1]['hash']}
    chain.logs = []
    await worker.catch_up()
    async with db() as s:
        assert (await s.get(Order, 'order-1')).status == 'REORGED'
        assert await s.scalar(select(func.count()).select_from(Outbox).where(Outbox.event_type == 'payment.reorged')) == 1


@pytest.mark.asyncio
async def test_rpc_outage_and_bad_parent_do_not_commit_checkpoint(db):
    chain = FakeChain(3)
    chain.blocks[2]['parent_hash'] = ZERO
    worker = Indexer(chain, db, settings())
    with pytest.raises(RuntimeError):
        await worker.catch_up()
    async with db() as s:
        assert await s.get(Checkpoint, 31337) is None
    chain.offline = True
    with pytest.raises(OSError):
        await worker.catch_up()
    chain.offline = False
    chain.blocks[2]['parent_hash'] = chain.blocks[1]['hash']
    await worker.catch_up()
    async with db() as s:
        assert (await s.get(Checkpoint, 31337)).block_number == 2


class Call:
    def __init__(self, value):
        self.value = value

    async def call(self, **kwargs):
        return self.value


class OrderChain(FakeChain):
    def contract(self, name):
        functions = SimpleNamespace(quoteProduct=lambda _: Call([10, 100000000, 100]),
            products=lambda _: Call([BUYER, 1000000, 10, 5, True, 'mud://test']),
            purchased=lambda *_: Call(0), nonces=lambda _: Call(0))
        return SimpleNamespace(address=MARKET, functions=functions)


@pytest.mark.asyncio
async def test_concurrent_order_creation_unique_ids_and_eip712(db):
    chain = OrderChain()
    request = CreateOrder(product_id='1', buyer=BUYER, max_mud_amount='20')
    async def create():
        async with db() as s, s.begin():
            return await create_order(s, chain, request)
    first, second = await asyncio.gather(create(), create())
    assert first.order_hash != second.order_hash
    assert first.typed_data['domain']['chainId'] == 31337
    assert first.typed_data['domain']['verifyingContract'] == MARKET
    # Parallel intents intentionally share a chain nonce; only one can settle. Never reserve nonces off-chain.
    assert first.nonce == second.nonce == '0'
    account = Account.create()
    data = typed_data(31337, MARKET, first.order_hash, '1', account.address, '20', 500, 0)
    encoded = encode_typed_data(full_message=data)
    signed = account.sign_message(encoded)
    assert Account.recover_message(encoded, signature=signed.signature) == account.address
    data['domain']['chainId'] = 8453
    assert Account.recover_message(encode_typed_data(full_message=data), signature=signed.signature) != account.address


def test_merkle_vectors_and_invalid_dataset():
    service = AirdropService(ROOT / 'tests/fixtures/eligibility.local.json')
    data = service.dataset()
    valid = data['claims'][0]
    args = {k: valid[k] for k in ('address', 'index', 'allocation', 'proof')}
    assert service.verify(VerifyProof(**args))['valid']
    assert not service.verify(VerifyProof(**{**args, 'allocation': str(int(args['allocation'])+1)}))['valid']
    assert not service.eligibility('0x'+'33'*20)['eligible']
    spec = importlib.util.spec_from_file_location('generator', ROOT / 'scripts/generate_merkle_tree.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dataset = json.loads((ROOT / 'tests/fixtures/eligibility.dataset.json').read_text())
    dataset['entries'].append(dataset['entries'][0])
    with pytest.raises(ValueError):
        module.generate(dataset)


def test_webhook_tampering_expiry_and_amount_validation():
    body = encode_payload({'order_id': 'one'})
    sig = signature('s'*32, 1000, 'request', 'key', body)
    assert verify_signature('s'*32, '1000', 'request', 'key', body, sig, now=1001)
    assert not verify_signature('s'*32, '1000', 'request', 'key', body+b' ', sig, now=1001)
    assert not verify_signature('s'*32, '1000', 'request', 'key', body, sig, now=1301)
    for bad in ('0', '-1', '1.0', str(2**256)):
        with pytest.raises(ValueError):
            parse_amount(bad)


@pytest.mark.asyncio
async def test_api_schema_boundaries_rate_limit_and_health(db):
    app = create_app(settings(requests_per_minute=3), db, OrderChain())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
            assert (await c.get('/health')).status_code == 200
            response = await c.post('/api/v1/marketplace/create-order', json={'buyer': 'invalid'})
            assert response.status_code == 422 and 'error' in response.json()
            response = await c.post('/api/v1/marketplace/create-order', json={
                'buyer': BUYER, 'product_id': '1', 'max_mud_amount': '20'})
            assert response.status_code == 201
            id_ = response.json()['id']
            assert (await c.get(f'/api/v1/marketplace/order/{id_}/status')).json()['status'] == 'AWAITING_PAYMENT'
            assert (await c.get('/api/v1/activity')).status_code == 429


@pytest.mark.asyncio
async def test_expired_cache_not_returned():
    class Cache:
        async def get(self, key):
            return json.dumps({'quote_timestamp': int(time.time())-1000})
    service = CurveService(FakeChain(), Cache())
    # The stale entry must not be returned as a fresh quote. Missing RPC contract adapter raises.
    with pytest.raises(AttributeError):
        await service.spot()


@pytest.mark.asyncio
async def test_websocket_reconnect_backfills_after_subscription_failure(db, monkeypatch):
    from app.workers import indexer as module
    chain = FakeChain()
    attempts, sleeps = [], []

    class Socket:
        @property
        def chain_id(self):
            async def value():
                return 31337
            return value()

        async def subscribe(self, kind):
            attempts.append(kind)
            if len(attempts) == 1:
                raise ConnectionError('subscription transport lost')
            raise asyncio.CancelledError()

    class WebSocket:
        def __init__(self, provider):
            self.eth = Socket()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    async def backoff(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(module, 'AsyncWeb3', WebSocket)
    monkeypatch.setattr(module.asyncio, 'sleep', backoff)
    with pytest.raises(asyncio.CancelledError):
        await Indexer(chain, db, settings()).run()
    assert attempts == ['newHeads', 'newHeads'] and 1 in sleeps
    async with db() as session:
        assert (await session.get(Checkpoint, 31337)).block_number == 4


@pytest.mark.asyncio
async def test_webhook_receiver_atomically_deduplicates_and_rejects_replay(db, monkeypatch):
    from app import fulfillment as receiver
    from app.models import FulfillmentReceipt
    monkeypatch.setattr(receiver, 'Session', db)
    monkeypatch.setattr(receiver, 'get_settings', lambda: settings(webhook_secret='z'*32))
    body = encode_payload({'type': 'order.confirmed', 'order_id': 'durable'})
    stamp = int(time.time())
    headers = {'X-Mud-Timestamp': str(stamp), 'X-Request-Id': 'r1', 'Idempotency-Key': 'durable-key',
               'X-Mud-Signature': signature('z'*32, stamp, 'r1', 'durable-key', body)}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=receiver.app), base_url='http://test') as client:
        assert (await client.post('/fulfill', content=body, headers=headers)).status_code == 200
        duplicate = await client.post('/fulfill', content=body, headers=headers)
        assert duplicate.json()['status'] == 'already_recorded'
        headers['X-Mud-Timestamp'] = str(stamp-301)
        assert (await client.post('/fulfill', content=body, headers=headers)).status_code == 401
    async with db() as session:
        assert await session.scalar(select(func.count()).select_from(FulfillmentReceipt)) == 1


@pytest.mark.asyncio
async def test_stale_webhook_attempt_cannot_regress_a_newer_delivery(db):
    await seed_order(db)
    async with db() as session, session.begin():
        session.add(Outbox(id='fenced', dedupe_key='fenced-key', order_id='order-1', event_type='order.confirmed',
                           payload={'type': 'order.confirmed', 'order_id': 'order-1'}))

    async def response_after_reclaim(request):
        # Another lease generation completes while the old worker is suspended in HTTP.
        async with db() as session, session.begin():
            row = await session.get(Outbox, 'fenced')
            row.attempts += 1
            row.status = 'DELIVERED'
            order = await session.get(Order, 'order-1')
            order.status, order.fulfillment_status = 'FULFILLED', 'DELIVERED'
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(response_after_reclaim)) as client:
        worker = OutboxWorker(db, settings(webhook_url='http://localhost/fulfill', webhook_secret='x'*32), client)
        assert await worker.once()
    async with db() as session:
        assert (await session.get(Outbox, 'fenced')).status == 'DELIVERED'
        assert (await session.get(Order, 'order-1')).status == 'FULFILLED'
        assert (await session.scalar(select(Delivery))).error == 'HTTP 503'


@pytest.mark.asyncio
async def test_reincluded_payment_updates_one_entitlement_and_ignores_old_reorg(db, monkeypatch):
    from app import fulfillment as receiver
    from app.models import Entitlement, FulfillmentReceipt
    monkeypatch.setattr(receiver, 'Session', db)
    monkeypatch.setattr(receiver, 'get_settings', lambda: settings(webhook_secret='z'*32))
    tx, old_block, new_block = '0x'+'aa'*32, '0x'+'11'*32, '0x'+'22'*32
    stamp = int(time.time())

    async def send(client, key, payload):
        body = encode_payload(payload)
        headers = {'X-Mud-Timestamp': str(stamp), 'X-Request-Id': key, 'Idempotency-Key': key,
                   'X-Mud-Signature': signature('z'*32, stamp, key, key, body)}
        assert (await client.post('/fulfill', content=body, headers=headers)).status_code == 200

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=receiver.app), base_url='http://test') as client:
        first = {'type': 'order.confirmed', 'order_id': 'one-order', 'tx_hash': tx, 'block_hash': old_block}
        await send(client, 'original-confirmation', first)
        reorg = {**first, 'type': 'payment.reorged'}
        await send(client, 'old-block-reorg', reorg)
        async with db() as session:
            assert (await session.get(Entitlement, 'one-order')).status == 'REORG_REVIEW'
        await send(client, 'new-canonical-confirmation', {**first, 'block_hash': new_block})
        await send(client, 'late-old-block-reorg', reorg)
        await send(client, 'late-old-confirmation', first)
        # Compensation delivered first must also prevent a delayed orphan activation.
        orphan = {**first, 'order_id': 'reordered-order'}
        await send(client, 'compensation-before-confirmation', {**orphan, 'type': 'payment.reorged'})
        await send(client, 'delayed-orphan-confirmation', orphan)
    async with db() as session:
        assert await session.scalar(select(func.count()).select_from(Entitlement)) == 1
        assert await session.scalar(select(func.count()).select_from(FulfillmentReceipt)) == 7
        entitlement = await session.get(Entitlement, 'one-order')
        assert entitlement.status == 'ACTIVE' and entitlement.block_hash == new_block


@pytest.mark.asyncio
async def test_transition_history_preserves_same_second_order_across_sessions(db, monkeypatch):
    from app.services import order_service
    from app.models import OrderTransition
    await seed_order(db)
    monkeypatch.setattr(order_service.time, 'time', lambda: 1000)
    async with db() as session, session.begin():
        order = await session.get(Order, 'order-1', with_for_update=True)
        order_service.transition(session, order, 'PAYMENT_OBSERVED', 'canonical event')
        order_service.transition(session, order, 'CONFIRMED', 'depth reached')
    async with db() as session, session.begin():
        order = await session.get(Order, 'order-1', with_for_update=True)
        order_service.transition(session, order, 'FULFILLED', 'receiver acknowledged')
    async with db() as session:
        rows = (await session.scalars(select(OrderTransition).order_by(OrderTransition.sequence))).all()
        assert [r.current for r in rows] == ['PAYMENT_OBSERVED', 'CONFIRMED', 'FULFILLED']
        assert [r.sequence for r in rows] == [1, 2, 3]
        assert len({r.timestamp for r in rows}) == 1
    app = create_app(settings(), db, OrderChain())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            history = (await client.get('/api/v1/marketplace/order/order-1/status')).json()['history']
            assert [h['state'] for h in history] == ['PAYMENT_OBSERVED', 'CONFIRMED', 'FULFILLED']
