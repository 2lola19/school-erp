from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
import uuid

from app.api.v1.dependencies import get_db, get_current_user_payload
from app.schemas.auth import TokenPayload
from app.schemas.student import StudentCreate, StudentResponse
from app.models.core import Student, User

router = APIRouter()

async def get_current_tenant_id(
    payload: TokenPayload, 
    session: AsyncSession
) -> uuid.UUID:
    # Safely resolve the user ID whether the JWT sub is an email or a UUID
    try:
        user_id = uuid.UUID(payload.sub)
        query = select(User).where(User.id == user_id)
    except ValueError:
        query = select(User).where(User.email == payload.sub)
        
    user = (await session.execute(query)).scalars().first()
    
    if not user or not user.tenant_id:
        raise HTTPException(status_code=403, detail="Action forbidden: User is not bound to a local institution.")
        
    return user.tenant_id

@router.get("/", response_model=List[StudentResponse])
async def get_students(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    target_tenant = await get_current_tenant_id(payload, session)
    
    # Strictly scope query to the authenticated user's tenant
    result = await session.execute(select(Student).where(Student.tenant_id == target_tenant))
    return result.scalars().all()

@router.post("/", response_model=StudentResponse)
async def create_student(
    student_data: StudentCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    target_tenant = await get_current_tenant_id(payload, session)
    
    # Enforce unique admission number within the SAME tenant
    existing = await session.execute(
        select(Student).where(
            Student.tenant_id == target_tenant,
            Student.admission_number == student_data.admission_number
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Admission number already in use at this institution.")
        
    new_student = Student(
        tenant_id=target_tenant,
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        admission_number=student_data.admission_number,
        date_of_birth=student_data.date_of_birth
    )
    session.add(new_student)
    await session.commit()
    await session.refresh(new_student)
    
    return new_student
