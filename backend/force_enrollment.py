import os
import re

core_file = os.path.join("app", "models", "core.py")

with open(core_file, "r", encoding="utf-8") as f:
    content = f.read()

# Isolate the exact class definition to replace
old_class_pattern = r"class Enrollment\(Base\):.*?created_at = Column\(DateTime\(timezone=True\), server_default=func\.now\(\)\)"
new_class = """class Enrollment(Base):
    __tablename__ = 'enrollments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey('classrooms.id'), nullable=False)
    academic_year = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())"""

if "academic_year = Column(String" not in content:
    content = re.sub(old_class_pattern, new_class, content, flags=re.DOTALL)
    with open(core_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Core model successfully overwritten to include academic_year.")
else:
    print("[*] Core model already possesses academic_year.")