import os

schema_tenant = """
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
import uuid

class TenantBase(BaseModel):
    name: str
    domain: str

class TenantCreate(TenantBase):
    pass

class TenantResponse(TenantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
"""

endpoint_tenant = """
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.v1.dependencies import get_db, get_current_user_payload
from app.schemas.tenant import TenantCreate, TenantResponse
from app.schemas.auth import TokenPayload
from app.models.core import Tenant

router = APIRouter()

@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    if "view_all_tenants" not in payload.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
    
    result = await session.execute(select(Tenant))
    return result.scalars().all()

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_in: TenantCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    if "view_all_tenants" not in payload.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        
    result = await session.execute(select(Tenant).where(Tenant.domain == tenant_in.domain))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain already exists")
        
    new_tenant = Tenant(name=tenant_in.name, domain=tenant_in.domain)
    session.add(new_tenant)
    await session.commit()
    await session.refresh(new_tenant)
    return new_tenant
"""

router_patch = """
import os

init_path = "app/api/v1/__init__.py"
with open(init_path, "r", encoding="utf-8") as f:
    content = f.read()

if "tenant" not in content:
    content = content.replace(
        "from app.api.v1.endpoints import auth",
        "from app.api.v1.endpoints import auth, tenant"
    )
    content += "\\napi_router.include_router(tenant.router, prefix=\\"/tenants\\", tags=[\\"tenants\\"])\\n"
    
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(content)
"""

files = {
    "app/schemas/tenant.py": schema_tenant,
    "app/api/v1/endpoints/tenant.py": endpoint_tenant,
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

exec(router_patch)
print("[+] Tenant API deployed and routed.")