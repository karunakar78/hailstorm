from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.configuration import TestConfiguration
from app.models.test import Test
from app.models.user import User
from app.schemas.test import TestCreate, TestConfigurationRead, TestConfigurationUpdate, TestRead, TestUpdate
from app.services import auth as auth_service
from app.services import tests as tests_service


router = APIRouter(prefix="/tests", tags=["Tests"])


def _to_test_read(test: Test, configuration: TestConfiguration | None = None) -> TestRead:
    cfg = configuration if configuration is not None else test.configuration
    return TestRead(
        id=test.id,
        owner_id=test.owner_id,
        name=test.name,
        description=test.description,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        configuration=TestConfigurationRead(
            id=cfg.id,
            test_id=cfg.test_id,
            target_id=cfg.target_id,
            target_url=cfg.target_url,
            request_rate=cfg.request_rate,
            duration_seconds=cfg.duration_seconds,
            updated_at=cfg.updated_at,
        )
        if cfg is not None
        else None,
    )


@router.post("", response_model=TestRead, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_data: TestCreate,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test, config = await tests_service.create_test(session, user.id, test_data)

    return _to_test_read(test, config)


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
    return [_to_test_read(t) for t in tests]


@router.get("/{test_id}", response_model=TestRead)
async def get_test(
    test_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.get_test(session, user.id, test_id)

    return _to_test_read(test)


@router.patch("/{test_id}", response_model=TestRead)
async def update_test(
    test_id: UUID,
    test_update: TestUpdate,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.update_test_metadata(session, user.id, test_id, test_update)

    return _to_test_read(test)


@router.put("/{test_id}/configuration", response_model=TestRead)
async def update_test_configuration(
    test_id: UUID,
    config_update: TestConfigurationUpdate,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.update_configuration(session, user.id, test_id, config_update)

    return _to_test_read(test)


@router.post("/{test_id}/archive", response_model=TestRead)
async def archive_test(
    test_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.archive_test(session, user.id, test_id)

    return _to_test_read(test)


@router.post("/{test_id}/restore", response_model=TestRead)
async def restore_test(
    test_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TestRead:
    test = await tests_service.restore_test(session, user.id, test_id)

    return _to_test_read(test)
