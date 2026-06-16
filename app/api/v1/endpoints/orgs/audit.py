from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import OrganizationContext, require_org_role
from app.db.models.audit_log import AuditLog
from app.db.session import get_db

router = APIRouter(prefix="/audit", tags=["orgs-audit"])


@router.get("")
async def get_audit_logs(
    page: int = 1,
    per_page: int = 50,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .where(AuditLog.organization_id == ctx.organization.id)
        .order_by(desc(AuditLog.timestamp))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]
