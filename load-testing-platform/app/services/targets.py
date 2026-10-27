import ipaddress
import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target import RegisteredTarget
from app.schemas.target import TargetCreate

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


async def register_target(session: AsyncSession, owner_id: UUID, target_data: TargetCreate) -> RegisteredTarget:
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


async def list_targets(session: AsyncSession, owner_id: UUID) -> list[RegisteredTarget]:
    result = await session.execute(select(RegisteredTarget).where(RegisteredTarget.owner_id == owner_id))
    return list(result.scalars().all())


async def get_target(session: AsyncSession, owner_id: UUID, target_id: UUID) -> RegisteredTarget:
    result = await session.execute(select(RegisteredTarget).where(RegisteredTarget.id == target_id, RegisteredTarget.owner_id == owner_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return target


async def initiate_verification(session: AsyncSession, owner_id: UUID, target_id: UUID) -> RegisteredTarget:
    return await get_target(session, owner_id, target_id)
