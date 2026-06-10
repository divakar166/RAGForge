"""Langfuse tracing integration for the RAG pipeline.

Wraps retrieval, LLM calls, and generation with @observe decorators
for full observability in Langfuse.
"""
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse = None


def get_langfuse():
    """Lazy-init Langfuse client."""
    global _langfuse
    if _langfuse is None and settings.LANGFUSE_ENABLED:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            logger.info("Langfuse initialized")
        except Exception as e:
            logger.warning("Failed to initialize Langfuse: %s", e)
    return _langfuse


def observe(name: str | None = None, **kwargs) -> Any:
    """Decorator to wrap a function with Langfuse observation.

    Falls back to no-op if Langfuse is disabled or unavailable.
    """
    if not settings.LANGFUSE_ENABLED:
        return _noop_decorator

    try:
        from langfuse.decorators import observe as langfuse_observe
        return langfuse_observe(name=name, **kwargs)
    except ImportError:
        return _noop_decorator


def _noop_decorator(fn):
    return fn


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
