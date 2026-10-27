from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services import auth as auth_service


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model= UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_db)) -> UserRead:
    user = await auth_service.register_user(session, user_data)
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, session: AsyncSession = Depends(get_db)) -> Token:
    user = await auth_service.authenticate_user(session, credentials.email, credentials.password)
    access_token = create_access_token(str(user.id))
    return Token(access_token=access_token, token_type="bearer")
