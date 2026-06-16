import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/users", tags=["users"])


def _to_user_response(u: User) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        email=u.email,
        username=u.username,
        is_active=u.is_active,
        is_superuser=u.is_superuser,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).order_by(User.username))
    users = result.scalars().all()
    return [_to_user_response(u) for u in users]


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _to_user_response(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.is_active is not None:
        user.is_active = req.is_active
    if req.is_superuser is not None:
        user.is_superuser = req.is_superuser

    await log_action(db, admin.id, "user:update", "user", user_id)
    return {"detail": "User updated"}
