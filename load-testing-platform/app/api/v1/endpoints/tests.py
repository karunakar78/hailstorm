from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
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


@router.get("", response_model=list[TestRead])
async def list_tests(
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of records to return"),
    search: str | None = Query(default=None, max_length=255, description="Case-insensitive name search"),
    status: str | None = Query(default=None, pattern="^(active|archived)$", description="Filter by status"),
) -> list[TestRead]:
    tests = await tests_service.list_tests(session, user.id, skip=skip, limit=limit, search=search, status=status)
    return [
        TestRead(
            id=t.id,
            owner_id=t.owner_id,
            name=t.name,
            description=t.description,
            status=t.status,
            created_at=t.created_at,
            updated_at=t.updated_at,
            configuration=TestConfigurationRead(
                id=t.configuration.id,
                test_id=t.configuration.test_id,
                target_id=t.configuration.target_id,
                target_url=t.configuration.target_url,
                request_rate=t.configuration.request_rate,
                duration_seconds=t.configuration.duration_seconds,
                updated_at=t.configuration.updated_at,
            )
            if t.configuration is not None
            else None,
        )
        for t in tests
    ]


@router.get("/{test_id}", response_model=TestRead)
async def get_test(
    test_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.get_test(session, user.id, test_id)

    return TestRead(
        id=test.id,
        owner_id=test.owner_id,
        name=test.name,
        description=test.description,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        configuration=TestConfigurationRead(
            id=test.configuration.id,
            test_id=test.configuration.test_id,
            target_id=test.configuration.target_id,
            target_url=test.configuration.target_url,
            request_rate=test.configuration.request_rate,
            duration_seconds=test.configuration.duration_seconds,
            updated_at=test.configuration.updated_at,
        )
        if test.configuration is not None
        else None,
    )
