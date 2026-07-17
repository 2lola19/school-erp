import os

core_file = os.path.join("app", "models", "core.py")

with open(core_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Guarantee Date is imported for temporal tracking
if " Date," not in content and " Date " not in content:
    content = content.replace("from sqlalchemy import ", "from sqlalchemy import Date, ")

# 2. Define the relational entity
new_model = """
class Attendance(Base):
    __tablename__ = 'attendance'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey('classrooms.id'), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

# 3. Inject model if not already present
if "class Attendance(Base):" not in content:
    content += new_model
    with open(core_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Attendance model mathematically bound to core schema.")
else:
    print("[*] Attendance model already exists in schema.")