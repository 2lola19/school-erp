import os

seed_py = """
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.core import Tenant, Role, User, Permission

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
# Enforce expire_on_commit=False to prevent synchronous lazy loading
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def seed_system():
    async with AsyncSessionLocal() as session:
        try:
            system_tenant = Tenant(name="System Master", domain="system.local")
            session.add(system_tenant)
            await session.commit()
            
            perm_view_all = Permission(name="view_all_tenants", description="Super Admin access")
            session.add(perm_view_all)
            await session.commit()
            
            # Context injected utilizing the locally retained UUID
            await session.execute(text(f"SET LOCAL app.current_tenant = '{system_tenant.id}'"))
            
            super_admin_role = Role(tenant_id=system_tenant.id, name="Super Admin")
            session.add(super_admin_role)
            await session.commit()
            
            admin_user = User(
                tenant_id=system_tenant.id,
                role_id=super_admin_role.id,
                email="admin@system.local",
                password_hash=get_password_hash("SuperSecurePassword123!")
            )
            session.add(admin_user)
            await session.commit()
            
            print("Seed complete. Super Admin initialized.")
        except Exception as e:
            print(f"Seed failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(seed_system())
"""

with open("scripts/seed.py", "w", encoding="utf-8") as f:
    f.write(seed_py.strip() + "\n")

print("Seed script patched.")
