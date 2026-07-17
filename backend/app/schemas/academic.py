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
