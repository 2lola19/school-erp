from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import decode_token, get_current_user, get_db, get_redis, get_rls_db
from app.core.config import settings
from app.models.core import Role, Staff, StaffRoleAssignment, User
from app.schemas.auth import CurrentUser, LoginCredentials, TokenResponse, UserContextResponse, Workspace
from app.services.auth_service import authenticate_user, issue_tokens

router = APIRouter()
REFRESH_COOKIE = "school_erp_refresh"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=f"{settings.API_V1_STR}/auth",
    )


@router.get("/me", response_model=UserContextResponse)
async def me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> UserContextResponse:
    result = await session.execute(
        select(StaffRoleAssignment, Role)
        .join(Staff, Staff.id == StaffRoleAssignment.staff_id)
        .join(Role, Role.id == StaffRoleAssignment.role_id)
        .where(
            Staff.user_id == current_user.id,
            Staff.tenant_id == current_user.tenant_id,
            StaffRoleAssignment.tenant_id == current_user.tenant_id,
            StaffRoleAssignment.status == "ACTIVE",
        )
        .order_by(StaffRoleAssignment.assignment_type, Role.name)
    )
    workspaces = [
        Workspace(
            assignment_id=assignment.id,
            role_id=role.id,
            name=role.name,
            code=role.code,
            category=role.role_category,
            assignment_type=assignment.assignment_type,
            scope=assignment.scope,
        )
        for assignment, role in result.all()
    ]
    return UserContextResponse(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        permission_version=current_user.permission_version,
        permissions=sorted(current_user.permissions),
        workspaces=workspaces,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginCredentials,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    user = await authenticate_user(session, credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid domain, email, or password",
        )
    tokens, refresh_token = issue_tokens(user)
    set_refresh_cookie(response, refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    payload = decode_token(refresh_token, expected_type="refresh")
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
    tokens, new_refresh_token = issue_tokens(user)
    set_refresh_cookie(response, new_refresh_token)
    await redis_client.setex(
        f"revoked_session:{payload.session_id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "1",
    )
    return tokens


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    if refresh_token:
        payload = decode_token(refresh_token, expected_type="refresh")
        if payload.sub == current_user.id and payload.tenant_id == current_user.tenant_id:
            await redis_client.setex(
                f"revoked_session:{payload.session_id}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                "1",
            )
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.API_V1_STR}/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
