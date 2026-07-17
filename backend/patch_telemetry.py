import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def instantiate_ledger():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    print("[*] Opening explicit database transaction for Telemetry Ledger...")
    
    try:
        async with engine.begin() as conn:
            # Command 1: Create Table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR NOT NULL,
                    entity_name VARCHAR NOT NULL,
                    entity_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # Command 2: Create Index
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs(tenant_id)"))
            
        print("[+] Telemetry Ledger mathematically guaranteed in PostgreSQL.")
    except Exception as e:
        print(f"[-] DDL Execution Failed: {e}")
    finally:
        await engine.dispose()

asyncio.run(instantiate_ledger())