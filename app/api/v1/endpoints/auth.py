from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RoleBrief,
    TokenResponse,
    UserResponse,
)
from app.services import auth as auth_service
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register_user(db, req)
        await log_action(db, str(user.id), "auth:register", "user", str(user.id))
        tokens = await auth_service.login(db, req.full_name, req.password)
        if tokens:
            return {"id": str(user.id), "email": user.email, **tokens}
        return {"id": str(user.id), "email": user.email, "full_name": req.full_name}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db), request: Request = None):
    username = req.username or req.email
    result = await auth_service.login(db, username, req.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    await log_action(db, None, "auth:login", ip_address=request.client.host if request else None)
    return TokenResponse(**result)


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.refresh_access_token(db, req.refresh_token)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(**result)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=[RoleBrief(id=str(r.id), name=r.name, permissions=[p.codename for p in r.permissions]) for r in user.roles],
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
