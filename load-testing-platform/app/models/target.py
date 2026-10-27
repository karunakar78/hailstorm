import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class RegisteredTarget(Base):
    """A load-test target registered by a user."""

    __tablename__ = "registered_targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, nullable=False, server_default="pending")
    verification_method: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="targets")

    def __repr__(self) -> str:
        return f"RegisteredTarget(id={self.id}, owner_id={self.owner_id}, hostname={self.hostname}, status={self.verification_status})"
