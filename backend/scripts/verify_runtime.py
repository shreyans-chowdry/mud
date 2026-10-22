#!/usr/bin/env python3
"""Verify actual PostgreSQL settlement, log replay and signed receiver idempotency locally."""
import asyncio
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
import httpx
from sqlalchemy import func, select, text
from app.blockchain import Chain
from app.config import ROOT, get_settings
from app.database import Session, engine
from app.models import Delivery, Entitlement, Event, FulfillmentReceipt, Order, OrderTransition, Outbox
from app.services.webhook_service import encode_payload, signature
from app.workers.indexer import Indexer


async def verify(lifecycle_file: Path):
    settings = get_settings()
    if settings.environment != 'local' or settings.chain_id != 31337 or engine.dialect.name != 'postgresql':
        raise ValueError('requires explicit LOCAL chain 31337 and PostgreSQL runtime database')
    destination = urlparse(settings.webhook_url or '')
    if destination.hostname not in ('127.0.0.1', 'localhost') or destination.port != 8001 or not settings.webhook_secret:
        raise ValueError('only the configured local fulfillment receiver on port 8001 is supported')
    lifecycle = json.loads(lifecycle_file.read_text())
    chain = Chain(settings)
    try:
        await chain.validate()
        async with Session() as session:
            order = await session.get(Order, lifecycle['orderId'])
            assert order and order.status == 'FULFILLED' and order.fulfillment_status == 'DELIVERED'
            assert order.settlement_tx.lower() == lifecycle['purchaseTx'].lower()
            event = await session.scalar(select(Event).where(Event.chain_id == 31337,
                Event.tx_hash == order.settlement_tx, Event.log_index == order.settlement_log))
            assert event and event.canonical and event.finality_status == 'FINALIZED'
            block_number = event.block_number
            before = await session.scalar(select(func.count()).select_from(Event))
            outbox = await session.scalar(select(Outbox).where(Outbox.order_id == order.id,
                                                              Outbox.event_type == 'order.confirmed'))
            assert outbox and outbox.status == 'DELIVERED'
            key, payload = outbox.dedupe_key, outbox.payload
            delivery_count = await session.scalar(select(func.count()).select_from(Delivery).where(Delivery.outbox_id == outbox.id))
            history = (await session.scalars(select(OrderTransition).where(OrderTransition.order_id == order.id)
                .order_by(OrderTransition.sequence.asc().nulls_first(), OrderTransition.timestamp, OrderTransition.id))).all()
            states = {h.current for h in history}
            assert {'AWAITING_PAYMENT', 'PAYMENT_OBSERVED', 'CONFIRMED', 'FULFILLED'} <= states
            sequences = [h.sequence for h in history]
            ordered_history = all(n is not None for n in sequences)
            if ordered_history:
                assert sequences == sorted(set(sequences))
                observed = [h.current for h in history]
                assert observed.index('AWAITING_PAYMENT') < observed.index('PAYMENT_OBSERVED') < observed.index('CONFIRMED') < observed.index('FULFILLED')
            schema_head = await session.scalar(text('SELECT version_num FROM alembic_version'))
        block = await chain.block(block_number)
        logs = await chain.events(block_number, block_number)
        worker = Indexer(chain, Session, settings)
        async with Session() as session, session.begin():
            await worker._acquire(session)
            await worker._insert(session, block, logs)
        async with Session() as session:
            after = await session.scalar(select(func.count()).select_from(Event))
            assert after == before, 'replayed actual block duplicated event rows'
        body = encode_payload(payload)
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            for _ in range(2):
                stamp, request_id = int(time.time()), str(uuid.uuid4())
                headers = {'Content-Type': 'application/json', 'X-Mud-Timestamp': str(stamp), 'X-Request-Id': request_id,
                           'Idempotency-Key': key, 'X-Mud-Signature': signature(settings.webhook_secret, stamp, request_id, key, body)}
                response = await client.post(settings.webhook_url, content=body, headers=headers)
                assert response.status_code == 200 and response.json()['status'] == 'already_recorded'
        async with Session() as session:
            receipt_count = await session.scalar(select(func.count()).select_from(FulfillmentReceipt).where(
                FulfillmentReceipt.idempotency_key == key))
            entitlement_count = await session.scalar(select(func.count()).select_from(Entitlement).where(
                Entitlement.order_id == lifecycle['orderId']))
            entitlement = await session.get(Entitlement, lifecycle['orderId'])
            assert receipt_count == 1 and entitlement_count == 1 and entitlement.status == 'ACTIVE'
            assert (await session.get(Order, lifecycle['orderId'])).status == 'FULFILLED'
        return {'chain_id': 31337, 'database_backend': 'postgresql', 'order_id': lifecycle['orderId'],
                'transaction_hash': lifecycle['purchaseTx'], 'status': 'FULFILLED', 'canonical_finality': 'FINALIZED',
                'events_before_replay': before, 'events_after_replay': after, 'replayed_log_count': len(logs),
                'outbox_delivery_records': delivery_count, 'receiver_receipts_for_key': receipt_count,
                'entitlements_for_order': entitlement_count, 'signed_duplicate_requests': 2,
                'verified_at_unix': int(time.time()), 'schema_head': schema_head,
                'ordered_transition_history_verified': ordered_history, 'transition_sequences': sequences}
    finally:
        await chain.close()
        await engine.dispose()


if __name__ == '__main__':
    result = asyncio.run(verify(ROOT / 'runtime/lifecycle.json'))
    (ROOT / 'runtime/postgres-integration.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
