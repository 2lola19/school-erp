import os

# 1. Build Student Schemas
os.makedirs("app/schemas", exist_ok=True)
schemas_code = """
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
import uuid

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    admission_number: str
    date_of_birth: Optional[date] = None

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)
"""
with open("app/schemas/student.py", "w", encoding="utf-8") as f:
    f.write(schemas_code.strip() + "\n")
print("[+] Student schemas generated.")

# 2. Build Student API Endpoints
os.makedirs("app/api/v1/endpoints", exist_ok=True)
endpoints_code = """
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
"""
with open("app/api/v1/endpoints/students.py", "w", encoding="utf-8") as f:
    f.write(endpoints_code.strip() + "\n")
print("[+] Student endpoints generated with mathematical RBAC binding.")

# 3. Register Router in API Gateway
api_file = "app/api/v1/api.py"
with open(api_file, "r", encoding="utf-8") as f:
    api_content = f.read()

# Add the import and router include if missing
if "from app.api.v1.endpoints import students" not in api_content:
    api_content = api_content.replace(
        "from app.api.v1.endpoints import auth", 
        "from app.api.v1.endpoints import auth, students"
    )
    api_content += '\napi_router.include_router(students.router, prefix="/students", tags=["Students"])\n'
    
    with open(api_file, "w", encoding="utf-8") as f:
        f.write(api_content)
    print("[+] Students router wired into main API gateway.")
else:
    print("[*] Students router already registered.")