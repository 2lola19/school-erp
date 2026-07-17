import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

# 1. Inject Python ORM Model
target_file = "app/models/core.py"
model_code = """
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String, nullable=False)
    entity_name = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
"""

if os.path.exists(target_file):
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()
    if "class AuditLog(Base):" not in content:
        with open(target_file, "a", encoding="utf-8") as f:
            f.write("\n" + model_code.strip() + "\n")
        print("[+] AuditLog model injected into ORM.")
    else:
        print("[*] AuditLog model already exists.")

# 2. Force DDL Execution
async def instantiate_ledger():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    print("[*] Opening explicit database transaction for Telemetry Ledger...")
    
    ddl = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY,
        tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR NOT NULL,
        entity_name VARCHAR NOT NULL,
        entity_id VARCHAR NOT NULL,
        timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs(tenant_id);
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text(ddl))
        print("[+] Telemetry Ledger mathematically guaranteed in PostgreSQL.")
    except Exception as e:
        print(f"[-] DDL Execution Failed: {e}")
    finally:
        await engine.dispose()

asyncio.run(instantiate_ledger())