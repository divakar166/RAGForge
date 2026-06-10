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
from app.schemas.search import ChunkResult, RAGRequest, RAGResponse, SearchRequest, SearchResponse
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

    return SearchResponse(
        query=req.query,
        results=[
            ChunkResult(
                content=r.content,
                score=r.score,
                document_id=r.document_id,
                doc_title=r.doc_title,
                chunk_index=r.chunk_index,
                section_path=r.section_path,
            )
            for r in results
        ],
    )


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

    return RAGResponse(**answer)


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
            "action": log.action,
            "query": (log.details or {}).get("query", ""),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]
