import os
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.models import Base


@pytest_asyncio.fixture
async def db(tmp_path):
    # Set MUD_TEST_DATABASE_URL to an isolated PostgreSQL database to run same suite there.
    url = os.environ.get('MUD_TEST_DATABASE_URL', f'sqlite+aiosqlite:///{tmp_path}/tests.db')
    engine = create_async_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()
