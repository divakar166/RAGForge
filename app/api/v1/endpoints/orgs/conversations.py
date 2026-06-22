import logging

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.core.deps import OrganizationContext, get_org_context
from app.db.supabase import get_supabase
from app.schemas.conversation import ConversationCreate, ConversationListItem, ConversationResponse, ConversationUpdate
from app.schemas.search import ConversationDetailResponse, ConversationMessage
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["orgs-conversations"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConversationResponse)
async def create_conversation(
    req: ConversationCreate,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await (
        supabase.table("conversation_threads")
        .insert({
            "organization_id": ctx.organization["id"],
            "user_id": ctx.member["user_id"],
            "title": req.title,
        })
        .select("*")
        .execute()
    )
    thread = result.data[0]
    return ConversationResponse(
        id=thread["id"],
        organization_id=thread["organization_id"],
        user_id=thread["user_id"],
        title=thread["title"],
        created_at=thread.get("created_at"),
        updated_at=thread.get("updated_at"),
    )


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    result = await (
        supabase.table("conversation_threads")
        .select("*")
        .eq("organization_id", ctx.organization["id"])
        .eq("user_id", ctx.member["user_id"])
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
    )
    items = []
    for t in (result.data or []):
        msg_count = await (
            supabase.table("conversations")
            .select("id", count="exact")
            .eq("thread_id", t["id"])
            .execute()
        )
        items.append(ConversationListItem(
            id=t["id"],
            title=t["title"],
            message_count=msg_count.count if hasattr(msg_count, "count") else 0,
            created_at=t.get("created_at"),
        ))
    return items


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    thread_resp = await (
        supabase.table("conversation_threads")
        .select("*")
        .eq("id", conversation_id)
        .eq("organization_id", ctx.organization["id"])
        .eq("user_id", ctx.member["user_id"])
        .single()
        .execute()
    )
    thread = thread_resp.data
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages_resp = await (
        supabase.table("conversations")
        .select("*")
        .eq("thread_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return ConversationDetailResponse(
        id=thread["id"],
        title=thread["title"],
        messages=[
            ConversationMessage(
                id=m["id"],
                query=m["query"],
                answer=m["answer"],
                citations=m.get("citations"),
                feedback_score=m.get("feedback_score"),
                created_at=m.get("created_at"),
            )
            for m in (messages_resp.data or [])
        ],
    )


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await (
        supabase.table("conversation_threads")
        .update(update_data)
        .eq("id", conversation_id)
        .eq("organization_id", ctx.organization["id"])
        .eq("user_id", ctx.member["user_id"])
        .select("*")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"detail": "Conversation updated"}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    ctx: OrganizationContext = Depends(get_org_context),
    supabase: AsyncClient = Depends(get_supabase),
):
    await supabase.table("conversations").delete().eq("thread_id", conversation_id).execute()
    await supabase.table("conversation_threads").delete().eq("id", conversation_id).eq("organization_id", ctx.organization["id"]).execute()
    return {"detail": "Conversation deleted"}
