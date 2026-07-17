import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.core import Role, Permission, RolePermission

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Create the permission if missing
        p_res = await session.execute(select(Permission).where(Permission.name == "view_all_tenants"))
        perm = p_res.scalars().first()
        if not perm:
            perm = Permission(name="view_all_tenants", description="Can view all system tenants")
            session.add(perm)
            await session.commit()
            await session.refresh(perm)
            print("[+] Database Seeded: Created 'view_all_tenants' permission.")
        else:
            print("[*] Permission 'view_all_tenants' already exists.")

        # 2. Locate Super Admin
        r_res = await session.execute(select(Role).where(Role.name == "Super Admin"))
        role = r_res.scalars().first()
        if not role:
            print("[-] Critical Error: Super Admin role not found.")
            return

        # 3. Bind Permission to Role
        rp_res = await session.execute(
            select(RolePermission)
            .where(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id)
        )
        if not rp_res.scalars().first():
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
            await session.commit()
            print("[+] RBAC Matrix: 'view_all_tenants' securely bound to Super Admin.")
        else:
            print("[*] RBAC Matrix: Link already exists.")

if __name__ == "__main__":
    asyncio.run(seed())