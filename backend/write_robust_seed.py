import os

robust_seed = """
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.core import Tenant, Role, User, Permission

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def seed_system():
    async with AsyncSessionLocal() as session:
        try:
            # 1. Check or Create Tenant
            result = await session.execute(select(Tenant).where(Tenant.domain == 'system.local'))
            system_tenant = result.scalars().first()
            if not system_tenant:
                system_tenant = Tenant(name="System Master", domain="system.local")
                session.add(system_tenant)
                await session.commit()
                print("[*] Created System Tenant.")
            else:
                print("[*] System Tenant exists.")

            # 2. Check or Create Global Permission
            result = await session.execute(select(Permission).where(Permission.name == 'view_all_tenants'))
            perm_view_all = result.scalars().first()
            if not perm_view_all:
                perm_view_all = Permission(name="view_all_tenants", description="Super Admin access")
                session.add(perm_view_all)
                await session.commit()
                print("[*] Created Global Permission.")
            else:
                print("[*] Global Permission exists.")

            # 3. Inject Tenant Context for RLS
            await session.execute(text(f"SET LOCAL app.current_tenant = '{system_tenant.id}'"))

            # 4. Check or Create Role
            result = await session.execute(select(Role).where(Role.tenant_id == system_tenant.id, Role.name == 'Super Admin'))
            super_admin_role = result.scalars().first()
            if not super_admin_role:
                super_admin_role = Role(tenant_id=system_tenant.id, name="Super Admin")
                session.add(super_admin_role)
                await session.commit()
                print("[*] Created Super Admin Role.")
            else:
                print("[*] Super Admin Role exists.")

            # 5. Check or Create User
            result = await session.execute(select(User).where(User.tenant_id == system_tenant.id, User.email == 'admin@system.local'))
            admin_user = result.scalars().first()
            if not admin_user:
                admin_user = User(
                    tenant_id=system_tenant.id,
                    role_id=super_admin_role.id,
                    email="admin@system.local",
                    password_hash=get_password_hash("SuperSecurePassword123!")
                )
                session.add(admin_user)
                await session.commit()
                print("[*] Created Super Admin User.")
            else:
                print("[*] Super Admin User exists.")
                
            print("[+] Seed complete. System initialized successfully.")
        except Exception as e:
            print(f"[-] Seed failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(seed_system())
"""

with open("scripts/seed.py", "w", encoding="utf-8") as f:
    f.write(robust_seed.strip() + "\n")

print("[+] Idempotent seed script written to scripts/seed.py")