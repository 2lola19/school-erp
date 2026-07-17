from datetime import timedelta
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis
from app.core.security import verify_password, create_access_token
from app.models.core import Tenant, User, Role, RolePermission, Permission
from app.schemas.auth import LoginCredentials, TokenResponse
from app.core.config import settings

async def authenticate_user(session: AsyncSession, creds: LoginCredentials) -> Tuple[User, list[str]]:
    tenant_result = await session.execute(select(Tenant).where(Tenant.domain == creds.domain))
    tenant = tenant_result.scalars().first()
    if not tenant:
        return None, []

    user_result = await session.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == creds.email)
    )
    user = user_result.scalars().first()

    if not user or not verify_password(creds.password, user.password_hash) or not user.is_active:
        return None, []

    perm_result = await session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    )
    permissions = list(perm_result.scalars().all())

    return user, permissions

async def blacklist_token(redis_client: redis.Redis, token: str) -> None:
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis_client.setex(f"bl_{token}", ttl, "revoked")

async def generate_tokens(user, permissions: list):
    from datetime import timedelta
    from app.core.config import settings
    from app.core.security import create_access_token_v2, create_refresh_token
    from app.schemas.auth import TokenResponse
    # Ensure permissions map to strings safely
    if permissions and not isinstance(permissions[0], str):
        perms = [p.name for p in permissions]
    else:
        perms = permissions or []
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token_v2(subject=user.id, tenant_id=user.tenant_id, role=user.role_id, permissions=perms, expires_delta=access_expires)
    refresh_expires = timedelta(minutes=10080)
    refresh_token = create_refresh_token(subject=str(user.id), expires_delta=refresh_expires)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type='bearer')
