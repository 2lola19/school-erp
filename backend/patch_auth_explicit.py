import os

auth_code = """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from app.api.v1.dependencies import get_db
from app.schemas.auth import LoginCredentials, TokenResponse
from app.models.core import User, Permission, RolePermission
from app.core.security import verify_password
from app.services import auth_service

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(creds: LoginCredentials, session: Annotated[AsyncSession, Depends(get_db)]):
    # Fetch the user using standard column matching
    result = await session.execute(select(User).where(User.email == creds.email))
    user = result.scalars().first()
    
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        
    # Explicitly join the RBAC tables using the known role_id
    perms = []
    if user.role_id:
        perm_query = await session.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
        )
        perms = perm_query.scalars().all()
        
    return await auth_service.generate_tokens(user, permissions=list(perms))
"""

with open("app/api/v1/endpoints/auth.py", "w", encoding="utf-8") as f:
    f.write(auth_code.strip() + "\n")

print("[+] Auth endpoint rebuilt to use explicit SQL joins.")