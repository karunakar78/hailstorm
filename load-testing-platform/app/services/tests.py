import ipaddress
import re
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.configuration import TestConfiguration
from app.models.target import RegisteredTarget
from app.models.test import Test
from app.schemas.test import TestConfigurationCreate, TestConfigurationUpdate, TestCreate, TestUpdate
from app.services.targets import is_prohibited_destination

HOSTNAME_REGEX = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$")


def normalize_hostname(raw: str) -> str:
    value = raw.strip().lower()
    if "://" in value:
        value = value.split("://", 1)[1]
    value = value.split("/", 1)[0]
    if ":" in value and not value.startswith("["):
        value = value.split(":", 1)[0]
    return value.strip()


def is_valid_hostname(hostname: str) -> bool:
    if not hostname or len(hostname) > 253:
        return False
    return HOSTNAME_REGEX.match(hostname) is not None


def is_prohibited_destination(hostname: str) -> bool:
    value = hostname.strip().lower()
    if value == "localhost" or value.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


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


async def register_target(session: AsyncSession, owner_id: UUID, target_data: TestConfigurationCreate) -> RegisteredTarget:
    hostname = normalize_hostname(target_data.hostname)
    if not is_valid_hostname(hostname):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hostname")
    if is_prohibited_destination(hostname):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prohibited destination")

    target = RegisteredTarget(owner_id=owner_id, hostname=hostname, verification_status="pending")
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return target


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


async def create_test(session: AsyncSession, user_id: UUID, test_data: TestCreate) -> tuple[Test, TestConfiguration]:
    target = await _get_authorized_target(session, user_id, test_data.configuration.target_id, test_data.configuration.target_url)

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

    await session.commit()
    await session.refresh(test)
    await session.refresh(config)
    return test, config


async def update_test_metadata(session: AsyncSession, user_id: UUID, test_id: UUID, update: TestUpdate) -> Test:
    test = await get_test(session, user_id, test_id)
    if test.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot update archived test")

    if "name" in update.model_fields_set:
        test.name = update.name
    if "description" in update.model_fields_set:
        test.description = update.description
    test.updated_at = func.now()

    await session.commit()
    await session.refresh(test)
    return test


async def update_configuration(session: AsyncSession, user_id: UUID, test_id: UUID, config_update: TestConfigurationUpdate) -> Test:
    test = await get_test(session, user_id, test_id)
    if test.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot update archived test")

    target = await _get_authorized_target(session, user_id, config_update.target_id, config_update.target_url)

    config = test.configuration
    config.target_id = config_update.target_id
    config.target_url = config_update.target_url
    config.request_rate = config_update.request_rate
    config.duration_seconds = config_update.duration_seconds
    config.updated_at = func.now()

    await session.commit()
    await session.refresh(config)
    return test
