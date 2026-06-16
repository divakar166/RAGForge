from fastapi import APIRouter

from app.api.v1.endpoints import auth, evaluate, invites, roles, users
from app.api.v1.endpoints.orgs import (
    audit,
    collections,
    conversations,
    documents,
    invites as org_invites,
    members,
    search,
)
from app.api.v1.endpoints.orgs import (
    evaluate as org_evaluate,
)

router = APIRouter(prefix="/api/v1")

# Auth & admin (no org scope)
router.include_router(auth.router)
router.include_router(invites.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(evaluate.router)

# Org-scoped endpoints
orgs_router = APIRouter(prefix="/orgs/{org_id}")
orgs_router.include_router(collections.router)
orgs_router.include_router(conversations.router)
orgs_router.include_router(documents.router)
orgs_router.include_router(search.router)
orgs_router.include_router(members.router)
orgs_router.include_router(org_invites.router)
orgs_router.include_router(audit.router)
orgs_router.include_router(org_evaluate.router)
router.include_router(orgs_router)
