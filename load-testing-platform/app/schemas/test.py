import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class TestConfigurationCreate(BaseModel):
    target_id: uuid.UUID
    target_url: str = Field(min_length=1, max_length=2048)
    request_rate: float = Field(gt=0, le=settings.MAX_REQUEST_RATE)
    duration_seconds: int = Field(gt=0, le=settings.MAX_DURATION_SECONDS)


class TestConfigurationRead(BaseModel):
    id: uuid.UUID
    test_id: uuid.UUID
    target_id: uuid.UUID
    target_url: str
    request_rate: float
    duration_seconds: int
    updated_at: datetime


class TestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    configuration: TestConfigurationCreate

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Name must be a non-empty string")
        return stripped


class TestRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    configuration: TestConfigurationRead | None = None
