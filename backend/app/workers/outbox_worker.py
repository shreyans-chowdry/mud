import asyncio
import logging
import time
import uuid
import httpx
from sqlalchemy import or_, select
from ..models import Delivery, Order, Outbox
from ..metrics import OUTBOX_HEARTBEAT, WEBHOOK_RETRIES
from ..services.order_service import transition
from ..services.webhook_service import encode_payload, signature, validate_destination

log = logging.getLogger(__name__)


class OutboxWorker:
    def __init__(self, factory, settings, client=None):
        self.factory, self.settings = factory, settings
        self.client = client
        self.lock = asyncio.Lock()

    async def once(self):
        destination = validate_destination(self.settings)
        now = int(time.time())
        async with self.lock:
            async with self.factory() as session, session.begin():
                row = await session.scalar(select(Outbox).where(Outbox.next_attempt <= now,
                    or_(Outbox.status.in_(['PENDING', 'RETRY']), (Outbox.status == 'SENDING') & (Outbox.lease_until < now)))
                    .order_by(Outbox.next_attempt).with_for_update(skip_locked=True).limit(1))
                if not row:
                    return False
                row.status, row.lease_until, row.attempts = 'SENDING', now+60, row.attempts+1
                id_, key, payload, attempt = row.id, row.dedupe_key, row.payload, row.attempts
                request_id = str(uuid.uuid4())
                session.add(Delivery(outbox_id=id_, request_id=request_id))
            body = encode_payload(payload)
            headers = {'Content-Type': 'application/json', 'X-Mud-Timestamp': str(now), 'X-Request-Id': request_id,
                       'Idempotency-Key': key, 'X-Mud-Signature': signature(self.settings.webhook_secret, now, request_id, key, body)}
            status_code, error = None, None
            try:
                if self.client:
                    response = await self.client.post(destination, content=body, headers=headers)
                else:
                    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                        response = await client.post(destination, content=body, headers=headers)
                status_code = response.status_code
                if not 200 <= status_code < 300:
                    error = f'HTTP {status_code}'
            except (httpx.HTTPError, OSError) as exc:
                error = type(exc).__name__
            async with self.factory() as session, session.begin():
                row = await session.get(Outbox, id_, with_for_update=True)
                delivery = await session.scalar(select(Delivery).where(Delivery.request_id == request_id))
                delivery.status_code, delivery.error = status_code, error
                if row.status != 'SENDING' or row.attempts != attempt:
                    return True
                order = await session.get(Order, row.order_id, with_for_update=True)
                if error:
                    WEBHOOK_RETRIES.inc()
                    row.last_error = error
                    row.status = 'FAILED' if row.attempts >= self.settings.webhook_max_attempts else 'RETRY'
                    row.next_attempt = int(time.time())+min(3600, 2**row.attempts)
                    if order and row.event_type == 'order.confirmed' and order.status != 'REORGED':
                        order.fulfillment_status = row.status
                        transition(session, order, 'FULFILLMENT_FAILED' if row.status == 'FAILED' else 'FULFILLMENT_RETRY', error)
                else:
                    row.status, row.last_error = 'DELIVERED', None
                    if order and row.event_type == 'order.confirmed' and order.status != 'REORGED':
                        order.fulfillment_status = 'DELIVERED'
                        transition(session, order, 'FULFILLED', 'receiver acknowledged idempotent fulfillment')
            return True

    async def run(self):
        while True:
            try:
                worked = await self.once()
                OUTBOX_HEARTBEAT.set(time.time())
                await asyncio.sleep(0.1 if worked else 2)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning('outbox_worker_retry', extra={'error_type': type(exc).__name__})
                await asyncio.sleep(5)


async def main():
    from ..config import get_settings
    from ..database import Session, engine
    from prometheus_client import start_http_server
    start_http_server(9102, addr='0.0.0.0')
    try:
        await OutboxWorker(Session, get_settings()).run()
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
