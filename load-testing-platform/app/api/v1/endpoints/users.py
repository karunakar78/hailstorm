from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserRead
from app.services import auth as auth_service


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model= UserRead)
async def get_me(user: User = Depends(auth_service.get_current_user)) -> UserRead:
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)
