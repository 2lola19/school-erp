from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.core import User, Classroom, Enrollment, Student

router = APIRouter()

class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID
    classroom_id: uuid.UUID

class EnrollmentResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    classroom_id: uuid.UUID
    enrolled_at: datetime
    
    class Config:
        orm_mode = True

@router.post("/", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(
    payload: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify Classroom exists and belongs to tenant
    stmt = select(Classroom).where(
        Classroom.id == payload.classroom_id,
        Classroom.tenant_id == current_user.tenant_id
    )
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Classroom not found")

    # 2. Verify Student exists in the dedicated students table
    stmt_student = select(Student).where(
        Student.id == payload.student_id,
        Student.tenant_id == current_user.tenant_id
    )
    result_student = await db.execute(stmt_student)
    if not result_student.scalars().first():
        raise HTTPException(status_code=404, detail="Student not found")

    # 3. Check for existing exact enrollment
    stmt_existing = select(Enrollment).where(
        Enrollment.student_id == payload.student_id,
        Enrollment.classroom_id == payload.classroom_id
    )
    result_existing = await db.execute(stmt_existing)
    if result_existing.scalars().first():
        raise HTTPException(status_code=400, detail="Student is already enrolled in this classroom")

    # 4. Execute Relational Binding
    new_enrollment = Enrollment(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        student_id=payload.student_id,
        classroom_id=payload.classroom_id
    )
    db.add(new_enrollment)
    await db.commit()
    await db.refresh(new_enrollment)
    
    return new_enrollment
