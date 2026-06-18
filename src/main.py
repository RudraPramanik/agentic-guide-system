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

    import httpx

    qdrant_health_url = f"{settings.QDRANT_URL.rstrip('/')}/healthz"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=5.0, read=5.0),
        ) as client:
            response = await client.get(qdrant_health_url)
            response.raise_for_status()
    except Exception:
        log.warning("Qdrant unreachable - search degraded")

    yield

    flush_tracer()
    log.info("wandr.shutdown")
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Wandr API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

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

    return app


app = create_app()
