import os

perf_file = os.path.join("app", "api", "v1", "routers", "academic_performance.py")

with open(perf_file, "r", encoding="utf-8") as f:
    content = f.read()

attendance_code = """
import datetime
from app.models.core import Attendance

class AttendanceCreate(BaseModel):
    student_id: uuid.UUID
    classroom_id: uuid.UUID
    date: datetime.date
    status: str

class AttendanceResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    classroom_id: uuid.UUID
    date: datetime.date
    status: str
    
    class Config:
        from_attributes = True

@router.post("/attendance", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(payload: AttendanceCreate, db: AsyncSession = Depends(get_db)):
    student = (await db.execute(select(Student).where(Student.id == payload.student_id))).scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student target not found")
        
    new_attendance = Attendance(
        id=uuid.uuid4(),
        tenant_id=student.tenant_id,
        student_id=payload.student_id,
        classroom_id=payload.classroom_id,
        date=payload.date,
        status=payload.status
    )
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance
"""

if "mark_attendance" not in content:
    with open(perf_file, "a", encoding="utf-8") as f:
        f.write(attendance_code)
    print("[+] Attendance endpoints synthesized and bound to performance router.")
else:
    print("[*] Attendance endpoints already exist.")