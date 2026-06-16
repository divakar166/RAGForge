import logging

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.core.deps import OrganizationContext, get_org_context, require_org_role
from app.db.supabase import get_supabase
from app.schemas.collection import CollectionCreate, CollectionResponse, CollectionUpdate
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["orgs-collections"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_collection(
    req: CollectionCreate,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await (
        supabase.table("collections")
        .insert({
            "organization_id": ctx.organization["id"],
            "name": req.name,
            "description": req.description,
        })
        .select("*")
        .execute()
    )
    collection = result.data[0]

    await log_action(
        supabase, ctx.member["user_id"], "collection:create",
        resource_type="collection", resource_id=collection["id"],
        details={"name": req.name},
        organization_id=ctx.organization["id"],
    )

    return CollectionResponse(
        id=collection["id"],
        organization_id=collection["organization_id"],
        name=collection["name"],
        description=collection.get("description", ""),
        is_public=collection.get("is_public", False),
        created_at=collection.get("created_at"),
        updated_at=collection.get("updated_at"),
    )


@router.get("")
async def list_collections(
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await supabase.table("collections").select("*").eq("organization_id", ctx.organization["id"]).order("created_at", desc=True).execute()

    items = []
    for c in (result.data or []):
        doc_count = await supabase.table("documents").select("id", count="exact").eq("collection_id", c["id"]).execute()
        items.append(CollectionResponse(
            id=c["id"],
            organization_id=c["organization_id"],
            name=c["name"],
            description=c.get("description", ""),
            is_public=c.get("is_public", False),
            document_count=doc_count.count if hasattr(doc_count, "count") else 0,
            created_at=c.get("created_at"),
            updated_at=c.get("updated_at"),
        ))

    return items


@router.get("/{collection_id}")
async def get_collection(
    collection_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await supabase.table("collections").select("*").eq("id", collection_id).eq("organization_id", ctx.organization["id"]).single().execute()
    collection = result.data
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    doc_count = await supabase.table("documents").select("id", count="exact").eq("collection_id", collection_id).execute()
    return CollectionResponse(
        id=collection["id"],
        organization_id=collection["organization_id"],
        name=collection["name"],
        description=collection.get("description", ""),
        is_public=collection.get("is_public", False),
        document_count=doc_count.count if hasattr(doc_count, "count") else 0,
        created_at=collection.get("created_at"),
        updated_at=collection.get("updated_at"),
    )


@router.patch("/{collection_id}")
async def update_collection(
    collection_id: str,
    req: CollectionUpdate,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await supabase.table("collections").update(update_data).eq("id", collection_id).eq("organization_id", ctx.organization["id"]).select("*").execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    await log_action(
        supabase, ctx.member["user_id"], "collection:update",
        resource_type="collection", resource_id=collection_id,
        details=update_data,
        organization_id=ctx.organization["id"],
    )

    c = result.data[0]
    return CollectionResponse(
        id=c["id"],
        organization_id=c["organization_id"],
        name=c["name"],
        description=c.get("description", ""),
        is_public=c.get("is_public", False),
        created_at=c.get("created_at"),
        updated_at=c.get("updated_at"),
    )


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    await supabase.table("documents").update({"collection_id": None}).eq("collection_id", collection_id).eq("organization_id", ctx.organization["id"]).execute()
    await supabase.table("collections").delete().eq("id", collection_id).eq("organization_id", ctx.organization["id"]).execute()

    await log_action(
        supabase, ctx.member["user_id"], "collection:delete",
        resource_type="collection", resource_id=collection_id,
        organization_id=ctx.organization["id"],
    )
    return {"detail": "Collection deleted"}
