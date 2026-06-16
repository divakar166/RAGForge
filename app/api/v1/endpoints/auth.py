from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    OrgSelectRequest,
    RefreshRequest,
    RegisterInviteRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth as auth_service
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, org = await auth_service.register_user(db, req)
        await log_action(
            db, user.id, "auth:register",
            resource_type="user", organization_id=org.id,
        )
        await log_action(
            db, user.id, "org:create",
            resource_type="organization", resource_id=org.id, organization_id=org.id,
        )
        tokens = await auth_service.login_with_org(db, str(user.id), str(org.id))
        if not tokens:
            raise HTTPException(status_code=500, detail="Login after registration failed")
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "org_id": str(org.id),
            "org_name": org.name,
            **tokens,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/register-with-invite", status_code=status.HTTP_201_CREATED)
async def register_with_invite(
    req: RegisterInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, org, member = await auth_service.register_with_invitation(
            db, req.invitation_token, req.username, req.password, req.email
        )
        tokens = await auth_service.login_with_org(db, str(user.id), str(org.id))
        if not tokens:
            raise HTTPException(status_code=500, detail="Login after registration failed")
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "org_id": str(org.id),
            **tokens,
        }
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


@router.post("/select-org")
async def select_org(
    req: OrgSelectRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await auth_service.login_with_org(db, str(user.id), req.org_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    await log_action(db, user.id, "auth:select_org", resource_type="organization", resource_id=req.org_id)
    return TokenResponse(**result)


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    orgs = await auth_service.get_user_orgs(db, user.id)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        organizations=orgs,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
