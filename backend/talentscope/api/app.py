"""FastAPI application factory. Run with: uvicorn --factory talentscope.api.app:create_app"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from talentscope import __version__
from talentscope.api import routes_admin, routes_public
from talentscope.api.deps import SessionDep
from talentscope.api.errors import ApiError, register_error_handlers
from talentscope.config import Settings, get_settings
from talentscope.log_config import configure_logging

logger = logging.getLogger("talentscope.api")
_REQUEST_ID = re.compile("[A-Za-z0-9._-]{1,64}")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format)
    app = FastAPI(
        title="TalentScope API",
        version=__version__,
        description=(
            "Read API for TalentScope job-market data. All analytics describe only the "
            "sources listed in /api/v1/sources/coverage and are not a census of the "
            "Indonesian labour market."
        ),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # A caller's ID is reused only if it is a plain token; it is echoed in a header and
        # written to logs, so arbitrary text is replaced rather than passed through.
        incoming = request.headers.get("x-request-id", "")
        request.state.request_id = incoming if _REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "request",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    register_error_handlers(app)

    @app.get("/api/v1/health", tags=["health"])
    def health(session: SessionDep) -> dict[str, str]:
        """Liveness plus a database round trip, so a broken DB shows up as unhealthy."""
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.error("health check: database unavailable", extra={"error": type(exc).__name__})
            raise ApiError(503, "database_unavailable", "Database is not reachable.") from exc
        return {"status": "ok", "version": __version__}

    app.include_router(routes_public.router)
    app.include_router(routes_admin.router)
    return app
