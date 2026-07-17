import os
import asyncio
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.core import Role, Permission, RolePermission

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def link_permissions():
    async with AsyncSessionLocal() as session:
        try:
            r_result = await session.execute(select(Role).where(Role.name == 'Super Admin'))
            role = r_result.scalars().first()
            
            p_result = await session.execute(select(Permission).where(Permission.name == 'view_all_tenants'))
            perm = p_result.scalars().first()

            if role and perm:
                rp_result = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id
                    )
                )
                if not rp_result.scalars().first():
                    session.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    await session.commit()
                    print("[+] RBAC Matrix: 'view_all_tenants' linked to Super Admin.")
                else:
                    print("[*] RBAC Matrix: Permission already linked.")
        except Exception as e:
            print(f"[-] Database Error: {e}")

def patch_jwt_generator():
    sec_path = "app/core/security.py"
    with open(sec_path, "r", encoding="utf-8") as f:
        sec = f.read()
    if "permissions: list" not in sec:
        sec = sec.replace("role: str, expires", "role: str, permissions: list[str], expires")
        sec = sec.replace('"role": role}', '"role": role, "permissions": permissions}')
        with open(sec_path, "w", encoding="utf-8") as f:
            f.write(sec)

    auth_path = "app/services/auth_service.py"
    with open(auth_path, "r", encoding="utf-8") as f:
        auth = f.read()
    if "permissions=permissions" not in auth:
        auth = auth.replace("expires_delta=access_expires", "permissions=permissions, expires_delta=access_expires")
        auth = auth.replace("expires_delta=refresh_expires", "permissions=permissions, expires_delta=refresh_expires")
        with open(auth_path, "w", encoding="utf-8") as f:
            f.write(auth)
    print("[+] JWT Generator patched to include permissions payload.")

if __name__ == "__main__":
    patch_jwt_generator()
    asyncio.run(link_permissions())