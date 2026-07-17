import os
import re

router_dir = os.path.join("app", "api", "v1", "routers")
perf_file = os.path.join(router_dir, "academic_performance.py")
main_file = os.path.join("app", "main.py")

router_code = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
from typing import List

from app.api.v1.dependencies import get_db
from app.models.core import Subject, Grade, Student, Tenant

router = APIRouter()

class SubjectCreate(BaseModel):
    name: str
    code: str

class SubjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    
    class Config:
        from_attributes = True

class GradeCreate(BaseModel):
    student_id: uuid.UUID
    subject_id: uuid.UUID
    term: str
    academic_year: str
    score: float

class GradeResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    score: float
    term: str
    academic_year: str
    
    class Config:
        from_attributes = True

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(payload: SubjectCreate, db: AsyncSession = Depends(get_db)):
    tenant = (await db.execute(select(Tenant))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Institution matrix missing")
        
    new_subject = Subject(id=uuid.uuid4(), tenant_id=tenant.id, name=payload.name, code=payload.code)
    db.add(new_subject)
    await db.commit()
    await db.refresh(new_subject)
    return new_subject

@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subject))
    return result.scalars().all()

@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def record_grade(payload: GradeCreate, db: AsyncSession = Depends(get_db)):
    student = (await db.execute(select(Student).where(Student.id == payload.student_id))).scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student target not found")
        
    subject = (await db.execute(select(Subject).where(Subject.id == payload.subject_id))).scalars().first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject target not found")
        
    new_grade = Grade(
        id=uuid.uuid4(),
        tenant_id=student.tenant_id,
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        term=payload.term,
        academic_year=payload.academic_year,
        score=payload.score
    )
    db.add(new_grade)
    await db.commit()
    await db.refresh(new_grade)
    return new_grade
"""

with open(perf_file, "w", encoding="utf-8") as f:
    f.write(router_code)

with open(main_file, "r", encoding="utf-8") as f:
    main_code = f.read()

# Execute strict substring injection for main.py imports and router inclusions
if "academic_performance" not in main_code:
    main_code = re.sub(
        r'from app\.api\.v1\.routers import dashboard',
        'from app.api.v1.routers import dashboard\\nfrom app.api.v1.routers import academic_performance',
        main_code
    )
    main_code = re.sub(
        r'app\.include_router\(dashboard\.router, prefix="/api/v1/dashboard", tags=\["dashboard"\]\)',
        'app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])\\napp.include_router(academic_performance.router, prefix="/api/v1/academic/performance", tags=["academic"])',
        main_code
    )
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_code)
    print("[+] Academic Performance router synthesized and bound to execution context.")
else:
    print("[*] Academic Performance router already registered in main.py.")