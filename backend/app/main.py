import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pythonjsonlogger.json import JsonFormatter
from redis.asyncio import Redis
from sqlalchemy import text
from .api import router
from .blockchain import Chain
from .config import get_settings
from .database import Session, engine
from .security import RequestGuard
from .services.airdrop_service import AirdropService
from .services.curve_service import CurveService
from .workers.indexer import Indexer
from .workers.outbox_worker import OutboxWorker

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter('{asctime} {levelname} {name} {message}', style='{'))
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger('mud')


def create_app(settings=None, sessions=None, chain=None):
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings
        app.state.sessions = sessions or Session
        app.state.chain = chain or Chain(settings)
        app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
        app.state.curve = CurveService(app.state.chain, app.state.redis, settings.cache_ttl)
        app.state.airdrop = AirdropService(settings.eligibility_file)
        tasks = []
        if settings.run_workers:
            tasks = [asyncio.create_task(Indexer(app.state.chain, app.state.sessions, settings, app.state.redis).run()),
                     asyncio.create_task(OutboxWorker(app.state.sessions, settings).run())]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if app.state.redis:
                await app.state.redis.aclose()
            if not chain:
                await app.state.chain.close()
            if not sessions:
                await engine.dispose()

    app = FastAPI(title='MUD Protocol API', version='1.0.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
    app.add_middleware(RequestGuard, settings=settings)
    app.include_router(router)

    def error(request, status, code, message):
        return JSONResponse({'error': {'code': code, 'message': message,
            'request_id': getattr(request.state, 'request_id', None)}}, status_code=status)

    @app.exception_handler(ValueError)
    async def validation(request: Request, exc: ValueError):
        return error(request, 422, 'invalid_request', str(exc)[:200])

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation(request: Request, exc: RequestValidationError):
        return error(request, 422, 'invalid_request', 'request schema validation failed')

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(request, exc.status_code, 'request_failed', str(exc.detail))

    @app.exception_handler(Exception)
    async def unavailable(request: Request, exc: Exception):
        log.warning('request_failed', extra={'error_type': type(exc).__name__,
                    'request_id': getattr(request.state, 'request_id', None)})
        return error(request, 503, 'dependency_unavailable', 'chain, deployment, database or upstream service unavailable')

    @app.get('/health')
    async def health():
        return {'status': 'alive'}

    @app.get('/ready')
    async def ready(request: Request):
        async with request.app.state.sessions() as session:
            await session.execute(text('SELECT 1'))
            # Existence of migrated table is part of readiness.
            await session.execute(text('SELECT chain_id FROM checkpoints LIMIT 1'))
        await request.app.state.chain.validate()
        if request.app.state.redis:
            await request.app.state.redis.ping()
        return {'status': 'ready', 'chain_id': settings.chain_id}

    @app.get('/metrics', include_in_schema=False)
    async def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
