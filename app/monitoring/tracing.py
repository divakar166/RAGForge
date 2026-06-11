"""Langfuse tracing integration for the RAG pipeline."""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse = None


def get_langfuse():
    """Lazy-init Langfuse client singleton."""
    global _langfuse
    if _langfuse is None and settings.LANGFUSE_ENABLED:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                base_url=settings.LANGFUSE_BASE_URL,
            )
            _langfuse.auth_check()
            logger.info("Langfuse initialized (host=%s)", settings.LANGFUSE_BASE_URL)
        except Exception as e:
            logger.warning("Failed to initialize Langfuse: %s", e)
    return _langfuse


async def flush_langfuse():
    """Flush pending Langfuse traces (call on shutdown)."""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
            logger.debug("Langfuse traces flushed")
        except Exception as e:
            logger.warning("Failed to flush Langfuse: %s", e)


def observe(name: str | None = None, **kwargs: Any) -> Any:
    """Wrap a function with Langfuse @observe or no-op if disabled."""
    if not settings.LANGFUSE_ENABLED:
        return lambda fn: fn

    from langfuse.decorators import observe as langfuse_observe

    return langfuse_observe(name=name, **kwargs)


def score_trace(trace_id: str, name: str, value: float | int | bool, data_type: str = "NUMERIC") -> None:
    """Attach a score to an existing Langfuse trace."""
    lf = get_langfuse()
    if lf is None:
        return
    try:
        lf.score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type=data_type,
        )
    except Exception as e:
        logger.debug("Failed to score trace %s: %s", trace_id, e)
