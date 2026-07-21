from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as redis
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import (
    AuditLog,
    Permission,
    PermissionBundlePermission,
    Role,
    RoleConflict,
    RoleDelegationRule,
    RolePermission,
    RolePermissionBundle,
    Staff,
    StaffRoleAssignment,
    User,
)
from app.schemas.auth import CurrentUser
from app.schemas.roles import (
    PermissionPreview,
    RoleAssignmentCreate,
    RoleAssignmentUpdate,
    StaffCreate,
)
from app.services.access_control import active_assignment_predicates, bump_permission_version

SECONDARY_ROLE_LIMIT = 4
CATEGORY_LIMITS = {
    "MANAGEMENT": 1,
    "FINANCE": 1,
    "HEALTH": 1,
    "PLATFORM": 1,
}
SCOPE_REQUIRED_CODES = {
    "SUBJECT_TEACHER",
    "CLASS_TEACHER",
    "HEAD_OF_DEPARTMENT",
    "COACH",
    "ACTIVITY_PATRON",
    "HOUSE_MASTER",
    "EXAMINATION_OFFICER",
    "CAMPUS_MANAGER",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def get_staff_for_update(
    session: AsyncSession, tenant_id: UUID, staff_id: UUID
) -> Staff:
    result = await session.execute(
        select(Staff)
        .where(Staff.id == staff_id, Staff.tenant_id == tenant_id)
        .with_for_update()
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    return staff


async def get_staff_assignments_for_update(
    session: AsyncSession, tenant_id: UUID, staff_id: UUID
) -> list[StaffRoleAssignment]:
    result = await session.execute(
        select(StaffRoleAssignment)
        .where(
            StaffRoleAssignment.tenant_id == tenant_id,
            StaffRoleAssignment.staff_id == staff_id,
            StaffRoleAssignment.status.in_(["ACTIVE", "PENDING"]),
        )
        .with_for_update()
    )
    return list(result.scalars().all())


async def _get_role(session: AsyncSession, tenant_id: UUID, role_id: UUID) -> Role:
    result = await session.execute(
        select(Role).where(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
            Role.is_active.is_(True),
        )
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail="Role is inactive or belongs to another tenant")
    return role


async def _check_delegation(
    session: AsyncSession, actor: CurrentUser, assignable_role_id: UUID
) -> bool:
    if "roles.assign.any" in actor.permissions:
        return False
    result = await session.execute(
        select(RoleDelegationRule.requires_approval)
        .join(StaffRoleAssignment, StaffRoleAssignment.role_id == RoleDelegationRule.assigner_role_id)
        .join(Staff, Staff.id == StaffRoleAssignment.staff_id)
        .where(
            Staff.user_id == actor.id,
            Staff.tenant_id == actor.tenant_id,
            StaffRoleAssignment.tenant_id == actor.tenant_id,
            RoleDelegationRule.tenant_id == actor.tenant_id,
            RoleDelegationRule.assignable_role_id == assignable_role_id,
            *active_assignment_predicates(),
        )
    )
    rules = result.scalars().all()
    if not rules:
        raise HTTPException(status_code=403, detail="Role exceeds your delegation authority")
    return any(rules)


async def _conflicts(
    session: AsyncSession,
    tenant_id: UUID,
    proposed_role_id: UUID,
    active_role_ids: set[UUID],
) -> list[RoleConflict]:
    if not active_role_ids:
        return []
    result = await session.execute(
        select(RoleConflict).where(
            RoleConflict.tenant_id == tenant_id,
            or_(
                (RoleConflict.role_id == proposed_role_id)
                & (RoleConflict.conflicting_role_id.in_(active_role_ids)),
                (RoleConflict.conflicting_role_id == proposed_role_id)
                & (RoleConflict.role_id.in_(active_role_ids)),
            ),
        )
    )
    return list(result.scalars().all())


async def _validate_assignment(
    session: AsyncSession,
    actor: CurrentUser,
    staff: Staff,
    payload: RoleAssignmentCreate,
    assignments: list[StaffRoleAssignment],
) -> tuple[Role, list[RoleConflict], bool]:
    role = await _get_role(session, actor.tenant_id, payload.role_id)
    if role.code in SCOPE_REQUIRED_CODES and not payload.scope:
        raise HTTPException(status_code=400, detail=f"{role.name} requires an operational scope")

    if any(a.role_id == role.id for a in assignments):
        raise HTTPException(status_code=409, detail="Role is already active or awaiting approval")

    active = [a for a in assignments if a.status == "ACTIVE"]
    if payload.assignment_type == "SECONDARY":
        secondary = [a for a in active if a.assignment_type == "SECONDARY"]
        if len(secondary) >= SECONDARY_ROLE_LIMIT:
            raise HTTPException(status_code=409, detail="A staff member may have at most four active secondary roles")

        if role.role_category in CATEGORY_LIMITS:
            active_role_ids = [a.role_id for a in secondary]
            if active_role_ids:
                count_result = await session.execute(
                    select(func.count(Role.id)).where(
                        Role.id.in_(active_role_ids),
                        Role.role_category == role.role_category,
                    )
                )
                if count_result.scalar_one() >= CATEGORY_LIMITS[role.role_category]:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Only {CATEGORY_LIMITS[role.role_category]} active {role.role_category.lower()} secondary role is allowed",
                    )

    conflicts = await _conflicts(
        session, actor.tenant_id, role.id, {a.role_id for a in active}
    )
    blocked = [c for c in conflicts if c.action == "BLOCK"]
    if blocked:
        raise HTTPException(status_code=409, detail=blocked[0].reason)
    delegated_approval = await _check_delegation(session, actor, role.id)
    approval_required = (
        role.is_sensitive
        or role.requires_approval
        or delegated_approval
        or any(c.action == "REQUIRE_APPROVAL" for c in conflicts)
    )
    return role, conflicts, approval_required


def _audit(
    *,
    actor: CurrentUser,
    staff_id: UUID,
    assignment: StaffRoleAssignment,
    action: str,
    reason: str,
    old_values: dict | None = None,
) -> AuditLog:
    return AuditLog(
        tenant_id=actor.tenant_id,
        user_id=actor.id,
        staff_id=staff_id,
        action=action,
        entity_name="STAFF_ROLE_ASSIGNMENT",
        entity_id=str(assignment.id),
        reason=reason,
        old_values=old_values or {},
        new_values={
            "role_id": str(assignment.role_id),
            "assignment_type": assignment.assignment_type,
            "status": assignment.status,
        },
        scope=assignment.scope,
    )


async def create_staff_with_primary_role(
    session: AsyncSession,
    redis_client: redis.Redis,
    actor: CurrentUser,
    payload: StaffCreate,
) -> Staff:
    user_result = await session.execute(
        select(User).where(User.id == payload.user_id, User.tenant_id == actor.tenant_id).with_for_update()
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User belongs to another tenant or does not exist")
    staff = Staff(
        tenant_id=actor.tenant_id,
        user_id=user.id,
        employee_number=payload.employee_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        employment_position=payload.employment_position,
    )
    session.add(staff)
    await session.flush()
    assignment_payload = RoleAssignmentCreate(
        role_id=payload.primary_role_id,
        assignment_type="PRIMARY",
        scope=payload.role_scope,
        reason=payload.role_reason,
    )
    role, _, approval_required = await _validate_assignment(
        session, actor, staff, assignment_payload, []
    )
    if approval_required:
        raise HTTPException(status_code=400, detail="The initial primary role must not require approval")
    assignment = StaffRoleAssignment(
        tenant_id=actor.tenant_id,
        staff_id=staff.id,
        role_id=role.id,
        assignment_type="PRIMARY",
        status="ACTIVE",
        scope=payload.role_scope,
        assigned_by=actor.id,
        assignment_reason=payload.role_reason,
    )
    session.add(assignment)
    await bump_permission_version(session, redis_client, user=user)
    await session.flush()
    session.add(_audit(actor=actor, staff_id=staff.id, assignment=assignment, action="PRIMARY_ROLE_ASSIGNED", reason=payload.role_reason))
    return staff


async def assign_role(
    session: AsyncSession,
    redis_client: redis.Redis,
    actor: CurrentUser,
    staff_id: UUID,
    payload: RoleAssignmentCreate,
) -> StaffRoleAssignment:
    staff = await get_staff_for_update(session, actor.tenant_id, staff_id)
    assignments = await get_staff_assignments_for_update(session, actor.tenant_id, staff_id)
    role, _, approval_required = await _validate_assignment(
        session, actor, staff, payload, assignments
    )
    if payload.assignment_type == "PRIMARY" and any(
        a.assignment_type == "PRIMARY" and a.status == "ACTIVE" for a in assignments
    ) and not approval_required:
        for old_primary in assignments:
            if old_primary.assignment_type == "PRIMARY" and old_primary.status == "ACTIVE":
                old_primary.status = "REVOKED"
                old_primary.revoked_by = actor.id
                old_primary.revoked_at = now_utc()
                old_primary.revocation_reason = payload.reason
        await session.flush()

    assignment = StaffRoleAssignment(
        tenant_id=actor.tenant_id,
        staff_id=staff.id,
        role_id=role.id,
        assignment_type=payload.assignment_type,
        status="PENDING" if approval_required else "ACTIVE",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        is_temporary=payload.is_temporary,
        scope=payload.scope,
        assigned_by=actor.id,
        assignment_reason=payload.reason,
        delegated_by=payload.delegated_by,
        delegation_reason=payload.delegation_reason,
    )
    session.add(assignment)
    user = await session.get(User, staff.user_id)
    await bump_permission_version(session, redis_client, user=user)
    await session.flush()
    session.add(
        _audit(
            actor=actor,
            staff_id=staff.id,
            assignment=assignment,
            action=f"{payload.assignment_type}_ROLE_{assignment.status}",
            reason=payload.reason,
        )
    )
    return assignment


async def transition_assignment(
    session: AsyncSession,
    redis_client: redis.Redis,
    actor: CurrentUser,
    staff_id: UUID,
    assignment_id: UUID,
    target_status: str,
    reason: str,
) -> StaffRoleAssignment:
    staff = await get_staff_for_update(session, actor.tenant_id, staff_id)
    result = await session.execute(
        select(StaffRoleAssignment)
        .where(
            StaffRoleAssignment.id == assignment_id,
            StaffRoleAssignment.staff_id == staff_id,
            StaffRoleAssignment.tenant_id == actor.tenant_id,
        )
        .with_for_update()
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    old_status = assignment.status
    if target_status == "ACTIVE":
        if assignment.status != "PENDING":
            raise HTTPException(status_code=409, detail="Only pending assignments can be approved")
        if assignment.assigned_by == actor.id:
            raise HTTPException(status_code=409, detail="Sensitive role assignments cannot be self-approved")
        current = await get_staff_assignments_for_update(session, actor.tenant_id, staff_id)
        active = [item for item in current if item.status == "ACTIVE" and item.id != assignment.id]
        role = await _get_role(session, actor.tenant_id, assignment.role_id)
        if assignment.assignment_type == "SECONDARY":
            secondary = [item for item in active if item.assignment_type == "SECONDARY"]
            if len(secondary) >= SECONDARY_ROLE_LIMIT:
                raise HTTPException(
                    status_code=409,
                    detail="A staff member may have at most four active secondary roles",
                )
            if role.role_category in CATEGORY_LIMITS:
                active_role_ids = [item.role_id for item in secondary]
                if active_role_ids:
                    count_result = await session.execute(
                        select(func.count(Role.id)).where(
                            Role.id.in_(active_role_ids),
                            Role.role_category == role.role_category,
                        )
                    )
                    if count_result.scalar_one() >= CATEGORY_LIMITS[role.role_category]:
                        raise HTTPException(
                            status_code=409,
                            detail=f"Only {CATEGORY_LIMITS[role.role_category]} active {role.role_category.lower()} secondary role is allowed",
                        )
        conflicts = await _conflicts(
            session,
            actor.tenant_id,
            role.id,
            {item.role_id for item in active},
        )
        blocked = [conflict for conflict in conflicts if conflict.action == "BLOCK"]
        if blocked:
            raise HTTPException(status_code=409, detail=blocked[0].reason)
        if assignment.assignment_type == "PRIMARY":
            for existing in current:
                if existing.id != assignment.id and existing.assignment_type == "PRIMARY" and existing.status == "ACTIVE":
                    existing.status = "REVOKED"
                    existing.revoked_by = actor.id
                    existing.revoked_at = now_utc()
                    existing.revocation_reason = reason
            await session.flush()
        assignment.approved_by = actor.id
        assignment.approved_at = now_utc()
    elif target_status in {"REVOKED", "SUSPENDED"}:
        if assignment.assignment_type == "PRIMARY" and assignment.status == "ACTIVE":
            raise HTTPException(status_code=409, detail="Replace an active primary role; do not remove it")
        if target_status == "REVOKED":
            assignment.revoked_by = actor.id
            assignment.revoked_at = now_utc()
            assignment.revocation_reason = reason
    else:
        raise HTTPException(status_code=400, detail="Unsupported role transition")
    assignment.status = target_status
    user = await session.get(User, staff.user_id)
    await bump_permission_version(session, redis_client, user=user)
    session.add(
        _audit(
            actor=actor,
            staff_id=staff.id,
            assignment=assignment,
            action=f"ROLE_{target_status}",
            reason=reason,
            old_values={"status": old_status},
        )
    )
    return assignment


async def update_assignment(
    session: AsyncSession,
    redis_client: redis.Redis,
    actor: CurrentUser,
    staff_id: UUID,
    assignment_id: UUID,
    payload: RoleAssignmentUpdate,
) -> StaffRoleAssignment:
    staff = await get_staff_for_update(session, actor.tenant_id, staff_id)
    result = await session.execute(
        select(StaffRoleAssignment)
        .where(
            StaffRoleAssignment.id == assignment_id,
            StaffRoleAssignment.staff_id == staff_id,
            StaffRoleAssignment.tenant_id == actor.tenant_id,
        )
        .with_for_update()
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    if assignment.status not in {"ACTIVE", "PENDING"}:
        raise HTTPException(status_code=409, detail="Only active or pending assignments can be updated")
    role = await _get_role(session, actor.tenant_id, assignment.role_id)
    starts_at = payload.starts_at if "starts_at" in payload.model_fields_set else assignment.starts_at
    ends_at = payload.ends_at if "ends_at" in payload.model_fields_set else assignment.ends_at
    scope = assignment.scope if "scope" not in payload.model_fields_set else (payload.scope or {})
    if role.code in SCOPE_REQUIRED_CODES and not scope:
        raise HTTPException(status_code=400, detail=f"{role.name} requires an operational scope")
    if starts_at and ends_at and ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be later than starts_at")

    old_values = {
        "starts_at": assignment.starts_at.isoformat() if assignment.starts_at else None,
        "ends_at": assignment.ends_at.isoformat() if assignment.ends_at else None,
        "scope": assignment.scope,
    }
    assignment.starts_at = starts_at
    assignment.ends_at = ends_at
    assignment.scope = scope
    assignment.is_temporary = ends_at is not None
    user = await session.get(User, staff.user_id)
    await bump_permission_version(session, redis_client, user=user)
    session.add(
        _audit(
            actor=actor,
            staff_id=staff.id,
            assignment=assignment,
            action="ROLE_ASSIGNMENT_UPDATED",
            reason=payload.reason,
            old_values=old_values,
        )
    )
    return assignment


async def permission_preview(
    session: AsyncSession,
    actor: CurrentUser,
    staff_id: UUID,
    payload: RoleAssignmentCreate,
) -> PermissionPreview:
    staff = await get_staff_for_update(session, actor.tenant_id, staff_id)
    assignments = await get_staff_assignments_for_update(session, actor.tenant_id, staff_id)
    role, conflicts, approval_required = await _validate_assignment(
        session, actor, staff, payload, assignments
    )
    permissions_result = await session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id, RolePermission.tenant_id == actor.tenant_id)
    )
    bundle_permissions_result = await session.execute(
        select(Permission.name)
        .join(
            PermissionBundlePermission,
            PermissionBundlePermission.permission_id == Permission.id,
        )
        .join(
            RolePermissionBundle,
            RolePermissionBundle.bundle_id == PermissionBundlePermission.bundle_id,
        )
        .where(
            RolePermissionBundle.role_id == role.id,
            RolePermissionBundle.tenant_id == actor.tenant_id,
            PermissionBundlePermission.tenant_id == actor.tenant_id,
        )
    )
    permissions = set(permissions_result.scalars().all())
    permissions.update(bundle_permissions_result.scalars().all())
    return PermissionPreview(
        role_id=role.id,
        assignment_type=payload.assignment_type,
        proposed_status="PENDING" if approval_required else "ACTIVE",
        permissions_gained=sorted(permissions),
        conflict_warnings=[conflict.reason for conflict in conflicts],
        approval_required=approval_required,
        scope=payload.scope,
    )
