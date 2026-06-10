import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models.document import Document
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import DocumentAccessRequest, DocumentResponse
from app.services.audit import log_action
from app.services.rbac import has_any_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await has_any_permission(user, ["document:create", "*:*"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    allowed = [e.strip() for e in settings.ALLOWED_EXTENSIONS.split(",") if e.strip()]
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

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        title=file.filename or "untitled",
        file_path=file_path,
        file_type=ext,
        file_size=len(content),
        status="uploaded",
        owner_id=str(user.id),
    )
    db.add(doc)
    await db.flush()
    await log_action(
        db,
        str(user.id),
        "document:upload",
        "document",
        str(doc.id),
        {"filename": file.filename, "size": len(content)},
    )

    # Dispatch Celery task for async processing
    try:
        from app.workers.tasks import process_document as process_doc_task

        process_doc_task.delay(str(doc.id))
    except Exception as e:
        logger.warning("Failed to dispatch Celery task: %s", e)

    return {
        "id": str(doc.id),
        "title": doc.title,
        "status": doc.status,
        "detail": "Document queued for processing",
    }


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # RBAC: admins see all, others see their own + public documents
    if user.is_superuser:
        result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    else:
        result = await db.execute(
            select(Document)
            .where((Document.owner_id == str(user.id)) | Document.is_public)
            .order_by(Document.created_at.desc())
        )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=str(d.id),
            title=d.title,
            file_type=d.file_type,
            file_size=d.file_size,
            status=d.status,
            is_public=d.is_public,
            owner_id=d.owner_id,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # RBAC check
    if not user.is_superuser and str(doc.owner_id) != str(user.id) and not doc.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await log_action(db, str(user.id), "document:read", "document", document_id)
    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        is_public=doc.is_public,
        owner_id=doc.owner_id,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not user.is_superuser and str(doc.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete")

    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await log_action(db, str(user.id), "document:delete", "document", document_id)
    return {"detail": "Document deleted"}


@router.post("/{document_id}/access")
async def set_document_access(
    document_id: str,
    req: DocumentAccessRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID")
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not user.is_superuser and str(doc.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if req.is_public is not None:
        doc.is_public = req.is_public

    # TODO: Store allowed_role_ids and allowed_user_ids in a junction table
    # For now, they are stored at Qdrant payload level during processing

    await log_action(
        db,
        str(user.id),
        "document:set_access",
        "document",
        document_id,
        req.model_dump(),
    )
    return {"detail": "Access rules updated"}
