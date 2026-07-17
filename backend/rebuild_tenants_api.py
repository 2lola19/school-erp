import os

content = """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated
from pydantic import BaseModel
import uuid

from app.api.v1.dependencies import get_db
from app.models.core import Tenant, User, Role
from app.core.security import get_password_hash

router = APIRouter()

class TenantCreate(BaseModel):
    name: str
    domain: str

class SchoolAdminCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

@router.get("/")
async def get_tenants(session: Annotated[AsyncSession, Depends(get_db)]):
    result = await session.execute(select(Tenant))
    return result.scalars().all()

@router.post("/")
async def create_tenant(tenant: TenantCreate, session: Annotated[AsyncSession, Depends(get_db)]):
    new_tenant = Tenant(name=tenant.name, domain=tenant.domain)
    session.add(new_tenant)
    await session.commit()
    await session.refresh(new_tenant)
    return new_tenant

@router.post("/{tenant_id}/admin")
async def create_school_admin(
    tenant_id: str,
    admin_data: SchoolAdminCreate,
    session: Annotated[AsyncSession, Depends(get_db)]
):
    # Enforce strict UUID casting to prevent database parsing errors
    try:
        target_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Tenant ID format")

    # 1. Verify tenant exists
    tenant_res = await session.execute(select(Tenant).where(Tenant.id == target_uuid))
    if not tenant_res.scalars().first():
        raise HTTPException(status_code=404, detail="Institution not found in database")

    # 2. Dynamically instantiate the School Admin role if missing
    role_res = await session.execute(select(Role).where(Role.name == "School Admin"))
    role = role_res.scalars().first()
    if not role:
        role = Role(name="School Admin", description="Local administrator for a specific tenant")
        session.add(role)
        await session.commit()
        await session.refresh(role)

    # 3. Prevent duplicate accounts
    user_res = await session.execute(select(User).where(User.email == admin_data.email))
    if user_res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered in system")

    # 4. Mint the new School Admin bound to the target tenant
    new_admin = User(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        first_name=admin_data.first_name,
        last_name=admin_data.last_name,
        role_id=role.id,
        tenant_id=target_uuid
    )
    session.add(new_admin)
    await session.commit()
    
    return {"message": "School Admin provisioned successfully"}
"""

with open("app/api/v1/endpoints/tenants.py", "w", encoding="utf-8") as f:
    f.write(content.strip() + "\n")

print("[+] Tenants API rebuilt from scratch. Scopes sanitized.")