"""FastAPI application factory and entrypoint."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.redis import close_redis
from app.database.session import dispose_engine
from app.websocket.routes import router as websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info(
        "startup",
        app=settings.APP_NAME,
        version=__version__,
        environment=settings.ENVIRONMENT,
        trading_mode=settings.TRADING_MODE,
        live_trading_enabled=settings.LIVE_TRADING_ENABLED,
    )
    if settings.LIVE_TRADING_ENABLED:
        allowed, missing = settings.live_trading_allowed()
        if not allowed:
            logger.error("live_trading_interlock_failed", missing=missing)
    yield
    await dispose_engine()
    await close_redis()
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, settings.LOG_JSON)

    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description=(
            "AI-assisted, risk-gated automated trading platform. "
            "Paper trading only in V1; the LLM can only create trade proposals."
        ),
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex)
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(websocket_router)

    @app.get("/api/docs/openapi.yaml", include_in_schema=False)
    async def openapi_yaml() -> PlainTextResponse:
        """The complete OpenAPI 3 specification as YAML."""
        return PlainTextResponse(
            yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True),
            media_type="application/yaml",
        )

    @app.get("/api/docs", include_in_schema=False)
    async def api_docs() -> HTMLResponse:
        """Self-contained ReDoc page rendered from the YAML spec."""
        return HTMLResponse(
            f"""<!doctype html>
<html>
  <head>
    <title>{settings.APP_NAME} API</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>body {{ margin: 0; padding: 0; }}</style>
  </head>
  <body>
    <redoc spec-url="/api/docs/openapi.yaml"></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  </body>
</html>"""
        )

    @app.get("/", tags=["meta"], summary="Service banner")
    async def root() -> dict[str, str]:
        return {
            "service": settings.APP_NAME,
            "version": __version__,
            "docs": "/api/docs",
            "openapi": "/api/docs/openapi.yaml",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    return app


app = create_app()
