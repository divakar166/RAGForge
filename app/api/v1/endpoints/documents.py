"""Deprecated — documents endpoints are now at /api/v1/orgs/{org_id}/documents.

See app/api/v1/endpoints/orgs/documents.py instead.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents():
    return {"message": "Deprecated. Use /api/v1/orgs/{org_id}/documents instead."}
