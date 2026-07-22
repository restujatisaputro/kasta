from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kasta_api import __version__
from kasta_api.api.metadata import API_DESCRIPTION, OPENAPI_TAGS
from kasta_api.api.router import api_router
from kasta_api.core.config import get_settings
from kasta_api.core.errors import register_exception_handlers
from kasta_api.core.logging import configure_logging
from kasta_api.core.middleware import ErrorHandlingMiddleware, RequestContextMiddleware
from kasta_api.core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from kasta_api.db.session import dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("KASTA API started")
    yield
    await dispose_engine()
    logger.info("KASTA API stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title="KASTA API",
        summary="API Keuangan dan Asistensi UMKM",
        description=API_DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.expose_api_docs else None,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
        openapi_tags=OPENAPI_TAGS,
    )
    register_exception_handlers(app)

    # Urutan penambahan menghasilkan: request context -> CORS -> error handler -> router.
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_strings,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", settings.request_id_header],
        expose_headers=[settings.request_id_header],
    )
    app.add_middleware(SecurityHeadersMiddleware, production=settings.environment == "production")
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware, header_name=settings.request_id_header)

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
