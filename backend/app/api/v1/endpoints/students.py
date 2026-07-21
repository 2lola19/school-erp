from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_rls_db, require_permissions
from app.models.core import AuditLog, Student
from app.schemas.auth import CurrentUser
from app.schemas.student import StudentCreate, StudentResponse

router = APIRouter()


@router.get("/", response_model=list[StudentResponse])
async def get_students(
    actor: Annotated[CurrentUser, Depends(require_permissions("students.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[Student]:
    result = await session.execute(
        select(Student).where(Student.tenant_id == actor.tenant_id)
    )
    return list(result.scalars().all())


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("students.create"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Student:
    existing = await session.scalar(
        select(Student).where(
            Student.tenant_id == actor.tenant_id,
            Student.admission_number == student_data.admission_number,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Admission number already exists")
    student = Student(tenant_id=actor.tenant_id, **student_data.model_dump())
    session.add(student)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=actor.tenant_id,
            user_id=actor.id,
            action="STUDENT_CREATED",
            entity_name="STUDENT",
            entity_id=str(student.id),
        )
    )
    await session.commit()
    await session.refresh(student)
    return student
