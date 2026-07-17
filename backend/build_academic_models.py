import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 1. Inject Academic Models into Core Schema
target_file = "app/models/core.py"
models_code = """
from sqlalchemy import Date

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    employee_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Student(Base):
    __tablename__ = "students"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    admission_number = Column(String, index=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
"""

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

if "class Teacher(Base):" not in content:
    # Ensure Date import is present
    if "from sqlalchemy import" in content and "Date" not in content:
        content = content.replace("from sqlalchemy import Column", "from sqlalchemy import Column, Date")
    
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\n" + models_code.strip() + "\n")
    print("[+] Academic models (Teacher, Student) injected into core.py")
else:
    print("[*] Academic models already exist in core.py")

# 2. Force Postgres Table Instantiation (Zero Downtime Migration)
from app.core.config import settings
from app.db.session import engine
from app.models.core import Base

async def instantiate_tables():
    print("[*] Synchronizing models with PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[+] Database synchronization complete. Tables instantiated.")

asyncio.run(instantiate_tables())