from collections.abc import AsyncGenerator, Callable
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.feature_registry import FeatureCode
from app.db.session import AsyncSessionLocal
from app.models.core import User
from app.schemas.auth import CurrentUser, TokenPayload
from app.services.access_control import get_effective_permissions
from app.services.entitlements import EntitlementService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def decode_token(token: str, *, expected_type: str = "access") -> TokenPayload:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = TokenPayload(
            **jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        )
    except (JWTError, ValueError):
        raise credentials_error
    if payload.type != expected_type:
        raise credentials_error
    return payload


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> CurrentUser:
    payload = decode_token(token)
    if await redis_client.get(f"revoked_session:{payload.session_id}"):
        raise HTTPException(status_code=401, detail="Session revoked")

    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(payload.tenant_id)},
    )
    result = await session.execute(
        select(User).where(
            User.id == payload.sub,
            User.tenant_id == payload.tenant_id,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user or user.permission_version != payload.permission_version:
        raise HTTPException(status_code=401, detail="Session permissions are stale")

    permissions = await get_effective_permissions(session, redis_client, user)
    return CurrentUser(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        permission_version=user.permission_version,
        permissions=permissions,
    )


async def get_current_user_payload(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Compatibility alias for older endpoints while they migrate to CurrentUser."""
    return current_user


async def get_rls_db(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncSession:
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(current_user.tenant_id)},
    )
    return session


def require_permissions(*required: str) -> Callable:
    async def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        missing = set(required) - current_user.permissions
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(sorted(missing))}",
            )
        return current_user

    return dependency


def require_access(
    feature_code: FeatureCode,
    *required_permissions: str,
    write: bool = True,
) -> Callable:
    """Require both user RBAC permission and tenant subscription entitlement."""

    async def dependency(
        actor: Annotated[CurrentUser, Depends(require_permissions(*required_permissions))],
        session: Annotated[AsyncSession, Depends(get_rls_db)],
        redis_client: Annotated[redis.Redis, Depends(get_redis)],
    ) -> CurrentUser:
        await EntitlementService(session, redis_client).require_feature(
            actor.tenant_id,
            feature_code,
            write=write,
        )
        return actor

    return dependency
