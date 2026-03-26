"""Middleware - Rate limiting, logging, CORS"""
import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Skip logging for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)

        response: Response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else "unknown",
        )

        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        response.headers["X-Powered-By"] = "IntentAPI"
        return response
