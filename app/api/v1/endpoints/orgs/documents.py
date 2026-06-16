import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import OrganizationContext, get_org_context, require_org_role
from app.db.models.document import Document
from app.db.session import get_db
from app.schemas.document import DocumentAccessRequest, DocumentResponse, PaginatedDocumentResponse
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["orgs-documents"])


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin", "member")),
    db: AsyncSession = Depends(get_db),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    allowed = {e.strip() for e in settings.ALLOWED_EXTENSIONS.split(",") if e.strip()}
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{ext} not allowed",
        )

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    org_storage = os.path.join(settings.UPLOAD_DIR, str(ctx.organization.id))
    os.makedirs(org_storage, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(org_storage, f"{file_id}.{ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        organization_id=ctx.organization.id,
        title=file.filename or "untitled",
        file_path=file_path,
        file_type=ext,
        file_size=len(content),
        status="uploaded",
        uploaded_by_id=ctx.member.user_id,
    )
    db.add(doc)
    await db.flush()

    await log_action(
        db, ctx.member.user_id, "document:upload",
        resource_type="document", resource_id=doc.id,
        details={"filename": file.filename, "size": len(content)},
        organization_id=ctx.organization.id,
    )

    try:
        from app.workers.celery_app import celery_app
        celery_app.send_task("process_document", args=[str(doc.id), str(ctx.organization.id)])
    except Exception as e:
        logger.warning("Failed to dispatch Celery task: %s", e)

    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        filename=doc.title,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        is_public_in_org=doc.is_public_in_org,
        uploaded_by_id=str(doc.uploaded_by_id),
        organization_id=str(doc.organization_id),
        collection_id=str(doc.collection_id) if doc.collection_id else None,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("")
async def list_documents(
    page: int = 1,
    per_page: int = 20,
    ctx: OrganizationContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    org_id = ctx.organization.id
    base_query = select(Document).where(Document.organization_id == org_id)

    if ctx.member.role not in ("owner", "admin"):
        base_query = base_query.where(
            (Document.uploaded_by_id == ctx.member.user_id) | Document.is_public_in_org
        )

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    docs = result.scalars().all()

    return PaginatedDocumentResponse(
        items=[
            DocumentResponse(
                id=str(d.id),
                title=d.title,
                filename=d.title,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                is_public_in_org=d.is_public_in_org,
                uploaded_by_id=str(d.uploaded_by_id),
                organization_id=str(d.organization_id),
                collection_id=str(d.collection_id) if d.collection_id else None,
                chunk_count=d.chunk_count,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.organization_id == ctx.organization.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if ctx.member.role not in ("owner", "admin"):
        if doc.uploaded_by_id != ctx.member.user_id and not doc.is_public_in_org:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await log_action(
        db, ctx.member.user_id, "document:read",
        resource_type="document", resource_id=doc.id,
        organization_id=ctx.organization.id,
    )

    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        filename=doc.title,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        is_public_in_org=doc.is_public_in_org,
        uploaded_by_id=str(doc.uploaded_by_id),
        organization_id=str(doc.organization_id),
        collection_id=str(doc.collection_id) if doc.collection_id else None,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.organization_id == ctx.organization.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete from Qdrant too
    ctx.qdrant_store.delete_by_document_id(str(doc.id))

    await db.delete(doc)
    await log_action(
        db, ctx.member.user_id, "document:delete",
        resource_type="document", resource_id=doc.id,
        organization_id=ctx.organization.id,
    )
    return {"detail": "Document deleted"}


@router.post("/{document_id}/access")
async def set_document_access(
    document_id: str,
    req: DocumentAccessRequest,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(
            Document.id == doc_uuid,
            Document.organization_id == ctx.organization.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if req.is_public_in_org is not None:
        doc.is_public_in_org = req.is_public_in_org

    await log_action(
        db, ctx.member.user_id, "document:set_access",
        resource_type="document", resource_id=doc.id,
        details=req.model_dump(),
        organization_id=ctx.organization.id,
    )
    return {"detail": "Access rules updated"}
