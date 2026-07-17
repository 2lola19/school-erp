import os
import asyncio
from app.db.session import engine
from app.models.core import Base

target_file = "app/models/core.py"
models_code = """
class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
"""

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

if "class Classroom(Base):" not in content:
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\n" + models_code.strip() + "\n")
    print("[+] Relational models (Classroom, Enrollment) injected.")
else:
    print("[*] Relational models already exist.")

async def sync_db():
    print("[*] Synchronizing relational models with PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[+] Database synchronization complete. Junction tables instantiated.")

asyncio.run(sync_db())