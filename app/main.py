import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logger import setup_logging
from app.rag.vector_store import QdrantStore
from app.services.rate_limit import rate_limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    setup_logging()
    logger.info("Starting %s", settings.APP_NAME)

    # Initialize Langfuse eagerly so @observe decorators work
    if settings.LANGFUSE_ENABLED:
        from app.monitoring.tracing import get_langfuse

        get_langfuse()

    # Initialize Qdrant collection (non-async operation)
    try:
        store = QdrantStore()
        store.ensure_collection(settings.EMBEDDING_DIM)
        logger.info("Qdrant collection '%s' ready", settings.QDRANT_COLLECTION)
    except Exception as e:
        logger.warning("Qdrant not available on startup: %s", e)

    yield

    # Flush Langfuse traces before shutdown
    if settings.LANGFUSE_ENABLED:
        from app.monitoring.tracing import flush_langfuse

        await flush_langfuse()

    await rate_limiter.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
