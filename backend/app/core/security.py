from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _create_token(
    *,
    subject: UUID | str,
    tenant_id: UUID | str,
    permission_version: int,
    token_type: str,
    expires_delta: timedelta,
    session_id: UUID | str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "session_id": str(session_id or uuid4()),
        "permission_version": permission_version,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    *, subject: UUID | str, tenant_id: UUID | str, permission_version: int, session_id: UUID | str
) -> str:
    return _create_token(
        subject=subject,
        tenant_id=tenant_id,
        permission_version=permission_version,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        session_id=session_id,
    )


def create_refresh_token(
    *, subject: UUID | str, tenant_id: UUID | str, permission_version: int, session_id: UUID | str
) -> str:
    return _create_token(
        subject=subject,
        tenant_id=tenant_id,
        permission_version=permission_version,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        session_id=session_id,
    )
