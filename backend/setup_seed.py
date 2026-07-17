import os

security_py = """
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], tenant_id: str, role: str, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"exp": expire, "sub": str(subject), "tenant_id": tenant_id, "role": role}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
"""

seed_py = """
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.core import Tenant, Role, User, Permission

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
AsyncSessionLocal = async_sessionmaker(bind=engine)

async def seed_system():
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create System Tenant (RLS bypass not needed for base tenants table)
            system_tenant = Tenant(name="System Master", domain="system.local")
            session.add(system_tenant)
            await session.commit()
            await session.refresh(system_tenant)
            
            # 2. Create Global Permissions
            perm_view_all = Permission(name="view_all_tenants", description="Super Admin access")
            session.add(perm_view_all)
            await session.commit()
            
            # 3. Inject Tenant Context (Bypass RLS constraint for child tables)
            await session.execute(text(f"SET LOCAL app.current_tenant = '{system_tenant.id}'"))
            
            # 4. Create Tenant Role
            super_admin_role = Role(tenant_id=system_tenant.id, name="Super Admin")
            session.add(super_admin_role)
            await session.commit()
            await session.refresh(super_admin_role)
            
            # 5. Create Tenant User
            admin_user = User(
                tenant_id=system_tenant.id,
                role_id=super_admin_role.id,
                email="admin@system.local",
                password_hash=get_password_hash("SuperSecurePassword123!")
            )
            session.add(admin_user)
            await session.commit()
            
            print("✅ Seed complete. Super Admin initialized.")
        except Exception as e:
            print(f"❌ Seed failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(seed_system())
"""

files = {
    "app/core/security.py": security_py,
    "scripts/seed.py": seed_py
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

print("[*] Security and Seed files written.")
print("[*] Executing database seed...")
os.system("python scripts/seed.py")
