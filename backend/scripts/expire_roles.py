"""Expire elapsed temporary roles and invalidate their permission caches."""

import asyncio
from datetime import datetime, timezone

import redis.asyncio as redis
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.core import AuditLog, Staff, StaffRoleAssignment, Tenant, User
from app.services.access_control import bump_permission_version


async def expire_roles() -> int:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    expired_count = 0
    try:
        async with AsyncSessionLocal() as session:
            tenant_ids = list((await session.execute(select(Tenant.id))).scalars().all())
            for tenant_id in tenant_ids:
                await session.execute(
                    text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                result = await session.execute(
                    select(StaffRoleAssignment)
                    .where(
                        StaffRoleAssignment.tenant_id == tenant_id,
                        StaffRoleAssignment.status == "ACTIVE",
                        StaffRoleAssignment.ends_at.is_not(None),
                        StaffRoleAssignment.ends_at <= datetime.now(timezone.utc),
                    )
                    .with_for_update(skip_locked=True)
                )
                for assignment in result.scalars().all():
                    staff = await session.get(Staff, assignment.staff_id)
                    user = await session.get(User, staff.user_id)
                    assignment.status = "EXPIRED"
                    await bump_permission_version(session, redis_client, user=user)
                    session.add(
                        AuditLog(
                            tenant_id=assignment.tenant_id,
                            user_id=None,
                            staff_id=assignment.staff_id,
                            action="ROLE_EXPIRED",
                            entity_name="STAFF_ROLE_ASSIGNMENT",
                            entity_id=str(assignment.id),
                            reason="Assignment end date elapsed",
                        )
                    )
                    expired_count += 1
            await session.commit()
    finally:
        await redis_client.aclose()
    return expired_count


if __name__ == "__main__":
    print(f"Expired {asyncio.run(expire_roles())} role assignments")
