from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class TargetConfig(BaseModel):
    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("method")
    @classmethod
    def method_upper(cls, v: str) -> str:
        return v.upper()


class LoadConfig(BaseModel):
    duration: float = Field(gt=0, description="Test duration in seconds")
    rate: float = Field(gt=0, description="Target requests per second")
    concurrency: int = Field(ge=1, description="Max in-flight requests")


class RequestConfig(BaseModel):
    timeout: float = Field(default=5.0, gt=0, description="Per-request timeout in seconds")


class EngineConfig(BaseModel):
    target: TargetConfig
    load: LoadConfig
    request: RequestConfig = Field(default_factory=RequestConfig)


def load_config(path: str | Path) -> EngineConfig:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping")
    return EngineConfig.model_validate(data)
