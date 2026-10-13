from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class KeyStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class ManagedKey(Base):
    __tablename__ = "managed_keys"

    __table_args__ = (
        UniqueConstraint(
            "token_label",
            "key_id",
            name="uq_managed_key_token_id",
        ),
        CheckConstraint(
            "status IN ('created', 'active', 'suspended', 'revoked')",
            name="ck_managed_key_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    token_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    key_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    key_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    algorithm: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=KeyStatus.CREATED.value,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
