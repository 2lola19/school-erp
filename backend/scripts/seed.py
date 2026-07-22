"""Bootstrap the first platform administrator from environment variables.

Required:
    BOOTSTRAP_ADMIN_EMAIL
    BOOTSTRAP_ADMIN_PASSWORD (minimum 12 characters)
"""

import asyncio
import os

from sqlalchemy import select, text

from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.core import Permission, Role, RolePermission, Staff, StaffRoleAssignment, Tenant, User
from app.models.subscriptions import SubscriptionChangeHistory, SubscriptionPlan, TenantSubscription

PLATFORM_PERMISSIONS = {
    "tenants.read",
    "tenants.manage",
    "staff.read",
    "staff.create",
    "roles.assign",
    "roles.assign.any",
    "roles.approve",
    "roles.revoke",
    "audit_logs.read",
    "subscriptions.read",
    "subscriptions.manage",
    "plans.read",
    "plans.manage",
    "add_ons.manage",
    "tenant_entitlements.read",
    "tenant_entitlements.override",
    "billing.read",
    "billing.manage",
}


async def seed() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").lower().strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    if not email or len(password) < 12:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and a 12+ character BOOTSTRAP_ADMIN_PASSWORD")

    async with AsyncSessionLocal() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.domain == "platform.local"))
        if not tenant:
            tenant = Tenant(name="School ERP Platform", domain="platform.local")
            session.add(tenant)
            await session.flush()
        await session.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
            {"tenant_id": str(tenant.id)},
        )
        current_subscription = await session.scalar(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant.id,
                TenantSubscription.is_current.is_(True),
            )
        )
        if current_subscription is None:
            plan = await session.scalar(
                select(SubscriptionPlan).where(SubscriptionPlan.code == "ENTERPRISE_PLUS")
            )
            if plan is None:
                raise SystemExit("Run scripts.seed_subscriptions before bootstrapping the platform administrator")
            current_subscription = TenantSubscription(
                tenant_id=tenant.id,
                plan_id=plan.id,
                status="ACTIVE",
                is_current=True,
            )
            session.add(current_subscription)
            session.add(
                SubscriptionChangeHistory(
                    tenant_id=tenant.id,
                    old_plan_id=None,
                    new_plan_id=plan.id,
                    change_type="CREATED",
                    reason="Platform bootstrap subscription",
                )
            )
        if await session.scalar(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        ):
            await session.commit()
            print("Platform administrator already exists")
            return

        role = Role(
            tenant_id=tenant.id,
            name="Platform Administrator",
            code="PLATFORM_ADMIN",
            role_category="PLATFORM",
            is_system_role=True,
            is_sensitive=True,
            requires_approval=True,
        )
        session.add(role)
        await session.flush()
        for name in sorted(PLATFORM_PERMISSIONS):
            permission = await session.scalar(select(Permission).where(Permission.name == name))
            if not permission:
                permission = Permission(name=name)
                session.add(permission)
                await session.flush()
            session.add(
                RolePermission(
                    tenant_id=tenant.id,
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=get_password_hash(password),
        )
        session.add(user)
        await session.flush()
        staff = Staff(
            tenant_id=tenant.id,
            user_id=user.id,
            employee_number="PLATFORM-001",
            first_name="Platform",
            last_name="Administrator",
            employment_position="Platform Administrator",
        )
        session.add(staff)
        await session.flush()
        session.add(
            StaffRoleAssignment(
                tenant_id=tenant.id,
                staff_id=staff.id,
                role_id=role.id,
                assignment_type="PRIMARY",
                status="ACTIVE",
                assigned_by=user.id,
                approved_by=user.id,
                assignment_reason="Initial platform bootstrap",
            )
        )
        await session.commit()
        print(f"Created platform administrator {email}")


if __name__ == "__main__":
    asyncio.run(seed())
