import os

# 1. Patch the Core Schema
core_file = os.path.join("app", "models", "core.py")
with open(core_file, "r", encoding="utf-8") as f:
    core_content = f.read()

new_model = """
class Enrollment(Base):
    __tablename__ = 'enrollments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey('students.id'), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey('classrooms.id'), nullable=False)
    academic_year = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
"""

if "class Enrollment(Base):" not in core_content:
    with open(core_file, "a", encoding="utf-8") as f:
        f.write(new_model)
    print("[+] Enrollment model mathematically bound to core schema.")
else:
    print("[*] Enrollment model already exists.")

# 2. Patch the Performance API
perf_file = os.path.join("app", "api", "v1", "routers", "academic_performance.py")
with open(perf_file, "r", encoding="utf-8") as f:
    api_content = f.read()

enrollment_code = """
from app.models.core import Enrollment

class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID
    classroom_id: uuid.UUID
    academic_year: str

class EnrollmentResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    classroom_id: uuid.UUID
    academic_year: str
    
    class Config:
        from_attributes = True

@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(payload: EnrollmentCreate, db: AsyncSession = Depends(get_db)):
    student = (await db.execute(select(Student).where(Student.id == payload.student_id))).scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student target not found")
        
    new_enrollment = Enrollment(
        id=uuid.uuid4(),
        tenant_id=student.tenant_id,
        student_id=payload.student_id,
        classroom_id=payload.classroom_id,
        academic_year=payload.academic_year
    )
    db.add(new_enrollment)
    await db.commit()
    await db.refresh(new_enrollment)
    return new_enrollment
"""

if "enroll_student" not in api_content:
    with open(perf_file, "a", encoding="utf-8") as f:
        f.write(enrollment_code)
    print("[+] Enrollment endpoints synthesized and bound to performance router.")
else:
    print("[*] Enrollment endpoints already exist.")