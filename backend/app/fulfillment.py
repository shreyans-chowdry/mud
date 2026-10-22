"""Local durable entitlement receiver. A production merchant implements its own delivery."""
import json
import re
import time
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from .config import get_settings
from .database import Session
from .models import Entitlement, FulfillmentReceipt
from .services.webhook_service import verify_signature

app = FastAPI(title='Local MUD fulfillment receiver')


@app.post('/fulfill')
async def fulfill(request: Request):
    settings = get_settings()
    if settings.environment != 'local' or not settings.webhook_secret:
        raise HTTPException(503, 'local receiver disabled')
    body = await request.body()
    if len(body) > 65536:
        raise HTTPException(413, 'payload too large')
    key = request.headers.get('Idempotency-Key', '')
    if not key or len(key) > 200 or not verify_signature(settings.webhook_secret,
        request.headers.get('X-Mud-Timestamp'), request.headers.get('X-Request-Id', ''), key, body,
        request.headers.get('X-Mud-Signature', '')):
        raise HTTPException(401, 'invalid webhook signature or replay window')
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(422, 'invalid JSON')
    if not isinstance(payload, dict) or payload.get('type') not in ('order.confirmed', 'payment.reorged') \
            or not isinstance(payload.get('order_id'), str) or not 1 <= len(payload['order_id']) <= 36:
        raise HTTPException(422, 'invalid fulfillment event')
    for field in ('tx_hash', 'block_hash'):
        if field in payload and not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(payload[field])):
            raise HTTPException(422, 'invalid settlement hash')
    async with Session() as session:
        try:
            async with session.begin():
                if session.bind.dialect.name == 'postgresql':
                    await session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                                          {'key': 'mud-entitlement:'+payload['order_id']})
                existing = await session.get(FulfillmentReceipt, key)
                if existing:
                    if existing.payload != payload:
                        raise HTTPException(409, 'idempotency key payload conflict')
                    return {'status': 'already_recorded', 'idempotency_key': key}
                entitlement = await session.get(Entitlement, payload['order_id'], with_for_update=True)
                revoked = False
                if payload['type'] == 'order.confirmed':
                    # Compensation can arrive before a timed-out confirmation request.
                    # Preserve all revocations, even after a newer inclusion becomes active.
                    revocations = await session.scalars(select(FulfillmentReceipt.payload).where(
                        FulfillmentReceipt.payload['type'].as_string() == 'payment.reorged',
                        FulfillmentReceipt.payload['order_id'].as_string() == payload['order_id']))
                    revoked = any(r.get('tx_hash') == payload.get('tx_hash') and (
                        not r.get('block_hash') or r['block_hash'] == payload.get('block_hash')) for r in revocations)
                if payload['type'] == 'order.confirmed' and not revoked:
                    if entitlement is None:
                        entitlement = Entitlement(order_id=payload['order_id'], status='ACTIVE', source_key=key)
                        session.add(entitlement)
                    entitlement.status = 'ACTIVE'
                    entitlement.source_key = key
                    entitlement.tx_hash = payload.get('tx_hash')
                    entitlement.block_hash = payload.get('block_hash')
                    entitlement.updated_at = int(time.time())
                elif entitlement and entitlement.tx_hash == payload.get('tx_hash') and (
                        not payload.get('block_hash') or entitlement.block_hash == payload['block_hash']):
                    entitlement.status = 'REORG_REVIEW'
                    entitlement.updated_at = int(time.time())
                session.add(FulfillmentReceipt(idempotency_key=key, payload=payload))
        except IntegrityError:
            await session.rollback()
            existing = await session.get(FulfillmentReceipt, key)
            if not existing or existing.payload != payload:
                raise HTTPException(409, 'idempotency conflict')
    return {'status': 'local_entitlement_recorded', 'idempotency_key': key}
