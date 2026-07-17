import os

# 1. Build Academic Schemas
schemas_code = """
from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class TeacherBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    employee_id: str

class TeacherCreate(TeacherBase):
    pass

class TeacherResponse(TeacherBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class ClassroomBase(BaseModel):
    name: str
    teacher_id: Optional[uuid.UUID] = None

class ClassroomCreate(ClassroomBase):
    pass

class ClassroomResponse(ClassroomBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)
"""
with open("app/schemas/academic.py", "w", encoding="utf-8") as f:
    f.write(schemas_code.strip() + "\n")
print("[+] Academic schemas generated.")

# 2. Build Academic Endpoints with Foreign Key Defense
endpoints_code = """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
import uuid

from app.api.v1.dependencies import get_db, get_current_user_payload
from app.schemas.auth import TokenPayload
from app.schemas.academic import TeacherCreate, TeacherResponse, ClassroomCreate, ClassroomResponse
from app.models.core import Teacher, Classroom, User

router = APIRouter()

async def get_tenant_id(payload: TokenPayload, session: AsyncSession) -> uuid.UUID:
    try:
        user_id = uuid.UUID(payload.sub)
        query = select(User).where(User.id == user_id)
    except ValueError:
        query = select(User).where(User.email == payload.sub)
        
    user = (await session.execute(query)).scalars().first()
    if not user or not user.tenant_id:
        raise HTTPException(status_code=403, detail="Unbound users cannot manipulate local academic data.")
    return user.tenant_id

@router.post("/teachers/", response_model=TeacherResponse)
async def create_teacher(
    data: TeacherCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    tenant = await get_tenant_id(payload, session)
    new_teacher = Teacher(tenant_id=tenant, **data.model_dump())
    session.add(new_teacher)
    await session.commit()
    await session.refresh(new_teacher)
    return new_teacher

@router.post("/classrooms/", response_model=ClassroomResponse)
async def create_classroom(
    data: ClassroomCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    tenant = await get_tenant_id(payload, session)
    
    # Mathematical RBAC Defense: Prevent cross-tenant teacher assignment
    if data.teacher_id:
        teacher_query = await session.execute(
            select(Teacher).where(Teacher.id == data.teacher_id, Teacher.tenant_id == tenant)
        )
        if not teacher_query.scalars().first():
            raise HTTPException(status_code=400, detail="Foreign Key Violation: Teacher not found in this institution.")

    new_class = Classroom(tenant_id=tenant, **data.model_dump())
    session.add(new_class)
    await session.commit()
    await session.refresh(new_class)
    return new_class
"""
with open("app/api/v1/endpoints/academic.py", "w", encoding="utf-8") as f:
    f.write(endpoints_code.strip() + "\n")
print("[+] Relational endpoints generated with cross-tenant mutation defense.")

# 3. Dynamically Wire the Router
def wire_router():
    target_file = "app/api/v1/__init__.py"
    if os.path.exists(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        if "academic.router" in content:
            print("[*] Academic router already registered.")
            return

        if "from app.api.v1.endpoints import" in content:
            content = content.replace(
                "from app.api.v1.endpoints import", 
                "from app.api.v1.endpoints import academic,"
            )
            content += '\napi_router.include_router(academic.router, prefix="/academic", tags=["Academic Operations"])\n'
            
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)
            print("[+] Academic router wired into API Gateway.")
            return
    print("[-] Critical: Could not locate app/api/v1/__init__.py to inject router.")

wire_router()