from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from .config import get_settings


def make_database(url):
    options = {'pool_pre_ping': True}
    if not url.startswith('sqlite'):
        options.update(pool_size=10, max_overflow=10, pool_recycle=1800)
    engine = create_async_engine(url, **options)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


engine, Session = make_database(get_settings().database_url)


async def session_dependency():
    async with Session() as session:
        yield session


@asynccontextmanager
async def transaction(factory=Session):
    async with factory() as session, session.begin():
        yield session
