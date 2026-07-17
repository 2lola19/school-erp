import os

config_py = """
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REDIS_URL: str

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
"""

base_class_py = """
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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
"""

core_py = """
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base, TenantBase

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

class SchoolProfile(TenantBase):
    __tablename__ = "school_profiles"
    school_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    principal_name: Mapped[Optional[str]] = mapped_column(String(255))
    motto: Mapped[Optional[str]] = mapped_column(String(255))
    brand_color: Mapped[Optional[str]] = mapped_column(String(50))

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

class Role(TenantBase):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint('tenant_id', 'name', name='uq_tenant_role_name'),)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

class RolePermission(TenantBase):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)

class User(TenantBase):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint('tenant_id', 'email', name='uq_tenant_user_email'),)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class UserPermission(TenantBase):
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint('user_id', 'permission_id', name='uq_user_permission'),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), index=True)
"""

alembic_env_py = """
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import settings
from app.db.base_class import Base
from app.models import core 

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.SQLALCHEMY_DATABASE_URI
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.SQLALCHEMY_DATABASE_URI
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

env_file = """
PROJECT_NAME="School Management System API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=school_erp
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/school_erp
SECRET_KEY=generate_a_secure_random_string_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REDIS_URL=redis://localhost:6379/0
"""

docker_compose = """
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env
    ports:
      - "5432:5432"

volumes:
  postgres_data:
"""

files = {
    "app/core/config.py": config_py,
    "app/db/base_class.py": base_class_py,
    "app/models/core.py": core_py,
    "alembic/env.py": alembic_env_py,
    ".env": env_file,
    "docker-compose.yml": docker_compose
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\\n")

print("Core files populated successfully.")
