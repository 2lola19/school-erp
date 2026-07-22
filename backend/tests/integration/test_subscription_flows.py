import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.core.feature_registry import FeatureCode
from app.db.session import AsyncSessionLocal
from app.models.core import Student, Tenant
from app.models.subscriptions import SubscriptionPlan, TenantSubscription
from app.services.entitlements import EntitlementService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="database-backed integration tests are opt-in",
    ),
]


async def test_subscription_rls_quota_and_expired_write_restriction() -> None:
    suffix = uuid4().hex[:10]
    async with AsyncSessionLocal() as session:
        starter = await session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == "STARTER"))
        tenant_a = Tenant(name=f"Subscription A {suffix}", domain=f"sub-a-{suffix}.test")
        tenant_b = Tenant(name=f"Subscription B {suffix}", domain=f"sub-b-{suffix}.test")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_a.id)})
        subscription_a = TenantSubscription(tenant_id=tenant_a.id, plan_id=starter.id, status="ACTIVE", is_current=True)
        session.add(subscription_a)
        session.add_all([Student(tenant_id=tenant_a.id, first_name="Quota", last_name=str(index), admission_number=f"{suffix}-{index}") for index in range(200)])
        await session.commit()

        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_b.id)})
        session.add(TenantSubscription(tenant_id=tenant_b.id, plan_id=starter.id, status="ACTIVE", is_current=True))
        await session.commit()
        role_name = f"rls_reader_{suffix}"
        session_user = await session.scalar(text("SELECT session_user"))
        await session.execute(text(f'CREATE ROLE "{role_name}" NOLOGIN'))
        await session.execute(text(f'GRANT "{role_name}" TO "{session_user}" WITH ADMIN OPTION'))
        await session.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role_name}"'))
        await session.execute(text(f'GRANT SELECT ON tenant_subscriptions TO "{role_name}"'))
        await session.commit()
        try:
            for tenant_id in (tenant_a.id, tenant_b.id):
                await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
                await session.execute(text(f'SET LOCAL ROLE "{role_name}"'))
                visible = await session.scalar(select(func.count()).select_from(TenantSubscription))
                assert visible == 1
                await session.commit()
        finally:
            await session.execute(text("RESET ROLE"))
            await session.execute(text(f'REVOKE SELECT ON tenant_subscriptions FROM "{role_name}"'))
            await session.execute(text(f'REVOKE USAGE ON SCHEMA public FROM "{role_name}"'))
            await session.execute(text(f'DROP ROLE IF EXISTS "{role_name}"'))
            await session.commit()

        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_a.id)})
        service = EntitlementService(session)
        with pytest.raises(HTTPException) as quota_error:
            await service.check_quota(tenant_a.id, FeatureCode.QUOTA_ACTIVE_STUDENTS)
        assert quota_error.value.status_code == 409
        assert quota_error.value.detail["code"] == "QUOTA_EXCEEDED"

        current = await session.scalar(select(TenantSubscription).where(TenantSubscription.id == subscription_a.id).with_for_update())
        current.status = "EXPIRED"
        current.entitlement_version += 1
        await session.commit()
        assert (await service.require_feature(tenant_a.id, FeatureCode.STUDENTS_MANAGE, write=False)).can_read
        with pytest.raises(HTTPException) as status_error:
            await service.require_feature(tenant_a.id, FeatureCode.STUDENTS_MANAGE, write=True)
        assert status_error.value.status_code == 403
        assert status_error.value.detail["code"] == "SUBSCRIPTION_EXPIRED"
