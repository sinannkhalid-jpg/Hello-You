"""FastAPI application factory."""
from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db

setup_logging("INFO" if not settings.app_debug else "DEBUG")
log = get_logger("app")

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Educational OSINT platform. All lookups use only public, free "
            "APIs. Do not use for unauthorized access, hacking, or privacy "
            "violations."
        ),
        default_response_class=ORJSONResponse,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers (lightweight, helmet-like)
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response

    # Request timing
    @app.middleware("http")
    async def add_timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = int((time.perf_counter() - t0) * 1000)
        response.headers["X-Response-Time-ms"] = str(ms)
        return response

    # Rate limiter
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded):
        return ORJSONResponse(
            {"error": "rate_limited", "detail": str(exc.detail)},
            status_code=429,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        return ORJSONResponse(
            {"error": "http_error", "status": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled: %s", exc)
        return ORJSONResponse(
            {"error": "server_error", "detail": "Internal server error"},
            status_code=500,
        )

    @app.on_event("startup")
    async def _on_startup() -> None:
        # Create tables for dev convenience. Use Alembic in production.
        if "sqlite" in settings.database_url:
            await init_db()
            log.info("Initialized SQLite database at %s", settings.database_url)
        else:
            log.info("Skipping auto-create (set DATABASE_URL=sqlite for dev)")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    app.include_router(api_router)
    return app


app = create_app()
