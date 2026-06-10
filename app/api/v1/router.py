from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, evaluate, roles, search, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(documents.router)
router.include_router(search.router)
router.include_router(evaluate.router)
