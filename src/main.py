"""Wandr — FastAPI application factory, lifespan, and health endpoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.core.database.session import dispose_engine, ping_db
from src.core.exceptions import WandrError
from src.core.observability.logging import configure_logging, get_logger
from src.core.observability.tracing import flush_tracer
from src.core.responses import ApiResponse, ErrorResponse

log = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    log.info("wandr.startup", env=settings.ENVIRONMENT, version=settings.APP_VERSION)

    try:
        await ping_db()
    except Exception as exc:
        log.critical("DB unreachable", error=str(exc))
        raise SystemExit(1) from exc

    from src.search.client import close_qdrant_client, ensure_places_collection
    from src.search.embeddings import ensure_embedding_model_loaded

    await ensure_places_collection()
    await ensure_embedding_model_loaded()

    yield

    flush_tracer()
    log.info("wandr.shutdown")
    await close_qdrant_client()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Wandr API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Outermost middleware — added last (Starlette LIFO).
    from src.core.middleware.logging import RequestLoggingMiddleware
    from src.core.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(WandrError)
    async def wandr_error_handler(_request: Request, exc: WandrError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code="validation_error",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error",
                message="An unexpected error occurred",
            ).model_dump(),
        )

    @app.get("/api/v1/health", response_model=None)
    async def health():
        try:
            await ping_db()
        except Exception:
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    code="db_unavailable",
                    message="Database unreachable",
                ).model_dump(),
            )
        return ApiResponse(
            data={
                "status": "ok",
                "env": settings.ENVIRONMENT,
                "version": settings.APP_VERSION,
            }
        ).model_dump()

    # ── Routers — registered here as phases complete ──
    from src.auth.router import router as auth_router
    from src.destinations.router import router as destinations_router
    from src.places.router import router as places_router

    app.include_router(auth_router)
    app.include_router(destinations_router)
    app.include_router(places_router)

    return app


app = create_app()
