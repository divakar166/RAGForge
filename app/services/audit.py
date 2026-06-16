import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import AsyncClient

logger = logging.getLogger(__name__)


async def log_action(
    supabase: AsyncClient,
    actor_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    organization_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    try:
        await supabase.table("audit_logs").insert({
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "organization_id": organization_id,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        logger.exception("Failed to log audit action: %s", action)
