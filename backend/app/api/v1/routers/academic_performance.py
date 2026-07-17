from fastapi import APIRouter, Depends, HTTPException, status
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

class TranscriptItem(BaseModel):
    id: uuid.UUID
    subject_name: str
    subject_code: str
    score: float
    term: str
    academic_year: str

@router.get("/transcripts/{student_id}", response_model=List[TranscriptItem])
async def get_student_transcript(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Grade, Subject)
        .join(Subject, Grade.subject_id == Subject.id)
        .where(Grade.student_id == student_id)
        .order_by(Grade.academic_year.desc(), Grade.term.desc(), Subject.name.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": grade.id,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "score": grade.score,
            "term": grade.term,
            "academic_year": grade.academic_year
        }
        for grade, subject in rows
    ]

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
