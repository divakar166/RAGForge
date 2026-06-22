"""Prompt assembly and LLM generation with citations."""

import logging
from typing import Any, AsyncGenerator

from app.core.config import settings
from app.monitoring.tracing import observe
from app.rag.llm import LLMClient
from app.rag.retrieval import RetrievalResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a precise RAG assistant. Your answers must be grounded exclusively in the provided context.

## Reasoning
1. Identify which context chunks are relevant to the question.
2. Synthesise across multiple sources on the same topic.
3. If sources conflict, flag the conflict and note which source appears more authoritative (e.g. Board-approved minutes vs a draft forecast).
4. Then produce your final answer.

## Citations
- Cite every factual claim with the source number from the context: `Project Atlas was announced on January 15, 2026 [1].`
- When multiple sources support the same claim, cite all: `The budget was $2.8M [3][7].`
- When sources conflict, state: `Source [X] says … but source [Y] says … — the Board minutes are authoritative because they record the approved vote.`

## Quality
- If the context lacks sufficient information, say: `I cannot find sufficient information in the provided documents to answer this question.`
- Be specific — always include numbers, dates, and names when present.
- Decline to speculate on hypotheticals or topics outside the context.
- Use bullet points for multi-fact answers.
- Use the exact terminology from the source documents."""


def build_context(results: list[RetrievalResult]) -> str:
    """Build a context string from retrieval results with citations."""
    sections: list[str] = []
    for i, r in enumerate(results):
        source = f"\"{r.doc_title}\""
        if r.section_path:
            source += f" > {r.section_path}"
        classification = r.metadata.get("classification", "") if r.metadata else ""
        tags = f" [classification: {classification}]" if classification else ""
        sections.append(f"[{i + 1}] {r.content}\n   — Source: {source}{tags}")
    return "\n\n".join(sections)


def build_messages(query: str, context: str, history_context: str = "") -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history_context:
        messages.append({"role": "system", "content": history_context})
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"})
    return messages


@observe(name="generate_answer")
async def generate_answer(
    query: str,
    results: list[RetrievalResult],
    llm_client: LLMClient | None = None,
    stream: bool = False,
    history_context: str = "",
) -> dict[str, Any]:
    """Generate an answer with citations from retrieval results."""
    context = build_context(results)
    messages = build_messages(query, context, history_context)

    client = llm_client or LLMClient()
    response = await client.generate(messages, stream=stream)

    if stream:
        return response

    answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")

    citations = [
        {
            "text": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "score": r.score,
            "document_id": r.document_id,
            "document_filename": r.doc_title,
            "doc_title": r.doc_title,
            "section_path": r.section_path,
            "metadata": {},
            "chunk_index": r.chunk_index,
        }
        for r in results
    ]

    # Capture Langfuse trace ID for feedback
    trace_id = None
    if settings.LANGFUSE_ENABLED:
        try:
            from app.monitoring.tracing import get_current_trace_id

            trace_id = get_current_trace_id()
        except Exception:
            pass

    return {
        "query": query,
        "answer": answer,
        "citations": citations,
        "model": client.model,
        "trace_id": trace_id,
    }


@observe(name="generate_answer_stream")
async def generate_answer_stream(
    query: str,
    results: list[RetrievalResult],
    history_context: str = "",
) -> AsyncGenerator[str, None]:
    """Generate a streaming answer, yielding content tokens as they arrive."""
    context = build_context(results)
    messages = build_messages(query, context, history_context)
    client = LLMClient()
    async for token in client.generate_stream(messages):
        yield token
