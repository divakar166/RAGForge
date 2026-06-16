from fastapi import APIRouter, Depends
from supabase import AsyncClient

from app.core.deps import OrganizationContext, require_org_role
from app.db.supabase import get_supabase

router = APIRouter(prefix="/audit", tags=["orgs-audit"])


@router.get("")
async def get_audit_logs(
    page: int = 1,
    per_page: int = 50,
    ctx: OrganizationContext = Depends(require_org_role("owner", "admin")),
    supabase: AsyncClient = Depends(get_supabase),
):
    org_id = ctx.organization["id"]
    offset = (page - 1) * per_page
    result = await (
        supabase.table("audit_logs")
        .select("*")
        .eq("organization_id", org_id)
        .order("timestamp", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return result.data or []
