import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .database import AsyncSessionLocal, init_db
from .routers import articles, pipeline
from .schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database…")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="HN Article Enricher",
    description=(
        "Scrapes Hacker News front page, enriches each article with OpenAI "
        "(category, tags, summary, sentiment), and exposes the results via REST."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(articles.router)
app.include_router(pipeline.router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    db_status = "disconnected"
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:  # noqa: BLE001
            logger.error("DB health probe failed: %s", exc)

    return HealthResponse(status="ok", database=db_status, version="1.0.0")


# ---------------------------------------------------------------------------
# Global error handler — never leak internal stack traces
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
