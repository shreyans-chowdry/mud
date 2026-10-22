import asyncio
import logging
import time
from collections import defaultdict
from sqlalchemy import delete, select, text
from web3 import AsyncWeb3, WebSocketProvider
from ..models import Block, Checkpoint, Event, Order, Outbox
from ..metrics import INDEXER_HEARTBEAT, INDEXER_LAG, REORGS, RPC_FAILURES
from ..services.order_service import transition

log = logging.getLogger(__name__)


def extract_amounts(event):
    args, name = event['args'], event['event_type']
    user = args.get('buyer') or args.get('seller') or args.get('account')
    mud = args.get('mudOut', args.get('mudIn', args.get('mudPaid', 0)))
    collateral = args.get('collateralIn', args.get('collateralOut', 0))
    if name == 'Transfer':
        user = args['to'] if int(args['from'], 16) == 0 else args['from']
        mud = args['value']
    if name == 'Claimed':
        mud = args['amount']
    return user, str(mud), str(collateral)


class Indexer:
    def __init__(self, chain, factory, settings, redis=None):
        self.chain, self.factory, self.settings, self.redis = chain, factory, settings, redis
        self.lock = asyncio.Lock()

    async def _acquire(self, session):
        if session.bind.dialect.name == 'postgresql':
            # Transaction-scoped lock also protects multiple indexer processes for this chain.
            await session.execute(text('SELECT pg_advisory_xact_lock(:chain)'), {'chain': self.settings.chain_id})

    async def _reconcile(self, session, checkpoint):
        if checkpoint is None or checkpoint.block_number < self.settings.start_block:
            return
        head = await self.chain.head()
        if checkpoint.block_number <= head:
            actual = await self.chain.block(checkpoint.block_number)
            if actual['hash'] == checkpoint.block_hash:
                return
        original = checkpoint.block_number
        fork = min(original, head)
        floor = max(self.settings.start_block-1, original-self.settings.max_reorg_depth)
        found_hash = '0x'+'00'*32
        while fork > floor:
            stored = await session.get(Block, (self.settings.chain_id, fork))
            actual = await self.chain.block(fork)
            if stored and stored.hash == actual['hash']:
                found_hash = stored.hash
                break
            fork -= 1
        if fork == floor and floor >= self.settings.start_block:
            raise RuntimeError('reorg exceeds retained reconciliation bound; operator resync required')
        await self.rollback(session, fork)
        checkpoint.block_number, checkpoint.block_hash, checkpoint.updated_at = fork, found_hash, int(time.time())
        REORGS.inc()
        log.warning('canonical_reorganization', extra={'chain_id': self.settings.chain_id, 'old_tip': original, 'fork': fork})

    async def rollback(self, session, fork):
        chain = self.settings.chain_id
        removed = (await session.scalars(select(Event).where(Event.chain_id == chain, Event.block_number > fork,
                                                              Event.canonical.is_(True)))).all()
        keys = {(e.tx_hash, e.log_index): e for e in removed if e.event_type == 'OrderSettled'}
        for event in removed:
            event.canonical = False
            event.finality_status = 'ORPHANED'
        orders = (await session.scalars(select(Order).where(Order.chain_id == chain).with_for_update())).all()
        for order in orders:
            if (order.settlement_tx, order.settlement_log) not in keys:
                continue
            transition(session, order, 'REORGED', 'canonical settlement removed')
            order.fulfillment_status = 'REORG_REVIEW'
            rows = (await session.scalars(select(Outbox).where(Outbox.order_id == order.id).with_for_update())).all()
            # A leased delivery might already be in-flight. Compensate even when its ack was lost.
            if any(row.status in ('DELIVERED', 'SENDING') for row in rows):
                key = f'{order.id}:reorg:{order.settlement_tx}:{order.settlement_log}:' + keys[(order.settlement_tx, order.settlement_log)].block_hash
                if not await session.scalar(select(Outbox).where(Outbox.dedupe_key == key)):
                    session.add(Outbox(dedupe_key=key, order_id=order.id, event_type='payment.reorged',
                                      payload={'type': 'payment.reorged', 'order_id': order.id, 'tx_hash': order.settlement_tx,
                                               'block_hash': keys[(order.settlement_tx, order.settlement_log)].block_hash}))
            for row in rows:
                if row.status != 'DELIVERED':
                    row.status = 'CANCELLED'
        await session.execute(delete(Block).where(Block.chain_id == chain, Block.number > fork))

    async def _insert(self, session, block, decoded):
        chain = self.settings.chain_id
        stored = await session.get(Block, (chain, block['number']))
        if stored and stored.hash != block['hash']:
            raise RuntimeError('canonical block conflict')
        if not stored:
            session.add(Block(chain_id=chain, number=block['number'], hash=block['hash'],
                              parent_hash=block['parent_hash'], timestamp=block['timestamp']))
        for data in decoded:
            if data['block_hash'] != block['hash']:
                raise RuntimeError('RPC log/block hash mismatch')
            event = await session.scalar(select(Event).where(Event.chain_id == chain, Event.tx_hash == data['tx_hash'],
                                                             Event.log_index == data['log_index']))
            user, mud, collateral = extract_amounts(data)
            values = dict(chain_id=chain, tx_hash=data['tx_hash'], log_index=data['log_index'], block_number=block['number'],
                          block_hash=block['hash'], transaction_index=data['transaction_index'], user_address=user,
                          mud_amount=mud, collateral_amount=collateral, event_type=data['event_type'], timestamp=block['timestamp'],
                          finality_status='OBSERVED', canonical=True, raw=data)
            if event:
                if event.canonical and event.block_hash == block['hash']:
                    continue
                for key, value in values.items():
                    setattr(event, key, value)
            else:
                event = Event(**values)
                session.add(event)
            if data['event_type'] == 'OrderSettled' and data['args']['orderId'] != '0x'+'00'*32:
                args = data['args']
                order = await session.scalar(select(Order).where(Order.order_hash == args['orderId'],
                                                                  Order.chain_id == chain).with_for_update())
                if order and order.verifying_contract.lower() == data['contract'].lower() and order.buyer.lower() == args['buyer'].lower() \
                        and order.product_id == str(args['productId']) and int(args['mudPaid']) <= int(order.max_mud_amount):
                    order.settlement_tx, order.settlement_log = event.tx_hash, event.log_index
                    order.paid_amount = str(args['mudPaid'])
                    transition(session, order, 'PAYMENT_OBSERVED', 'canonical marketplace event')
                    order.fulfillment_status = 'WAITING_FINALITY'
        await session.flush()

    async def _finality(self, session, head, timestamp):
        events = (await session.scalars(select(Event).where(Event.chain_id == self.settings.chain_id,
            Event.canonical.is_(True), Event.finality_status != 'FINALIZED'))).all()
        for event in events:
            depth = head-event.block_number+1
            event.finality_status = 'FINALIZED' if depth >= self.settings.finality_depth else (
                'CONFIRMED' if depth >= self.settings.confirmations else 'OBSERVED')
            if event.event_type != 'OrderSettled':
                continue
            order = await session.scalar(select(Order).where(Order.chain_id == self.settings.chain_id,
                Order.settlement_tx == event.tx_hash, Order.settlement_log == event.log_index).with_for_update())
            if not order:
                continue
            if event.finality_status in ('CONFIRMED', 'FINALIZED') and order.status == 'PAYMENT_OBSERVED':
                transition(session, order, 'CONFIRMED', 'configured confirmation depth met')
            if event.finality_status == 'FINALIZED' and order.status == 'CONFIRMED':
                # Block-depth finality is a policy, not an L1-finality guarantee.
                key = f'{order.id}:confirmed:{event.tx_hash}:{event.log_index}:{event.block_hash}'
                if not await session.scalar(select(Outbox).where(Outbox.dedupe_key == key)):
                    session.add(Outbox(dedupe_key=key, order_id=order.id, event_type='order.confirmed', payload={
                        'type': 'order.confirmed', 'order_id': order.id, 'chain_id': order.chain_id, 'product_id': order.product_id,
                        'buyer': order.buyer, 'mud_paid': order.paid_amount, 'tx_hash': event.tx_hash,
                        'block_hash': event.block_hash, 'log_index': event.log_index}))
                order.fulfillment_status = 'QUEUED'
        expired = (await session.scalars(select(Order).where(Order.chain_id == self.settings.chain_id,
            Order.deadline < timestamp, Order.status.in_(['CREATED', 'AWAITING_PAYMENT'])))).all()
        for order in expired:
            transition(session, order, 'EXPIRED', 'deadline elapsed without indexed settlement')

    async def sync_once(self):
        async with self.lock:
            async with self.factory() as session, session.begin():
                await self._acquire(session)
                checkpoint = await session.get(Checkpoint, self.settings.chain_id)
                await self._reconcile(session, checkpoint)
                head = await self.chain.head()
                start = (checkpoint.block_number+1 if checkpoint else max(self.settings.start_block, self.chain.manifest['startBlock']))
                end = min(head, start+self.settings.batch_size-1)
                if start <= end:
                    logs = await self.chain.events(start, end)
                    grouped = defaultdict(list)
                    for event in logs:
                        grouped[event['block_number']].append(event)
                    previous = checkpoint.block_hash if checkpoint and checkpoint.block_number >= self.settings.start_block else None
                    for number in range(start, end+1):
                        block = await self.chain.block(number)
                        if previous and block['parent_hash'] != previous:
                            raise RuntimeError('parent hash mismatch; batch rollback and retry')
                        await self._insert(session, block, grouped[number])
                        previous = block['hash']
                        if checkpoint is None:
                            checkpoint = Checkpoint(chain_id=self.settings.chain_id, block_number=number,
                                                    block_hash=block['hash'], updated_at=int(time.time()))
                            session.add(checkpoint)
                        else:
                            checkpoint.block_number, checkpoint.block_hash, checkpoint.updated_at = number, block['hash'], int(time.time())
                    # Refuse to commit a batch if canonical head changed during RPC reads.
                    if (await self.chain.block(end))['hash'] != previous:
                        raise RuntimeError('chain changed during batch')
                tip = await self.chain.block(head)
                await self._finality(session, head, tip['timestamp'])
                INDEXER_LAG.set(head-(checkpoint.block_number if checkpoint else self.settings.start_block-1))
                more = end < head
            if self.redis:
                await self.redis.delete(f'mud:{self.settings.chain_id}:spot:v1')
            INDEXER_HEARTBEAT.set(time.time())
            return more

    async def catch_up(self):
        while await self.sync_once():
            await asyncio.sleep(0)

    async def run(self):
        delay = 1
        while True:
            try:
                await self.chain.validate()
                await self.catch_up()
                async with AsyncWeb3(WebSocketProvider(self.settings.rpc_ws, request_timeout=15)) as ws:
                    if await ws.eth.chain_id != self.settings.chain_id:
                        raise RuntimeError('WebSocket chain mismatch')
                    await ws.eth.subscribe('newHeads')
                    stream = ws.socket.process_subscriptions()
                    delay = 1
                    pending = asyncio.create_task(anext(stream))
                    try:
                        while True:
                            done, _ = await asyncio.wait({pending}, timeout=10)
                            if done:
                                pending.result()
                                pending = asyncio.create_task(anext(stream))
                            await self.catch_up()
                    finally:
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                RPC_FAILURES.inc()
                log.warning('indexer_retry', extra={'error_type': type(exc).__name__, 'backoff': delay})
                # HTTP backfill works even when subscriptions are unavailable.
                try:
                    await self.catch_up()
                except Exception:
                    log.warning('http_backfill_unavailable')
                await asyncio.sleep(delay)
                delay = min(delay*2, 30)


async def main():
    from ..blockchain import Chain
    from ..config import get_settings
    from ..database import Session, engine
    from prometheus_client import start_http_server
    start_http_server(9101, addr='0.0.0.0')
    settings = get_settings()
    chain = Chain(settings)
    try:
        await Indexer(chain, Session, settings).run()
    finally:
        await chain.close()
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
