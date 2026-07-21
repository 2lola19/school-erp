from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class AcademicSessionCreate(BaseModel):
    name: str = Field(min_length=4, max_length=30)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicSessionCreate":
        if self.ends_on <= self.starts_on:
            raise ValueError("ends_on must be later than starts_on")
        return self


class AcademicSessionResponse(AcademicSessionCreate):
    id: UUID
    tenant_id: UUID
    status: Literal["PLANNED", "ACTIVE", "CLOSED"]

    model_config = ConfigDict(from_attributes=True)


class AcademicTermCreate(BaseModel):
    session_id: UUID
    name: str = Field(min_length=2, max_length=30)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicTermCreate":
        if self.ends_on <= self.starts_on:
            raise ValueError("ends_on must be later than starts_on")
        return self


class AcademicTermResponse(AcademicTermCreate):
    id: UUID
    tenant_id: UUID
    status: Literal["PLANNED", "ACTIVE", "CLOSED"]

    model_config = ConfigDict(from_attributes=True)


class GuardianCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    relationship: str = Field(min_length=2, max_length=50)


class ApplicantCreate(BaseModel):
    application_number: str = Field(min_length=2, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    guardian: GuardianCreate


class ApplicantResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    application_number: str
    first_name: str
    last_name: str
    date_of_birth: date | None
    guardian_id: UUID | None
    guardian_relationship: str
    status: Literal["DRAFT", "SUBMITTED", "ADMITTED", "REJECTED"]
    admitted_student_id: UUID | None
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    decision_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class ApplicantDecision(BaseModel):
    decision: Literal["ADMIT", "REJECT"]
    reason: str = Field(min_length=3, max_length=2000)
    admission_number: str | None = Field(default=None, max_length=50)
    classroom_id: UUID | None = None

    @model_validator(mode="after")
    def require_admission_fields(self) -> "ApplicantDecision":
        if self.decision == "ADMIT" and not self.admission_number:
            raise ValueError("admission_number is required when admitting an applicant")
        return self


class AttendanceMark(BaseModel):
    student_id: UUID
    classroom_id: UUID
    date: date
    status: Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]


class AttendanceCorrection(BaseModel):
    status: Literal["PRESENT", "ABSENT", "LATE", "EXCUSED"]
    reason: str = Field(min_length=3, max_length=2000)


class WorkflowAction(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class AttendanceResponse(AttendanceMark):
    id: UUID
    tenant_id: UUID
    workflow_status: Literal["DRAFT", "SUBMITTED", "APPROVED"]
    recorded_by: UUID | None
    approved_by: UUID | None
    correction_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class TimetableEntryCreate(BaseModel):
    term_id: UUID
    classroom_id: UUID
    subject_id: UUID
    teacher_id: UUID
    weekday: int = Field(ge=1, le=7)
    period_label: str = Field(min_length=1, max_length=30)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def validate_times(self) -> "TimetableEntryCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class TimetableEntryResponse(TimetableEntryCreate):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ExamCycleCreate(BaseModel):
    term_id: UUID
    name: str = Field(min_length=2, max_length=100)
    opens_at: datetime | None = None
    closes_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ExamCycleCreate":
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValueError("closes_at must be later than opens_at")
        return self


class ExamCycleAction(BaseModel):
    action: Literal["OPEN", "CLOSE", "PUBLISH"]
    reason: str = Field(min_length=3, max_length=2000)


class ExamCycleResponse(ExamCycleCreate):
    id: UUID
    tenant_id: UUID
    status: Literal["DRAFT", "OPEN", "CLOSED", "PUBLISHED"]
    published_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AssessmentComponentCreate(BaseModel):
    exam_cycle_id: UUID
    classroom_id: UUID
    subject_id: UUID
    name: str = Field(min_length=1, max_length=100)
    maximum_score: float = Field(gt=0)
    weight: float = Field(gt=0, le=100)


class AssessmentComponentResponse(AssessmentComponentCreate):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ReportCardGenerate(BaseModel):
    student_id: UUID
    term_id: UUID
    classroom_id: UUID
    remarks: str | None = Field(default=None, max_length=2000)


class ReportCardEntryResponse(BaseModel):
    subject_id: UUID
    score: float
    letter_grade: str
    remark: str | None

    model_config = ConfigDict(from_attributes=True)


class ReportCardResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    student_id: UUID
    term_id: UUID
    classroom_id: UUID
    status: Literal["DRAFT", "APPROVED", "PUBLISHED"]
    generated_by: UUID
    approved_by: UUID | None
    published_at: datetime | None
    remarks: str | None
    entries: list[ReportCardEntryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
