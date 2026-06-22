import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from supabase import AsyncClient

from app.core.deps import OrganizationContext, get_org_context
from app.db.supabase import get_supabase
from app.rag.embeddings import OpenAIEmbeddingProvider
from app.rag.generation import generate_answer, generate_answer_stream
from app.rag.retrieval import RetrievalPipeline
from app.schemas.search import (
    ConversationResponse,
    FeedbackRequest,
    RAGRequest,
    RAGResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["orgs-search"])


async def _get_retrieval_pipeline(ctx: OrganizationContext) -> RetrievalPipeline:
    embed_provider = OpenAIEmbeddingProvider()
    pipeline = RetrievalPipeline(
        embed_provider=embed_provider,
        vector_store=ctx.qdrant_store,
    )
    return pipeline


@router.post("/query", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    pipeline = await _get_retrieval_pipeline(ctx)
    results = await pipeline.search(
        query=req.query,
        user_id=ctx.member["user_id"],
        org_role=ctx.member["role"],
        top_k=req.top_k,
    )

    await log_action(
        supabase, ctx.member["user_id"], "search:query",
        details={"query": req.query, "top_k": req.top_k, "results": len(results)},
        organization_id=ctx.organization["id"],
    )

    items = [
        SearchResultItem(
            score=r.score,
            text=r.content,
            content=r.content,
            document_id=r.document_id,
            document_filename=r.doc_title,
            doc_title=r.doc_title,
            chunk_index=r.chunk_index,
            section_path=r.section_path,
        )
        for r in results
    ]
    return SearchResponse(query=req.query, results=items, total=len(items))


@router.post("/ask", response_model=RAGResponse)
async def ask(
    req: RAGRequest,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] /ask query='%s' top_k=%d conversation_id=%s",
                request_id, req.query, req.top_k, req.conversation_id)

    from app.monitoring.tracing import get_current_trace_id, get_langfuse

    pipeline = await _get_retrieval_pipeline(ctx)
    logger.info("[%s] RetrievalPipeline created", request_id)

    # Build context from conversation history if thread exists
    history_context = ""
    if req.conversation_id:
        logger.info("[%s] Loading conversation history for thread %s", request_id, req.conversation_id)
        prev_msgs = await (
            supabase.table("conversations")
            .select("*")
            .eq("thread_id", req.conversation_id)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )
        if prev_msgs.data:
            parts = []
            for m in prev_msgs.data:
                parts.append(f"User: {m['query']}\nAssistant: {m['answer']}")
            history_context = "Previous conversation:\n" + "\n\n".join(parts) + "\n\n"
            logger.info("[%s] Loaded %d history messages", request_id, len(prev_msgs.data))

    logger.info("[%s] Running hybrid search...", request_id)
    results = await pipeline.search(
        query=req.query,
        user_id=ctx.member["user_id"],
        org_role=ctx.member["role"],
        top_k=req.top_k,
    )
    logger.info("[%s] Search returned %d results", request_id, len(results))

    if not results:
        return RAGResponse(
            query=req.query, answer="No relevant documents found.",
            citations=[], model="none",
        )

    if req.stream:
        logger.info("[%s] Streaming mode — returning token stream", request_id)
        stream_gen = generate_answer_stream(req.query, results, history_context=history_context)
        return StreamingResponse(stream_gen, media_type="text/event-stream")

    lf = get_langfuse()
    if lf is not None:
        logger.info("[%s] Langfuse tracing enabled", request_id)
        from langfuse import propagate_attributes

        with lf.start_as_current_observation(
            as_type="span", name="ask", input={"query": req.query},
        ) as root_span:
            with propagate_attributes(
                user_id=ctx.member["user_id"],
                session_id=ctx.member["user_id"],
                tags=["rag:ask"],
            ):
                logger.info("[%s] Generating answer with LLM...", request_id)
                answer = await generate_answer(req.query, results, history_context=history_context)
                logger.info("[%s] Answer generated successfully", request_id)
                root_span.update(output=answer)
                trace_id = get_current_trace_id()
                answer["trace_id"] = trace_id
    else:
        logger.info("[%s] Langfuse disabled — running without tracing", request_id)
        logger.info("[%s] Generating answer with LLM...", request_id)
        answer = await generate_answer(req.query, results, history_context=history_context)
        logger.info("[%s] Answer generated successfully", request_id)

    trace_id = answer.pop("trace_id", None)

    await log_action(
        supabase, ctx.member["user_id"], "search:ask",
        details={"query": req.query, "top_k": req.top_k},
        organization_id=ctx.organization["id"],
    )

    conv_data = {
        "organization_id": ctx.organization["id"],
        "user_id": ctx.member["user_id"],
        "query": req.query,
        "answer": answer.get("answer", ""),
        "citations": answer.get("citations"),
        "trace_id": trace_id,
    }
    if req.conversation_id:
        conv_data["thread_id"] = req.conversation_id
        await supabase.table("conversation_threads").update({"updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", req.conversation_id).execute()

    await supabase.table("conversations").insert(conv_data).execute()
    logger.info("[%s] Conversation saved to DB", request_id)

    resp = RAGResponse(**answer)
    resp.trace_id = trace_id
    logger.info("[%s] RAGResponse built — returning to client", request_id)
    return resp


@router.get("/history", response_model=list[ConversationResponse])
async def search_history(
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await (
        supabase.table("conversations")
        .select("*")
        .eq("organization_id", ctx.organization["id"])
        .eq("user_id", ctx.member["user_id"])
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [
        ConversationResponse(
            id=c["id"],
            query=c["query"],
            answer=c["answer"],
            citations=c.get("citations"),
            feedback_score=c.get("feedback_score"),
            created_at=c.get("created_at"),
        )
        for c in (result.data or [])
    ]


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    from app.monitoring.tracing import score_trace

    score_val = (
        1
        if req.score in ("thumbs_up", 1, "1")
        else 0 if req.score in ("thumbs_down", 0, "0")
        else int(req.score)
    )

    score_trace(
        trace_id=req.trace_id,
        name="user_satisfaction",
        value=score_val,
        data_type="BOOLEAN",
    )

    await supabase.table("conversations").update({"feedback_score": score_val}).eq("trace_id", req.trace_id).execute()

    await log_action(
        supabase, ctx.member["user_id"], "search:feedback",
        details={"trace_id": req.trace_id, "score": score_val, "comment": req.comment},
        organization_id=ctx.organization["id"],
    )
    return {"status": "ok"}
