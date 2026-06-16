import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.invitation import Invitation
from app.db.models.organization import Organization, OrganizationMember

logger = logging.getLogger(__name__)


async def create_organization(
    db: AsyncSession,
    name: str,
    slug: str,
    owner_id: uuid.UUID,
) -> Organization:
    org = Organization(name=name, slug=slug, owner_id=owner_id)
    db.add(org)
    await db.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=owner_id,
        role="owner",
    )
    db.add(member)
    await db.flush()

    return org


async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> Organization | None:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    return result.scalar_one_or_none()


async def update_organization(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str | None = None,
    is_active: bool | None = None,
) -> Organization | None:
    org = await get_organization(db, org_id)
    if not org:
        return None

    if name is not None:
        org.name = name
    if is_active is not None:
        org.is_active = is_active

    await db.flush()
    return org


async def delete_organization(db: AsyncSession, org_id: uuid.UUID) -> bool:
    org = await get_organization(db, org_id)
    if not org:
        return False
    await db.delete(org)
    await db.flush()
    return True


async def get_members(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active,
        )
    )
    members = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "email": m.user.email,
            "username": m.user.username,
            "role": m.role,
            "is_active": m.is_active,
            "created_at": m.created_at,
        }
        for m in members
    ]


async def update_member_role(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str | None = None,
    is_active: bool | None = None,
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return None

    if role is not None:
        member.role = role
    if is_active is not None:
        member.is_active = is_active

    await db.flush()
    return member


async def remove_member(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member or member.role == "owner":
        return False
    await db.delete(member)
    await db.flush()
    return True


async def invite_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    email: str,
    role: str,
    invited_by_id: uuid.UUID,
) -> Invitation:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invitation = Invitation(
        organization_id=org_id,
        email=email,
        token=token,
        role=role,
        invited_by_id=invited_by_id,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.flush()

    return invitation


async def get_org_stats(db: AsyncSession, org_id: uuid.UUID) -> dict:
    member_count = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active,
        )
    )
    from app.db.models.document import Document

    doc_count = await db.execute(
        select(func.count(Document.id)).where(Document.organization_id == org_id)
    )
    return {
        "member_count": member_count.scalar() or 0,
        "document_count": doc_count.scalar() or 0,
    }
