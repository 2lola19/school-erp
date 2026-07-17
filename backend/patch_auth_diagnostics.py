import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

# 1. Purge the Auth Hack and Restore Production Logic
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
    result = await session.execute(select(User).where(User.email == creds.email))
    user = result.scalars().first()
    
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication rejected: Bad email or password.")
        
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
print("[+] Auth logic restored to production state. Hack removed.")

# 2. Expose True Errors on the Frontend
frontend_login = "../frontend/src/app/(auth)/login/page.tsx"
if os.path.exists(frontend_login):
    with open(frontend_login, "r", encoding="utf-8") as f:
        content = f.read()
    
    bad_catch = "setError('Invalid credentials');"
    good_catch = "setError(err.response?.data?.detail || '500 Server Error. Check Uvicorn terminal.');"
    
    if bad_catch in content:
        content = content.replace(bad_catch, good_catch)
        with open(frontend_login, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] Frontend unmasked. Exact server errors will now be displayed.")

# 3. Verify Database Integrity
from app.core.config import settings
from app.models.core import User

async def verify_db():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)
    async with SessionLocal() as session:
        res = await session.execute(select(User))
        users = res.scalars().all()
        print("\n--- SECURE DATABASE LEDGER ---")
        for u in users:
            print(f"Account: {u.email} | Has Password Hash: {bool(u.password_hash)}")
        print("------------------------------\n")

asyncio.run(verify_db())