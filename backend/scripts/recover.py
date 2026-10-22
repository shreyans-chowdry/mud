#!/usr/bin/env python3
"""Explicit local projection reconciliation. Never deletes orders or delivery audit records."""
import argparse
import asyncio
from sqlalchemy import select
from app.blockchain import Chain
from app.config import get_settings
from app.database import Session, engine
from app.models import Checkpoint, Outbox
from app.workers.indexer import Indexer


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rewind-to', type=int)
    parser.add_argument('--retry-outbox', help='Exact FAILED outbox ID; requires receiver idempotency')
    parser.add_argument('--acknowledge', action='store_true')
    args = parser.parse_args()
    if not args.acknowledge or (args.rewind_to is None) == (args.retry_outbox is None):
        parser.error('select one action and --acknowledge; stop workers first')
    settings = get_settings()
    chain = Chain(settings)
    try:
        async with Session() as session, session.begin():
            if args.retry_outbox:
                row = await session.scalar(select(Outbox).where(Outbox.id == args.retry_outbox).with_for_update())
                if not row or row.status != 'FAILED':
                    raise ValueError('only exact FAILED delivery can be retried')
                row.status, row.attempts, row.next_attempt = 'RETRY', 0, 0
            else:
                if args.rewind_to < settings.start_block-1:
                    raise ValueError('rewind before configured start boundary')
                worker = Indexer(chain, Session, settings)
                await worker._acquire(session)
                checkpoint = await session.get(Checkpoint, settings.chain_id)
                if not checkpoint or args.rewind_to >= checkpoint.block_number:
                    raise ValueError('rewind must be below existing checkpoint')
                await worker.rollback(session, args.rewind_to)
                checkpoint.block_number = args.rewind_to
                checkpoint.block_hash = (await chain.block(args.rewind_to))['hash'] if args.rewind_to >= 0 else '0x'+'00'*32
        print('Recovery mutation committed; restart workers and inspect reconciliation events')
    finally:
        await chain.close()
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
