from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.test import TestCreate, TestConfigurationRead, TestRead
from app.services import auth as auth_service
from app.services import tests as tests_service


router = APIRouter(prefix="/tests", tags=["Tests"])


@router.post("", response_model=TestRead, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_data: TestCreate,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test, config = await tests_service.create_test(session, user.id, test_data)

    return TestRead(
        id=test.id,
        owner_id=test.owner_id,
        name=test.name,
        description=test.description,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        configuration=TestConfigurationRead(
            id=config.id,
            test_id=config.test_id,
            target_id=config.target_id,
            target_url=config.target_url,
            request_rate=config.request_rate,
            duration_seconds=config.duration_seconds,
            updated_at=config.updated_at,
        ),
    )
