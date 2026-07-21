from typing import Annotated
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_redis, get_rls_db, require_permissions
from app.models.core import RoleConflict, Staff, StaffRoleAssignment, User
from app.schemas.auth import CurrentUser
from app.schemas.roles import (
    EffectivePermissionsResponse,
    PermissionPreview,
    RoleActionRequest,
    RoleAssignmentCreate,
    RoleAssignmentResponse,
    RoleAssignmentUpdate,
    RoleConflictResponse,
    RoleHistoryResponse,
    StaffCreate,
    StaffResponse,
)
from app.services.access_control import get_effective_permissions
from app.services.roles import (
    assign_role,
    create_staff_with_primary_role,
    permission_preview,
    transition_assignment,
    update_assignment,
)

router = APIRouter()


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.create", "roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> Staff:
    staff = await create_staff_with_primary_role(session, redis_client, actor, payload)
    await session.commit()
    await session.refresh(staff)
    return staff


@router.get("/{staff_id}/roles", response_model=list[RoleAssignmentResponse])
async def list_staff_roles(
    staff_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[StaffRoleAssignment]:
    result = await session.execute(
        select(StaffRoleAssignment)
        .where(
            StaffRoleAssignment.staff_id == staff_id,
            StaffRoleAssignment.tenant_id == actor.tenant_id,
        )
        .order_by(StaffRoleAssignment.created_at.desc())
    )
    return list(result.scalars().all())


async def _assign(
    staff_id: UUID,
    payload: RoleAssignmentCreate,
    actor: CurrentUser,
    session: AsyncSession,
    redis_client: redis.Redis,
) -> StaffRoleAssignment:
    assignment = await assign_role(session, redis_client, actor, staff_id, payload)
    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.post("/{staff_id}/roles/primary", response_model=RoleAssignmentResponse, status_code=201)
async def assign_primary_role(
    staff_id: UUID,
    payload: RoleAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    payload.assignment_type = "PRIMARY"
    return await _assign(staff_id, payload, actor, session, redis_client)


@router.put("/{staff_id}/roles/primary", response_model=RoleAssignmentResponse)
async def change_primary_role(
    staff_id: UUID,
    payload: RoleAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    payload.assignment_type = "PRIMARY"
    return await _assign(staff_id, payload, actor, session, redis_client)


@router.post("/{staff_id}/roles/secondary", response_model=RoleAssignmentResponse, status_code=201)
async def assign_secondary_role(
    staff_id: UUID,
    payload: RoleAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    payload.assignment_type = "SECONDARY"
    return await _assign(staff_id, payload, actor, session, redis_client)


async def _transition(
    staff_id: UUID,
    assignment_id: UUID,
    action: RoleActionRequest,
    target_status: str,
    actor: CurrentUser,
    session: AsyncSession,
    redis_client: redis.Redis,
) -> StaffRoleAssignment:
    assignment = await transition_assignment(
        session,
        redis_client,
        actor,
        staff_id,
        assignment_id,
        target_status,
        action.reason,
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.post("/{staff_id}/roles/{assignment_id}/approve", response_model=RoleAssignmentResponse)
async def approve_role(
    staff_id: UUID,
    assignment_id: UUID,
    action: RoleActionRequest,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.approve"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    return await _transition(staff_id, assignment_id, action, "ACTIVE", actor, session, redis_client)


@router.patch("/{staff_id}/roles/{assignment_id}", response_model=RoleAssignmentResponse)
async def edit_role_assignment(
    staff_id: UUID,
    assignment_id: UUID,
    payload: RoleAssignmentUpdate,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    assignment = await update_assignment(
        session,
        redis_client,
        actor,
        staff_id,
        assignment_id,
        payload,
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.post("/{staff_id}/roles/{assignment_id}/suspend", response_model=RoleAssignmentResponse)
async def suspend_role(
    staff_id: UUID,
    assignment_id: UUID,
    action: RoleActionRequest,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.revoke"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    return await _transition(staff_id, assignment_id, action, "SUSPENDED", actor, session, redis_client)


@router.post("/{staff_id}/roles/{assignment_id}/revoke", response_model=RoleAssignmentResponse)
async def revoke_role(
    staff_id: UUID,
    assignment_id: UUID,
    action: RoleActionRequest,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.revoke"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    return await _transition(staff_id, assignment_id, action, "REVOKED", actor, session, redis_client)


@router.delete("/{staff_id}/roles/secondary/{assignment_id}", response_model=RoleAssignmentResponse)
async def remove_secondary_role(
    staff_id: UUID,
    assignment_id: UUID,
    action: RoleActionRequest,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.revoke"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StaffRoleAssignment:
    return await _transition(staff_id, assignment_id, action, "REVOKED", actor, session, redis_client)


@router.get("/{staff_id}/permissions", response_model=EffectivePermissionsResponse)
async def staff_permissions(
    staff_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> EffectivePermissionsResponse:
    result = await session.execute(
        select(User)
        .join(Staff, Staff.user_id == User.id)
        .where(Staff.id == staff_id, Staff.tenant_id == actor.tenant_id)
    )
    user = result.scalar_one()
    permissions = await get_effective_permissions(session, redis_client, user)
    return EffectivePermissionsResponse(
        staff_id=staff_id,
        permission_version=user.permission_version,
        permissions=sorted(permissions),
    )


@router.get("/{staff_id}/role-history", response_model=RoleHistoryResponse)
async def role_history(
    staff_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> RoleHistoryResponse:
    assignments = await list_staff_roles(staff_id, actor, session)
    return RoleHistoryResponse(assignments=assignments)


@router.get("/{staff_id}/role-conflicts", response_model=list[RoleConflictResponse])
async def role_conflicts(
    staff_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[RoleConflict]:
    active_roles = select(StaffRoleAssignment.role_id).where(
        StaffRoleAssignment.staff_id == staff_id,
        StaffRoleAssignment.tenant_id == actor.tenant_id,
        StaffRoleAssignment.status == "ACTIVE",
    )
    result = await session.execute(
        select(RoleConflict).where(
            RoleConflict.tenant_id == actor.tenant_id,
            or_(RoleConflict.role_id.in_(active_roles), RoleConflict.conflicting_role_id.in_(active_roles)),
        )
    )
    return list(result.scalars().all())


@router.post("/{staff_id}/permission-preview", response_model=PermissionPreview)
async def preview_permissions(
    staff_id: UUID,
    payload: RoleAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> PermissionPreview:
    return await permission_preview(session, actor, staff_id, payload)
