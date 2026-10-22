"""Opt-in actual RPC test: MUD_LIVE_TEST=1, after a local deploy. Isolated DB fixture."""
import os
import pytest
from sqlalchemy import func, select
from app.blockchain import Chain
from app.config import Settings
from app.models import Event
from app.services.curve_service import CurveService
from app.workers.indexer import Indexer


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get('MUD_LIVE_TEST') != '1', reason='requires freshly deployed chain 31337')
async def test_actual_rpc_backfill_and_duplicate_replay(db):
    settings = Settings(chain_id=31337)
    chain = Chain(settings)
    try:
        await chain.validate()
        worker = Indexer(chain, db, settings)
        await worker.catch_up()
        async with db() as s:
            first = await s.scalar(select(func.count()).select_from(Event))
            assert first > 0
        await worker.catch_up()
        async with db() as s:
            assert await s.scalar(select(func.count()).select_from(Event)) == first
        spot = await CurveService(chain).spot()
        assert spot['reserve_healthy']
        quote = await CurveService(chain).quote('buy', 1000000)
        assert int(quote['output_amount']) > 0
    finally:
        await chain.close()
