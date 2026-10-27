from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.target import TargetCreate, TargetRead
from app.services import auth as auth_service
from app.services import targets as targets_service


router = APIRouter(prefix="/targets", tags=["Targets"])


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
async def register_target(
    target_data: TargetCreate,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TargetRead:
    target = await targets_service.register_target(session, user.id, target_data)
    return TargetRead(
        id=target.id,
        owner_id=target.owner_id,
        hostname=target.hostname,
        verification_status=target.verification_status,
        verification_method=target.verification_method,
        created_at=target.created_at,
        verified_at=target.verified_at,
    )


@router.get("", response_model=list[TargetRead])
async def list_targets(
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TargetRead]:
    targets = await targets_service.list_targets(session, user.id)
    return [
        TargetRead(
            id=t.id,
            owner_id=t.owner_id,
            hostname=t.hostname,
            verification_status=t.verification_status,
            verification_method=t.verification_method,
            created_at=t.created_at,
            verified_at=t.verified_at,
        )
        for t in targets
    ]


@router.get("/{target_id}", response_model=TargetRead)
async def get_target(
    target_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TargetRead:
    target = await targets_service.get_target(session, user.id, target_id)
    return TargetRead(
        id=target.id,
        owner_id=target.owner_id,
        hostname=target.hostname,
        verification_status=target.verification_status,
        verification_method=target.verification_method,
        created_at=target.created_at,
        verified_at=target.verified_at,
    )


@router.post("/{target_id}/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_target(
    target_id: UUID,
    user: User = Depends(auth_service.get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await targets_service.initiate_verification(session, user.id, target_id)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"detail": "Verification queued"})
