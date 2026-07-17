import os

raw_sql_seed = """import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def force_seed():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    print("[*] Initiating absolute raw SQL injection...")
    
    async with engine.begin() as conn:
        # 1. Guarantee Tenant Exists
        res = await conn.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant_id = res.scalar()
        if not tenant_id:
            tenant_id = uuid.uuid4()
            await conn.execute(
                text("INSERT INTO tenants (id, name) VALUES (:id, 'System Foundation')"),
                {"id": tenant_id}
            )
            print(f"[*] Injected root tenant: {tenant_id}")
            
        # 2. Guarantee SUPERADMIN Role Exists
        res = await conn.execute(text("SELECT id FROM roles WHERE name = 'SUPERADMIN' LIMIT 1"))
        role_id = res.scalar()
        if not role_id:
            role_id = uuid.uuid4()
            await conn.execute(
                text("INSERT INTO roles (id, name, tenant_id) VALUES (:id, 'SUPERADMIN', :tid)"),
                {"id": role_id, "tid": tenant_id}
            )
            print(f"[*] Injected SUPERADMIN role: {role_id}")
            
        # 3. Guarantee User Exists and is Bound
        hashed_pwd = pwd_context.hash('admin123')
        res = await conn.execute(text("SELECT id FROM users WHERE email = 'admin@school.com'"))
        user_id = res.scalar()
        
        if user_id:
            await conn.execute(
                text("UPDATE users SET password_hash = :pwd, role_id = :rid, tenant_id = :tid, is_active = true WHERE id = :uid"),
                {"pwd": hashed_pwd, "rid": role_id, "tid": tenant_id, "uid": user_id}
            )
            print("[*] Updated existing admin@school.com.")
        else:
            user_id = uuid.uuid4()
            await conn.execute(
                text("INSERT INTO users (id, email, password_hash, is_active, role_id, tenant_id) VALUES (:id, 'admin@school.com', :pwd, true, :rid, :tid)"),
                {"id": user_id, "pwd": hashed_pwd, "rid": role_id, "tid": tenant_id}
            )
            print("[*] Injected admin@school.com.")
            
    print("[+] Relational dependency chain satisfied. Local Superadmin guaranteed.")
    await engine.dispose()

asyncio.run(force_seed())
"""

with open("local_seed.py", "w", encoding="utf-8") as f:
    f.write(raw_sql_seed)
print("[+] Raw SQL seed script synthesized.")