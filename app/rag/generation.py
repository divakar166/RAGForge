"""Prompt assembly and LLM generation with citations."""

import logging
from typing import Any

from app.core.config import settings
from app.monitoring.tracing import observe
from app.rag.llm import LLMClient
from app.rag.retrieval import RetrievalResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant. Answer the user's question based ONLY on the provided context.
If the context doesn't contain enough information to answer, say so clearly.
Always cite your sources by referencing the document title and section path.

Format your answer with clear citations like [Source: Document Title > Section]."""


def build_context(results: list[RetrievalResult]) -> str:
    """Build a context string from retrieval results with citations."""
    sections: list[str] = []
    for i, r in enumerate(results):
        source = r.doc_title
        if r.section_path:
            source += f" > {r.section_path}"
        sections.append(f"[{i + 1}] {r.content}\n   — Source: {source}")
    return "\n\n".join(sections)


def build_messages(query: str, context: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]


@observe(name="generate_answer")
async def generate_answer(
    query: str,
    results: list[RetrievalResult],
    llm_client: LLMClient | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """Generate an answer with citations from retrieval results."""
    context = build_context(results)
    messages = build_messages(query, context)

    client = llm_client or LLMClient()
    response = await client.generate(messages, stream=stream)

    if stream:
        return response

    answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")

    citations = [
        {
            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "score": r.score,
            "document_id": r.document_id,
            "doc_title": r.doc_title,
            "section_path": r.section_path,
        }
        for r in results
    ]

    # Capture Langfuse trace ID for feedback
    trace_id = None
    if settings.LANGFUSE_ENABLED:
        try:
            from langfuse.decorators import langfuse_context
            trace_id = langfuse_context.get_current_trace_id()
        except Exception:
            pass

    return {
        "query": query,
        "answer": answer,
        "citations": citations,
        "model": client.model,
        "trace_id": trace_id,
    }
