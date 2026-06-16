from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import AsyncClient

from app.core.deps import get_current_user
from app.db.supabase import get_supabase
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
async def register(req: RegisterRequest, supabase: AsyncClient = Depends(get_supabase)):
    try:
        user, org = await auth_service.register_user(supabase, req)
        await log_action(
            supabase, user["id"], "auth:register",
            resource_type="user", organization_id=org["id"],
        )
        await log_action(
            supabase, user["id"], "org:create",
            resource_type="organization", resource_id=org["id"], organization_id=org["id"],
        )
        tokens = await auth_service.login_with_org(supabase, user["id"], org["id"])
        if not tokens:
            raise HTTPException(status_code=500, detail="Login after registration failed")
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "org_id": org["id"],
            "org_name": org["name"],
            **tokens,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/register-with-invite", status_code=status.HTTP_201_CREATED)
async def register_with_invite(
    req: RegisterInviteRequest,
    supabase: AsyncClient = Depends(get_supabase),
):
    try:
        user, org, member = await auth_service.register_with_invitation(
            supabase, req.invitation_token, req.username, req.password, req.email
        )
        tokens = await auth_service.login_with_org(supabase, user["id"], org["id"])
        if not tokens:
            raise HTTPException(status_code=500, detail="Login after registration failed")
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "org_id": org["id"],
            "org_name": org["name"],
            **tokens,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login")
async def login(req: LoginRequest, supabase: AsyncClient = Depends(get_supabase), request: Request = None):
    username = req.username or req.email
    result = await auth_service.login(supabase, username, req.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    await log_action(supabase, None, "auth:login", ip_address=request.client.host if request else None)
    return TokenResponse(**result)


@router.post("/refresh")
async def refresh(req: RefreshRequest, supabase: AsyncClient = Depends(get_supabase)):
    result = await auth_service.refresh_access_token(supabase, req.refresh_token)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return TokenResponse(**result)


@router.post("/select-org")
async def select_org(
    req: OrgSelectRequest,
    supabase: AsyncClient = Depends(get_supabase),
    user: dict = Depends(get_current_user),
):
    result = await auth_service.login_with_org(supabase, user["id"], req.org_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    await log_action(supabase, user["id"], "auth:select_org", resource_type="organization", resource_id=req.org_id)
    return TokenResponse(**result)


@router.get("/me")
async def me(user: dict = Depends(get_current_user), supabase: AsyncClient = Depends(get_supabase)):
    orgs = await auth_service.get_user_orgs(supabase, user["id"])
    return UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        is_active=user["is_active"],
        is_superuser=user["is_superuser"],
        organizations=orgs,
        created_at=user.get("created_at"),
        updated_at=user.get("updated_at"),
    )
