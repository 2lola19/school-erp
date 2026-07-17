from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
from pydantic import BaseModel, ConfigDict
import uuid

from app.api.v1.dependencies import get_db, get_current_user_payload
from app.schemas.auth import TokenPayload
from app.models.core import Tenant, User, Role
from app.core.security import get_password_hash

router = APIRouter()

class TenantCreate(BaseModel):
    name: str
    domain: str

class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    model_config = ConfigDict(from_attributes=True)

class SchoolAdminCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    if "view_all_tenants" not in payload.permissions:
        raise HTTPException(status_code=403, detail="Global visibility restricted.")
    result = await session.execute(select(Tenant))
    return result.scalars().all()

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant: TenantCreate, 
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    new_tenant = Tenant(name=tenant.name, domain=tenant.domain)
    session.add(new_tenant)
    await session.commit()
    await session.refresh(new_tenant)
    return new_tenant

@router.post("/{tenant_id}/admin")
async def create_school_admin(
    tenant_id: str,
    admin_data: SchoolAdminCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        target_uuid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Tenant ID format")

    tenant_res = await session.execute(select(Tenant).where(Tenant.id == target_uuid))
    if not tenant_res.scalars().first():
        raise HTTPException(status_code=404, detail="Institution not found in database")

    role_res = await session.execute(select(Role).where(Role.name == "School Admin"))
    role = role_res.scalars().first()
    if not role:
        role = Role(name="School Admin", description="Local administrator for a specific tenant", tenant_id=target_uuid)
        session.add(role)
        await session.commit()
        await session.refresh(role)

    user_res = await session.execute(select(User).where(User.email == admin_data.email))
    if user_res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered in system")

    new_admin = User(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        role_id=role.id,
        tenant_id=target_uuid
    )
    session.add(new_admin)
    await session.commit()
    
    return {"message": "School Admin provisioned successfully"}
