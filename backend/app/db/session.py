from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine_options: dict[str, Any] = {
    "pool_pre_ping": True,
    "echo": False,
}
if settings.DB_USE_NULL_POOL:
    engine_options["poolclass"] = NullPool
else:
    engine_options.update({"pool_size": 20, "max_overflow": 10})

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, **engine_options)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
