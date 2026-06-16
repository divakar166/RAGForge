from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient

from app.core.deps import get_current_admin
from app.db.supabase import get_supabase
from app.schemas.user import UserResponse, UserUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_response(u: dict) -> UserResponse:
    return UserResponse(
        id=u["id"],
        email=u["email"],
        username=u["username"],
        is_active=u["is_active"],
        is_superuser=u["is_superuser"],
        created_at=u.get("created_at"),
        updated_at=u.get("updated_at"),
    )


@router.get("")
async def list_users(
    supabase: AsyncClient = Depends(get_supabase),
    admin: dict = Depends(get_current_admin),
):
    result = await supabase.table("users").select("*").order("username").execute()
    return [_to_user_response(u) for u in (result.data or [])]


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    supabase: AsyncClient = Depends(get_supabase),
    admin: dict = Depends(get_current_admin),
):
    user_resp = await supabase.table("users").select("*").eq("id", user_id).single().execute()
    user = user_resp.data
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_user_response(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdate,
    supabase: AsyncClient = Depends(get_supabase),
    admin: dict = Depends(get_current_admin),
):
    user_resp = await supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not user_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = {}
    if req.is_active is not None:
        update_data["is_active"] = req.is_active
    if req.is_superuser is not None:
        update_data["is_superuser"] = req.is_superuser

    if update_data:
        await supabase.table("users").update(update_data).eq("id", user_id).execute()

    await log_action(supabase, admin["id"], "user:update", resource_type="user", resource_id=user_id)
    return {"detail": "User updated"}
