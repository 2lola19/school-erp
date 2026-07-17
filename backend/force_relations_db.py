import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def force_db_creation():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, isolation_level="AUTOCOMMIT")
    print("[*] Bypassing Alembic. Executing raw DDL commands...")
    
    # Raw SQL to guarantee table instantiation
    ddl = """
    CREATE TABLE IF NOT EXISTS classrooms (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name VARCHAR NOT NULL,
        teacher_id UUID REFERENCES teachers(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_classrooms_tenant_id ON classrooms(tenant_id);

    CREATE TABLE IF NOT EXISTS enrollments (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
        enrolled_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_enrollments_tenant_id ON enrollments(tenant_id);
    """
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text(ddl))
        print("[+] PostgreSQL confirms tables physically exist.")
    except Exception as e:
        print(f"[-] DDL Execution Failed: {e}")
    finally:
        await engine.dispose()

asyncio.run(force_db_creation())