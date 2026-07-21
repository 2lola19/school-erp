from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeacherCreate(BaseModel):
    user_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    employee_id: str = Field(min_length=1, max_length=50)
    primary_role_id: UUID
    role_scope: dict = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=2000)


class TeacherResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    staff_id: UUID | None
    first_name: str
    last_name: str
    email: EmailStr
    employee_id: str

    model_config = ConfigDict(from_attributes=True)


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    teacher_id: UUID | None = None


class ClassroomResponse(ClassroomCreate):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=30)


class SubjectResponse(SubjectCreate):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class GradeCreate(BaseModel):
    student_id: UUID
    subject_id: UUID
    classroom_id: UUID
    term: str = Field(min_length=1, max_length=30)
    academic_year: str = Field(min_length=4, max_length=20)
    score: float = Field(ge=0, le=100)


class GradeResponse(GradeCreate):
    id: UUID
    tenant_id: UUID
    workflow_status: Literal["DRAFT", "SUBMITTED", "APPROVED"]
    entered_by: UUID
    approved_by: UUID | None

    model_config = ConfigDict(from_attributes=True)
