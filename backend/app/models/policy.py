import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PolicyEffect(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    effect: Mapped[PolicyEffect] = mapped_column(
        Enum(PolicyEffect, name="policy_effect", native_enum=True), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target: Mapped[dict] = mapped_column(JSONB, nullable=False)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
