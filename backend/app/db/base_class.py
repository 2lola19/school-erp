import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    id: Any
    __name__: str

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

class TenantBase(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None).replace(tzinfo=None)
    )