import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.target import RegisteredTarget
from app.models.test import Test


class TestConfiguration(Base):
    """One current configuration for a load test."""

    __tablename__ = "test_configurations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    test_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, unique=True)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("registered_targets.id"), nullable=False)
    target_url: Mapped[str] = mapped_column(String, nullable=False)
    request_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    test: Mapped[Test] = relationship(back_populates="configuration")
    target: Mapped[RegisteredTarget] = relationship(back_populates="configurations")

    __table_args__ = (
        CheckConstraint("request_rate > 0", name="ck_test_configurations_request_rate_positive"),
        CheckConstraint("duration_seconds > 0", name="ck_test_configurations_duration_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"TestConfiguration(id={self.id}, test_id={self.test_id}, target_id={self.target_id}, "
            f"target_url={self.target_url}, request_rate={self.request_rate}, duration_seconds={self.duration_seconds})"
        )
