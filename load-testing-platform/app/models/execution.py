import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.test import Test


class Execution(Base):
    """Individual attempt to execute a load test."""

    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    test_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tests.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    test: Mapped[Test] = relationship(back_populates="executions")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'stopping', 'completed', 'failed', 'cancelled')",
            name="ck_executions_status_valid",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"Execution(id={self.id}, test_id={self.test_id}, status={self.status}, "
            f"requested_at={self.requested_at}, started_at={self.started_at}, finished_at={self.finished_at}, "
            f"error_message={self.error_message})"
        )
