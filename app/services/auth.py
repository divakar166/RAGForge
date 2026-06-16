import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.invitation import Invitation
from app.db.models.organization import Organization, OrganizationMember
from app.db.models.user import User
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, req: RegisterRequest) -> tuple[User, Organization]:
    existing = await db.execute(
        select(User).where((User.email == req.email) | (User.username == req.username))
    )
    if existing.scalar_one_or_none():
        raise ValueError("Email or username already taken")

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    await db.flush()

    org = Organization(
        name=req.org_name,
        slug=req.org_slug,
        owner_id=user.id,
    )
    db.add(org)
    await db.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member)
    await db.flush()

    return user, org


async def register_with_invitation(
    db: AsyncSession,
    token: str,
    username: str,
    password: str,
    email: str,
) -> tuple[User, Organization, OrganizationMember]:
    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.organization))
        .where(Invitation.token == token, Invitation.accepted_at.is_(None))
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise ValueError("Invalid or expired invitation token")

    if invitation.expires_at < datetime.now(timezone.utc):
        raise ValueError("Invitation has expired")

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()

    member = OrganizationMember(
        organization_id=invitation.organization_id,
        user_id=user.id,
        role=invitation.role,
    )
    db.add(member)
    await db.flush()

    invitation.accepted_at = datetime.now(timezone.utc)
    await db.flush()

    return user, invitation.organization, member


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.memberships))
        .where((User.username == username) | (User.email == username))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def login(db: AsyncSession, username: str, password: str) -> dict | None:
    user = await authenticate_user(db, username, password)
    if not user:
        return None

    extra_claims = {}
    if user.memberships:
        primary = user.memberships[0]
        extra_claims["org_id"] = str(primary.organization_id)
        extra_claims["org_role"] = primary.role

    return {
        "access_token": create_access_token(str(user.id), extra_claims=extra_claims),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def login_with_org(db: AsyncSession, user_id: str, org_id: str) -> dict | None:
    try:
        user_uuid = uuid.UUID(user_id)
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        return None

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_uuid,
            OrganizationMember.user_id == user_uuid,
            OrganizationMember.is_active,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return None

    return {
        "access_token": create_access_token(
            user_id,
            extra_claims={
                "org_id": str(member.organization_id),
                "org_role": member.role,
                "org_name": member.organization.name,
            },
        ),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict | None:
    try:
        payload = decode_token(refresh_token)
    except InvalidTokenError:
        return None

    user_id = payload.get("sub")
    token_type = payload.get("type")

    if not user_id or token_type != "refresh":
        return None

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None

    result = await db.execute(
        select(User)
        .options(selectinload(User.memberships))
        .where(User.id == user_uuid, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        return None

    extra_claims = {}
    if user.memberships:
        primary = user.memberships[0]
        extra_claims["org_id"] = str(primary.organization_id)
        extra_claims["org_role"] = primary.role

    return {
        "access_token": create_access_token(str(user.id), extra_claims=extra_claims),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def get_user_orgs(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == user_id, OrganizationMember.is_active)
    )
    members = result.scalars().all()
    return [
        {
            "id": str(m.organization.id),
            "name": m.organization.name,
            "slug": m.organization.slug,
            "role": m.role,
        }
        for m in members
    ]
