"""Deprecated — search endpoints are now at /api/v1/orgs/{org_id}/search.

See app/api/v1/endpoints/orgs/search.py instead.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_info():
    return {"message": "Deprecated. Use /api/v1/orgs/{org_id}/search instead."}
