import json
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as redis
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import (
    Permission,
    PermissionBundle,
    PermissionBundlePermission,
    RolePermission,
    RolePermissionBundle,
    Staff,
    StaffRoleAssignment,
    User,
    UserPermission,
)


def permission_cache_key(tenant_id: UUID, user_id: UUID, version: int) -> str:
    return f"permissions:{tenant_id}:{user_id}:{version}"


async def get_effective_permissions(
    session: AsyncSession,
    redis_client: redis.Redis,
    user: User,
) -> set[str]:
    key = permission_cache_key(user.tenant_id, user.id, user.permission_version)
    cached = await redis_client.get(key)
    if cached:
        return set(json.loads(cached))

    now = datetime.now(timezone.utc)
    role_permissions = await session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(StaffRoleAssignment, StaffRoleAssignment.role_id == RolePermission.role_id)
        .join(Staff, Staff.id == StaffRoleAssignment.staff_id)
        .where(
            Staff.user_id == user.id,
            Staff.tenant_id == user.tenant_id,
            RolePermission.tenant_id == user.tenant_id,
            StaffRoleAssignment.tenant_id == user.tenant_id,
            StaffRoleAssignment.status == "ACTIVE",
            or_(StaffRoleAssignment.starts_at.is_(None), StaffRoleAssignment.starts_at <= now),
            or_(StaffRoleAssignment.ends_at.is_(None), StaffRoleAssignment.ends_at > now),
        )
    )
    effective = set(role_permissions.scalars().all())

    bundle_permissions = await session.execute(
        select(Permission.name)
        .join(PermissionBundlePermission, PermissionBundlePermission.permission_id == Permission.id)
        .join(PermissionBundle, PermissionBundle.id == PermissionBundlePermission.bundle_id)
        .join(RolePermissionBundle, RolePermissionBundle.bundle_id == PermissionBundle.id)
        .join(StaffRoleAssignment, StaffRoleAssignment.role_id == RolePermissionBundle.role_id)
        .join(Staff, Staff.id == StaffRoleAssignment.staff_id)
        .where(
            Staff.user_id == user.id,
            Staff.tenant_id == user.tenant_id,
            PermissionBundle.tenant_id == user.tenant_id,
            PermissionBundle.is_active.is_(True),
            StaffRoleAssignment.tenant_id == user.tenant_id,
            StaffRoleAssignment.status == "ACTIVE",
            or_(StaffRoleAssignment.starts_at.is_(None), StaffRoleAssignment.starts_at <= now),
            or_(StaffRoleAssignment.ends_at.is_(None), StaffRoleAssignment.ends_at > now),
        )
    )
    effective.update(bundle_permissions.scalars().all())

    overrides = await session.execute(
        select(Permission.name, UserPermission.effect)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(
            UserPermission.user_id == user.id,
            UserPermission.tenant_id == user.tenant_id,
            or_(UserPermission.expires_at.is_(None), UserPermission.expires_at > now),
            or_(UserPermission.effect == "DENY", UserPermission.approved_at.is_not(None)),
        )
    )
    allowed: set[str] = set()
    denied: set[str] = set()
    for permission_name, effect in overrides.all():
        (denied if effect == "DENY" else allowed).add(permission_name)

    effective = (effective | allowed) - denied
    await redis_client.setex(key, 300, json.dumps(sorted(effective)))
    return effective


async def bump_permission_version(
    session: AsyncSession,
    redis_client: redis.Redis,
    *,
    user: User,
) -> None:
    old_key = permission_cache_key(user.tenant_id, user.id, user.permission_version)
    user.permission_version += 1
    await redis_client.delete(old_key)


def scope_contains(assignment_scope: dict, required_scope: dict) -> bool:
    """Return true when an assignment scope covers every requested dimension."""
    if not assignment_scope:
        return True
    for key, required_value in required_scope.items():
        assigned_value = assignment_scope.get(key)
        if assigned_value is None:
            return False
        if isinstance(assigned_value, list):
            if required_value not in assigned_value and str(required_value) not in {
                str(value) for value in assigned_value
            }:
                return False
        elif str(assigned_value) != str(required_value):
            return False
    return True


async def ensure_permission_scope(
    session: AsyncSession,
    *,
    user_id: UUID,
    tenant_id: UUID,
    permission_name: str,
    required_scope: dict,
) -> None:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(StaffRoleAssignment.scope)
        .join(RolePermission, RolePermission.role_id == StaffRoleAssignment.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .join(Staff, Staff.id == StaffRoleAssignment.staff_id)
        .where(
            Staff.user_id == user_id,
            Staff.tenant_id == tenant_id,
            StaffRoleAssignment.tenant_id == tenant_id,
            Permission.name == permission_name,
            StaffRoleAssignment.status == "ACTIVE",
            or_(StaffRoleAssignment.starts_at.is_(None), StaffRoleAssignment.starts_at <= now),
            or_(StaffRoleAssignment.ends_at.is_(None), StaffRoleAssignment.ends_at > now),
        )
    )
    if any(scope_contains(scope or {}, required_scope) for scope in result.scalars().all()):
        return

    direct_allow = await session.scalar(
        select(UserPermission.id)
        .join(Permission, Permission.id == UserPermission.permission_id)
        .where(
            UserPermission.user_id == user_id,
            UserPermission.tenant_id == tenant_id,
            UserPermission.effect == "ALLOW",
            UserPermission.approved_at.is_not(None),
            Permission.name == permission_name,
            or_(UserPermission.expires_at.is_(None), UserPermission.expires_at > now),
        )
    )
    if not direct_allow:
        raise HTTPException(status_code=403, detail="Permission does not cover the requested scope")


def active_assignment_predicates(now: datetime | None = None) -> tuple:
    instant = now or datetime.now(timezone.utc)
    return (
        StaffRoleAssignment.status == "ACTIVE",
        or_(StaffRoleAssignment.starts_at.is_(None), StaffRoleAssignment.starts_at <= instant),
        or_(StaffRoleAssignment.ends_at.is_(None), StaffRoleAssignment.ends_at > instant),
    )
