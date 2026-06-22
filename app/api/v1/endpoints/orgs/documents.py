import logging
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from supabase import AsyncClient

from app.core.config import settings
from app.core.deps import OrganizationContext, get_org_context, require_org_role
from app.db.supabase import get_supabase
from app.schemas.document import DocumentAccessRequest, DocumentResponse, DocumentUpdateRequest, PaginatedDocumentResponse
from app.services.audit import log_action
from app.rag.vector_store import allowed_roles_for_classification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["orgs-documents"])


def _resolve_path(stored: str) -> str:
    if os.path.isabs(stored):
        return stored
    if stored.startswith("./"):
        return os.path.abspath(stored)
    return os.path.abspath(os.path.join(settings.UPLOAD_DIR, stored))


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    classification: str = Form("internal"),
    collection_id: str | None = Form(None),
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
    allowed = {e.strip() for e in settings.ALLOWED_EXTENSIONS.split(",") if e.strip()}
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{ext} not allowed",
        )

    if classification not in ("public", "internal", "confidential"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="classification must be one of: public, internal, confidential",
        )

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )

    if collection_id:
        coll_check = await supabase.table("collections").select("id").eq("id", collection_id).eq("organization_id", ctx.organization["id"]).execute()
        if not coll_check.data:
            raise HTTPException(status_code=404, detail="Collection not found")

    org_storage = os.path.join(settings.UPLOAD_DIR, ctx.organization["id"])
    os.makedirs(org_storage, exist_ok=True)
    file_id = str(uuid.uuid4())
    rel_path = os.path.join(ctx.organization["id"], f"{file_id}.{ext}")
    full_path = os.path.join(settings.UPLOAD_DIR, rel_path)

    with open(full_path, "wb") as f:
        f.write(content)

    allowed_roles = allowed_roles_for_classification(classification)

    doc_data = {
        "organization_id": ctx.organization["id"],
        "title": file.filename or "untitled",
        "file_path": rel_path,
        "file_type": ext,
        "file_size": len(content),
        "status": "uploaded",
        "classification": classification,
        "allowed_roles": allowed_roles,
        "uploaded_by_id": ctx.member["user_id"],
    }
    if collection_id:
        doc_data["collection_id"] = collection_id
    insert = await supabase.table("documents").insert(doc_data).select("*").execute()
    doc = insert.data[0] if insert.data else None
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create document record")

    await log_action(
        supabase, ctx.member["user_id"], "document:upload",
        resource_type="document", resource_id=doc["id"],
        details={"filename": file.filename, "size": len(content)},
        organization_id=ctx.organization["id"],
    )

    try:
        from app.workers.celery_app import celery_app
        celery_app.send_task("process_document", args=[str(doc["id"]), str(ctx.organization["id"])])
    except Exception as e:
        logger.warning("Failed to dispatch Celery task: %s", e)

    return DocumentResponse(
        id=doc["id"],
        title=doc["title"],
        filename=doc["title"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        classification=doc.get("classification", "internal"),
        allowed_roles=doc.get("allowed_roles", ["member"]),
        uploaded_by_id=doc["uploaded_by_id"],
        organization_id=doc["organization_id"],
        collection_id=doc.get("collection_id"),
        chunk_count=doc.get("chunk_count", 0),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.get("")
async def list_documents(
    page: int = 1,
    per_page: int = 20,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    org_id = ctx.organization["id"]
    query = supabase.table("documents").select("*", count="exact").eq("organization_id", org_id)

    if ctx.member["role"] not in ("owner", "admin"):
        query = query.contains("allowed_roles", [ctx.member["role"]])

    offset = (page - 1) * per_page
    result = await query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    total = result.count if hasattr(result, "count") else 0

    return PaginatedDocumentResponse(
        items=[
            DocumentResponse(
                id=d["id"],
                title=d["title"],
                filename=d["title"],
                file_type=d["file_type"],
                file_size=d["file_size"],
                status=d["status"],
                classification=d.get("classification", "internal"),
                allowed_roles=d.get("allowed_roles", ["member"]),
                uploaded_by_id=d["uploaded_by_id"],
                organization_id=d["organization_id"],
                collection_id=d.get("collection_id"),
                chunk_count=d.get("chunk_count", 0),
                created_at=d.get("created_at"),
                updated_at=d.get("updated_at"),
            )
            for d in (result.data or [])
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    doc_resp = await (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("organization_id", ctx.organization["id"])
        .single()
        .execute()
    )
    doc = doc_resp.data
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if ctx.member["role"] not in ("owner", "admin"):
        if ctx.member["role"] not in doc.get("allowed_roles", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await log_action(
        supabase, ctx.member["user_id"], "document:read",
        resource_type="document", resource_id=doc["id"],
        organization_id=ctx.organization["id"],
    )

    return DocumentResponse(
        id=doc["id"],
        title=doc["title"],
        filename=doc["title"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        classification=doc.get("classification", "internal"),
        allowed_roles=doc.get("allowed_roles", ["member"]),
        uploaded_by_id=doc["uploaded_by_id"],
        organization_id=doc["organization_id"],
        collection_id=doc.get("collection_id"),
        chunk_count=doc.get("chunk_count", 0),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    doc_resp = await (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("organization_id", ctx.organization["id"])
        .single()
        .execute()
    )
    doc = doc_resp.data
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if os.path.exists(_resolve_path(doc["file_path"])):
        os.remove(_resolve_path(doc["file_path"]))

    ctx.qdrant_store.delete_by_document_id(str(doc["id"]))

    await supabase.table("documents").delete().eq("id", document_id).execute()

    await log_action(
        supabase, ctx.member["user_id"], "document:delete",
        resource_type="document", resource_id=doc["id"],
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Document deleted"}


@router.post("/{document_id}/access")
async def set_document_access(
    document_id: str,
    req: DocumentAccessRequest,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    doc_resp = await (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("organization_id", ctx.organization["id"])
        .single()
        .execute()
    )
    doc = doc_resp.data
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if req.allowed_roles is not None:
        await supabase.table("documents").update({"allowed_roles": req.allowed_roles}).eq("id", document_id).execute()
        if ctx.qdrant_store:
            ctx.qdrant_store.update_point_payload(str(doc["id"]), {"allowed_roles": req.allowed_roles})

    await log_action(
        supabase, ctx.member["user_id"], "document:set_access",
        resource_type="document", resource_id=doc["id"],
        details=req.model_dump(),
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Access rules updated"}


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    doc_resp = await (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("organization_id", ctx.organization["id"])
        .single()
        .execute()
    )
    doc = doc_resp.data
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if ctx.member["role"] not in ("owner", "admin"):
        if ctx.member["role"] not in doc.get("allowed_roles", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    file_path = _resolve_path(doc["file_path"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/markdown",
        "html": "text/html",
    }
    media_type = media_types.get(doc["file_type"], "application/octet-stream")

    await log_action(
        supabase, ctx.member["user_id"], "document:download",
        resource_type="document", resource_id=doc["id"],
        organization_id=ctx.organization["id"],
    )

    return FileResponse(path=file_path, filename=doc["title"], media_type=media_type)


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    req: DocumentUpdateRequest,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "classification" in update_data:
        cls = update_data["classification"]
        if cls not in ("public", "internal", "confidential"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid classification")
        update_data["allowed_roles"] = allowed_roles_for_classification(cls)

    result = await supabase.table("documents").update(update_data).eq("id", document_id).eq("organization_id", ctx.organization["id"]).select("*").execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc = result.data[0]
    if hasattr(ctx, "qdrant_store") and ctx.qdrant_store:
        payload_updates = {}
        if "allowed_roles" in update_data:
            payload_updates["allowed_roles"] = update_data["allowed_roles"]
        if "classification" in update_data:
            payload_updates["classification"] = update_data["classification"]
        if payload_updates:
            ctx.qdrant_store.update_point_payload(str(doc["id"]), payload_updates)

    await log_action(
        supabase, ctx.member["user_id"], "document:update",
        resource_type="document", resource_id=doc["id"],
        details=update_data,
        organization_id=ctx.organization["id"],
    )

    return DocumentResponse(
        id=doc["id"],
        title=doc["title"],
        filename=doc["title"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        classification=doc.get("classification", "internal"),
        allowed_roles=doc.get("allowed_roles", ["member"]),
        uploaded_by_id=doc["uploaded_by_id"],
        organization_id=doc["organization_id"],
        collection_id=doc.get("collection_id"),
        chunk_count=doc.get("chunk_count", 0),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
