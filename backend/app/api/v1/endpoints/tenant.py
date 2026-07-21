from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, require_permissions
from app.core.security import get_password_hash
from app.models.core import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    Staff,
    StaffRoleAssignment,
    Tenant,
    User,
)
from app.schemas.auth import CurrentUser
from app.services.role_templates import (
    SCHOOL_ADMIN_PERMISSIONS,
    ensure_tenant_role_templates,
)

router = APIRouter()

class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=2, max_length=255, pattern=r"^[a-z0-9.-]+$")


class TenantResponse(BaseModel):
    id: UUID
    name: str
    domain: str

    model_config = ConfigDict(from_attributes=True)


class SchoolAdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    employee_number: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=3, max_length=2000)


@router.get("/", response_model=list[TenantResponse])
async def get_tenants(
    actor: Annotated[CurrentUser, Depends(require_permissions("tenants.read"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[Tenant]:
    result = await session.execute(select(Tenant).order_by(Tenant.name))
    return list(result.scalars().all())


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("tenants.manage"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    domain = payload.domain.lower()
    if await session.scalar(select(Tenant).where(Tenant.domain == domain)):
        raise HTTPException(status_code=409, detail="Tenant domain already exists")
    tenant = Tenant(name=payload.name, domain=domain)
    session.add(tenant)
    await session.flush()
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant.id)},
    )
    await ensure_tenant_role_templates(session, tenant.id)
    await session.commit()
    await session.refresh(tenant)
    return tenant


@router.post("/{tenant_id}/admin", status_code=status.HTTP_201_CREATED)
async def create_school_admin(
    tenant_id: UUID,
    payload: SchoolAdminCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("tenants.manage"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    await ensure_tenant_role_templates(session, tenant_id)
    if await session.scalar(
        select(User).where(User.tenant_id == tenant_id, User.email == payload.email.lower())
    ):
        raise HTTPException(status_code=409, detail="Email already exists in this tenant")

    role = await session.scalar(
        select(Role).where(Role.tenant_id == tenant_id, Role.code == "SCHOOL_ADMIN")
    )
    if not role:
        role = Role(
            tenant_id=tenant_id,
            name="School Administrator",
            code="SCHOOL_ADMIN",
            description="Tenant administrator with delegated school operations",
            role_category="MANAGEMENT",
            is_system_role=True,
        )
        session.add(role)
        await session.flush()

    for permission_name in sorted(SCHOOL_ADMIN_PERMISSIONS):
        permission = await session.scalar(
            select(Permission).where(Permission.name == permission_name)
        )
        if not permission:
            permission = Permission(name=permission_name)
            session.add(permission)
            await session.flush()
        existing = await session.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if not existing:
            session.add(
                RolePermission(
                    tenant_id=tenant_id,
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )

    user = User(
        tenant_id=tenant_id,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
    )
    session.add(user)
    await session.flush()
    staff = Staff(
        tenant_id=tenant_id,
        user_id=user.id,
        employee_number=payload.employee_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        employment_position="School Administrator",
    )
    session.add(staff)
    await session.flush()
    assignment = StaffRoleAssignment(
        tenant_id=tenant_id,
        staff_id=staff.id,
        role_id=role.id,
        assignment_type="PRIMARY",
        status="ACTIVE",
        assigned_by=actor.id,
        assignment_reason=payload.reason,
    )
    session.add(assignment)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=actor.id,
            staff_id=staff.id,
            action="SCHOOL_ADMIN_PROVISIONED",
            entity_name="USER",
            entity_id=str(user.id),
            reason=payload.reason,
        )
    )
    await session.commit()
    return {"message": "School administrator provisioned", "user_id": str(user.id)}
