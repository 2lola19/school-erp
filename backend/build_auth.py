import os

schemas_auth = """
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List

class LoginCredentials(BaseModel):
    domain: str
    email: EmailStr
    password: str
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role_id: str
    permissions: List[str] = []
"""

services_auth = """
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

async def generate_tokens(user: User, permissions: list[str]) -> TokenResponse:
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=7)

    access_token = create_access_token(
        subject=str(user.id), tenant_id=str(user.tenant_id), role_id=str(user.role_id),
        expires_delta=access_expires
    )
    refresh_token = create_access_token(
        subject=str(user.id), tenant_id=str(user.tenant_id), role_id=str(user.role_id),
        expires_delta=refresh_expires
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

async def blacklist_token(redis_client: redis.Redis, token: str) -> None:
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis_client.setex(f"bl_{token}", ttl, "revoked")
"""

dependencies = """
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
"""

endpoints_auth = """
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from app.api.v1.dependencies import get_db, get_redis, oauth2_scheme
from app.schemas.auth import LoginCredentials, TokenResponse
from app.services import auth_service

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(creds: LoginCredentials, session: Annotated[AsyncSession, Depends(get_db)]):
    user, permissions = await auth_service.authenticate_user(session, creds)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect domain, email, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await auth_service.generate_tokens(user, permissions)

@router.post("/logout")
async def logout(token: Annotated[str, Depends(oauth2_scheme)], redis_client: Annotated[redis.Redis, Depends(get_redis)]):
    await auth_service.blacklist_token(redis_client, token)
    return {"status": "logged_out"}
"""

api_v1_init = """
from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
"""

main_py = """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}
"""

docker_compose_yml = """
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

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
"""

files = {
    "app/schemas/auth.py": schemas_auth,
    "app/services/auth_service.py": services_auth,
    "app/api/v1/dependencies.py": dependencies,
    "app/api/v1/endpoints/auth.py": endpoints_auth,
    "app/api/v1/__init__.py": api_v1_init,
    "app/main.py": main_py,
    "docker-compose.yml": docker_compose_yml
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

print("[+] API Transport Layer and Auth endpoints populated.")