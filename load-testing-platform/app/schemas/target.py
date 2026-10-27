import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TargetCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)


class TargetRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    hostname: str
    verification_status: str
    verification_method: str | None
    created_at: datetime
    verified_at: datetime | None
