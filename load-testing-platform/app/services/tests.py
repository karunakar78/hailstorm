from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.configuration import TestConfiguration
from app.models.target import RegisteredTarget
from app.models.test import Test
from app.schemas.test import TestCreate
from app.services.targets import is_prohibited_destination


async def _get_authorized_target(
    session: AsyncSession,
    user_id: UUID,
    target_id: UUID,
    target_url: str,
) -> RegisteredTarget:
    result = await session.execute(
        select(RegisteredTarget).where(RegisteredTarget.id == target_id, RegisteredTarget.owner_id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if target.verification_status != "verified":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Target not verified")

    requested_hostname = (urlparse(str(target_url)).hostname or "").lower()
    if requested_hostname != (target.hostname or "").lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Target URL outside authorized scope")

    if requested_hostname and is_prohibited_destination(requested_hostname):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prohibited destination")

    return target


async def create_test(session: AsyncSession, user_id: UUID, test_data: TestCreate) -> tuple[Test, TestConfiguration]:
    # 3. Authorize target
    target = await _get_authorized_target(session, user_id, test_data.configuration.target_id, test_data.configuration.target_url)

    # 4. Create records
    test = Test(owner_id=user_id, name=test_data.name, description=test_data.description, status="active")
    session.add(test)
    await session.flush()

    config = TestConfiguration(
        test_id=test.id,
        target_id=test_data.configuration.target_id,
        target_url=test_data.configuration.target_url,
        request_rate=test_data.configuration.request_rate,
        duration_seconds=test_data.configuration.duration_seconds,
    )
    session.add(config)

    # 5. Commit both records in a single transaction
    await session.commit()
    await session.refresh(test)
    await session.refresh(config)
    return test, config


async def list_tests(
    session: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    status: str | None = None,
) -> list[Test]:
    query = select(Test).options(selectinload(Test.configuration)).where(Test.owner_id == user_id)
    if status is not None:
        query = query.where(Test.status == status)
    if search is not None and search.strip():
        query = query.where(Test.name.ilike(f"%{search.strip()}%", escape="\\"))
    query = query.order_by(Test.created_at.desc(), Test.id.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_test(session: AsyncSession, user_id: UUID, test_id: UUID) -> Test:
    result = await session.execute(
        select(Test).options(selectinload(Test.configuration)).where(Test.id == test_id, Test.owner_id == user_id)
    )
    test = result.scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return test
