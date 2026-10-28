from fastapi import APIRouter

from app.api.v1.endpoints import auth, targets, tests, users

router = APIRouter(prefix="/api/v1", tags=["API v1"])

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(targets.router)
router.include_router(tests.router)
