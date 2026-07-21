"""Synchronize built-in role templates for every existing school tenant."""

import asyncio

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.core import Tenant
from app.services.role_templates import ensure_tenant_role_templates


async def sync() -> None:
    total_changes = 0
    async with AsyncSessionLocal() as session:
        tenants = list((await session.execute(select(Tenant))).scalars().all())
        for tenant in tenants:
            await session.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
                {"tenant_id": str(tenant.id)},
            )
            total_changes += await ensure_tenant_role_templates(session, tenant.id)
            await session.commit()
    print(f"Role template synchronization complete: {total_changes} changes")


if __name__ == "__main__":
    asyncio.run(sync())
