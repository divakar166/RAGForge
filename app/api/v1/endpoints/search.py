from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.session import get_db
from app.rag.embeddings import TEIEmbeddingProvider
from app.rag.generation import generate_answer
from app.rag.retrieval import RetrievalPipeline
from app.schemas.search import FeedbackRequest, RAGRequest, RAGResponse, SearchRequest, SearchResponse, SearchResultItem
from app.services.audit import log_action
from app.services.rbac import has_any_permission

router = APIRouter(prefix="/search", tags=["search"])


async def _get_retrieval_pipeline() -> RetrievalPipeline:
    embed_provider = TEIEmbeddingProvider()
    pipeline = RetrievalPipeline(embed_provider=embed_provider)
    return pipeline


@router.post("/query")
async def search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await has_any_permission(user, ["search:query", "*:*"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    pipeline = await _get_retrieval_pipeline()
    role_ids = [str(r.id) for r in user.roles]
    results = await pipeline.search(
        query=req.query,
        user_id=str(user.id),
        role_ids=role_ids,
        top_k=req.top_k,
    )

    await log_action(
        db,
        str(user.id),
        "search:query",
        details={"query": req.query, "top_k": req.top_k, "results": len(results)},
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


@router.post("/ask")
async def ask(
    req: RAGRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await has_any_permission(user, ["search:query", "*:*"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    pipeline = await _get_retrieval_pipeline()
    role_ids = [str(r.id) for r in user.roles]
    results = await pipeline.search(
        query=req.query,
        user_id=str(user.id),
        role_ids=role_ids,
        top_k=req.top_k,
    )

    if not results:
        return RAGResponse(
            query=req.query,
            answer="No relevant documents found.",
            citations=[],
            model="none",
        )

    answer = await generate_answer(req.query, results)
    await log_action(db, str(user.id), "search:ask", details={"query": req.query, "top_k": req.top_k})

    trace_id = answer.pop("trace_id", None)
    resp = RAGResponse(**answer)
    resp.trace_id = trace_id
    resp.citations = [
        SearchResultItem(
            score=c.get("score", 0),
            text=c.get("content", ""),
            content=c.get("content", ""),
            document_id=c.get("document_id", ""),
            document_filename=c.get("doc_title", ""),
            doc_title=c.get("doc_title", ""),
        )
        for c in resp.citations
    ]
    return resp


@router.get("/history")
async def search_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.user_id == str(user.id),
            AuditLog.action.in_(["search:query", "search:ask"]),
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "type": "ask" if log.action == "search:ask" else "search",
            "query": (log.details or {}).get("query", ""),
            "created_at": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit user feedback (thumbs up/down) for a RAG response trace."""
    from app.monitoring.tracing import score_trace

    score_val = 1 if req.score in ("thumbs_up", 1, "1") else 0 if req.score in ("thumbs_down", 0, "0") else int(req.score)
    score_trace(
        trace_id=req.trace_id,
        name="user_satisfaction",
        value=score_val,
        data_type="BOOLEAN",
    )

    await log_action(
        db,
        str(user.id),
        "search:feedback",
        details={"trace_id": req.trace_id, "score": score_val, "comment": req.comment},
    )

    return {"status": "ok"}
