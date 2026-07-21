from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.core import Tenant, User
from app.schemas.auth import LoginCredentials, TokenResponse


async def authenticate_user(
    session: AsyncSession, credentials: LoginCredentials
) -> User | None:
    tenant = await session.scalar(
        select(Tenant).where(Tenant.domain == credentials.domain.lower().strip())
    )
    if not tenant:
        return None
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant.id)},
    )
    user = await session.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.email == credentials.email.lower(),
            User.is_active.is_(True),
        )
    )
    if not user or not verify_password(credentials.password, user.password_hash):
        return None
    return user


def issue_tokens(user: User) -> tuple[TokenResponse, str]:
    session_id = uuid4()
    access_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        permission_version=user.permission_version,
        session_id=session_id,
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        permission_version=user.permission_version,
        session_id=session_id,
    )
    return (
        TokenResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        refresh_token,
    )
