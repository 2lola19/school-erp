import os

core_file = os.path.join("app", "models", "core.py")

with open(core_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Guarantee Float is imported for precise grading
if "Float" not in content:
    content = content.replace("from sqlalchemy import ", "from sqlalchemy import Float, ")

# 2. Define the new relational entities
new_models = """
class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Grade(Base):
    __tablename__ = 'grades'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey('subjects.id'), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey('classrooms.id'), nullable=True)
    term = Column(String, nullable=False)
    academic_year = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

# 3. Inject models if not already present
if "class Subject(Base):" not in content:
    content += new_models
    with open(core_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Subject and Grade models mathematically bound to core schema.")
else:
    print("[*] Academic models already exist in schema.")