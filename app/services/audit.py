import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    actor_id: uuid.UUID | str | None = None,
    action: str = "",
    resource_type: str | None = None,
    resource_id: uuid.UUID | str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    organization_id: uuid.UUID | str | None = None,
) -> None:
    log = AuditLog(
        actor_id=_to_uuid(actor_id) if actor_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=_to_uuid(resource_id) if resource_id else None,
        details=details,
        ip_address=ip_address,
        organization_id=_to_uuid(organization_id) if organization_id else None,
    )
    db.add(log)


def _to_uuid(value: uuid.UUID | str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)
