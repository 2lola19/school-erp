from typing import AsyncGenerator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from jose import jwt, JWTError
import redis.asyncio as redis
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.auth import TokenPayload

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

async def get_current_user_payload(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
) -> TokenPayload:
    is_blacklisted = await redis_client.get(f"bl_{token}")
    if is_blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_rls_db(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
) -> AsyncSession:
    await session.execute(text(f"SET LOCAL app.current_tenant = '{payload.tenant_id}'"))
    return session
