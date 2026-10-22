import asyncio
import time
import uuid
from collections import defaultdict
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

RATE_SCRIPT = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"


class RequestGuard(BaseHTTPMiddleware):
    def __init__(self, app, settings):
        super().__init__(app)
        self.settings = settings
        self.counts = defaultdict(int)
        self.lock = asyncio.Lock()
        self.minute = 0

    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        if request.method in ('POST', 'PUT', 'PATCH'):
            # Buffer at most 64 KiB, including chunked requests. No trust in Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    return JSONResponse({'error': {'code': 'body_too_large', 'request_id': request_id}}, status_code=413)
            request._body = bytes(body)
        if request.url.path.startswith('/api/'):
            client = request.client.host if request.client else 'unknown'
            minute = int(time.time())//60
            redis = getattr(request.app.state, 'redis', None)
            if redis:
                try:
                    count = await redis.eval(RATE_SCRIPT, 1, f'mud:rate:{minute}:{client}')
                except Exception:
                    return JSONResponse({'error': {'code': 'rate_limiter_unavailable', 'request_id': request_id}}, status_code=503)
            else:
                async with self.lock:
                    if self.minute != minute:
                        self.counts.clear()
                        self.minute = minute
                    self.counts[client] += 1
                    count = self.counts[client]
            if count > self.settings.requests_per_minute:
                return JSONResponse({'error': {'code': 'rate_limited', 'request_id': request_id}},
                                    status_code=429, headers={'Retry-After': '60'})
        response = await call_next(request)
        response.headers['X-Request-Id'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response
