from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMResponse(BaseModel):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)


class DecisionAction(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    reason: str = Field(min_length=3, max_length=2000)


class FeeScheduleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    academic_session_id: UUID | None = None


class FeeScheduleResponse(FeeScheduleCreate, ORMResponse):
    is_active: bool


class InvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=2, max_length=50)
    student_id: UUID
    fee_schedule_id: UUID
    due_on: date | None = None


class InvoiceResponse(ORMResponse):
    invoice_number: str
    student_id: UUID
    fee_schedule_id: UUID
    amount: Decimal
    balance: Decimal
    status: Literal["OPEN", "PAID", "VOID"]
    due_on: date | None
    issued_by: UUID


class PaymentCreate(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reference: str = Field(min_length=2, max_length=100)


class PaymentResponse(PaymentCreate, ORMResponse):
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    received_by: UUID
    approved_by: UUID | None
    received_at: datetime
    approved_at: datetime | None


class RefundCreate(BaseModel):
    payment_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=2000)


class RefundResponse(RefundCreate, ORMResponse):
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    requested_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None


class HealthRecordUpsert(BaseModel):
    student_id: UUID
    allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    immunisations: list[str] = Field(default_factory=list)
    emergency_plan: str | None = Field(default=None, max_length=5000)


class HealthRecordResponse(HealthRecordUpsert, ORMResponse):
    updated_by: UUID


class HealthEncounterCreate(BaseModel):
    health_record_id: UUID
    occurred_at: datetime | None = None
    summary: str = Field(min_length=3, max_length=5000)
    treatment: str | None = Field(default=None, max_length=5000)
    referral: str | None = Field(default=None, max_length=2000)


class HealthEncounterResponse(ORMResponse):
    health_record_id: UUID
    occurred_at: datetime
    summary: str
    treatment: str | None
    referral: str | None
    recorded_by: UUID


class MedicalConsentCreate(BaseModel):
    student_id: UUID
    consent_type: str = Field(min_length=2, max_length=100)
    status: Literal["GRANTED", "DECLINED", "REVOKED"]
    valid_from: date
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "MedicalConsentCreate":
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must not be earlier than valid_from")
        return self


class MedicalConsentResponse(MedicalConsentCreate, ORMResponse):
    recorded_by: UUID


class EmergencyFlagCreate(BaseModel):
    student_id: UUID
    label: str = Field(min_length=2, max_length=150)
    instructions: str = Field(min_length=3, max_length=5000)


class EmergencyFlagResponse(EmergencyFlagCreate, ORMResponse):
    is_active: bool
    updated_by: UUID


class BreakGlassCreate(BaseModel):
    user_id: UUID
    student_id: UUID
    reason: str = Field(min_length=10, max_length=2000)
    expires_at: datetime


class BreakGlassResponse(BreakGlassCreate, ORMResponse):
    status: Literal["ACTIVE", "REVIEWED", "REVOKED"]
    granted_by: UUID
    reviewed_by: UUID | None
    reviewed_at: datetime | None


class CounsellingCaseCreate(BaseModel):
    student_id: UUID
    assigned_counsellor_id: UUID
    referral_reason: str = Field(min_length=3, max_length=5000)
    support_plan: str | None = Field(default=None, max_length=5000)


class CounsellingCaseResponse(CounsellingCaseCreate, ORMResponse):
    status: Literal["OPEN", "CLOSED"]
    created_by: UUID


class CounsellingEncounterCreate(BaseModel):
    case_id: UUID
    occurred_at: datetime | None = None
    confidential_notes: str = Field(min_length=3, max_length=10000)
    outcome: str | None = Field(default=None, max_length=5000)


class CounsellingEncounterResponse(ORMResponse):
    case_id: UUID
    occurred_at: datetime
    confidential_notes: str
    outcome: str | None
    recorded_by: UUID


class LibraryItemCreate(BaseModel):
    catalogue_code: str = Field(min_length=2, max_length=50)
    isbn: str | None = Field(default=None, max_length=30)
    title: str = Field(min_length=1, max_length=255)
    author: str | None = Field(default=None, max_length=255)
    total_copies: int = Field(ge=1)


class LibraryItemResponse(LibraryItemCreate, ORMResponse):
    available_copies: int


class LibraryLoanCreate(BaseModel):
    item_id: UUID
    student_id: UUID
    due_on: date


class LibraryLoanResponse(LibraryLoanCreate, ORMResponse):
    issued_at: datetime
    returned_at: datetime | None
    status: Literal["ISSUED", "RETURNED", "LOST"]
    issued_by: UUID


class TransportRouteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    pickup_points: list[str] = Field(min_length=1)
    capacity: int = Field(gt=0)


class TransportRouteResponse(TransportRouteCreate, ORMResponse):
    is_active: bool


class TransportAssignmentCreate(BaseModel):
    route_id: UUID
    student_id: UUID
    pickup_point: str = Field(min_length=2, max_length=255)


class TransportAssignmentResponse(TransportAssignmentCreate, ORMResponse):
    status: Literal["ACTIVE", "INACTIVE"]


class HostelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    gender_policy: str | None = Field(default=None, max_length=50)
    capacity: int = Field(gt=0)


class HostelResponse(HostelCreate, ORMResponse):
    is_active: bool


class HostelRoomCreate(BaseModel):
    hostel_id: UUID
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0)


class HostelRoomResponse(HostelRoomCreate, ORMResponse):
    pass


class HostelAssignmentCreate(BaseModel):
    room_id: UUID
    student_id: UUID
    starts_on: date
    ends_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "HostelAssignmentCreate":
        if self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must not be earlier than starts_on")
        return self


class HostelAssignmentResponse(HostelAssignmentCreate, ORMResponse):
    status: Literal["ACTIVE", "INACTIVE"]


class ActivityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: str = Field(min_length=2, max_length=100)
    lead_staff_id: UUID | None = None


class ActivityResponse(ActivityCreate, ORMResponse):
    status: Literal["ACTIVE", "INACTIVE"]


class ActivityEnrollmentCreate(BaseModel):
    activity_id: UUID
    student_id: UUID


class ActivityEnrollmentResponse(ActivityEnrollmentCreate, ORMResponse):
    status: Literal["ACTIVE", "WITHDRAWN"]


class ActivityAttendanceCreate(BaseModel):
    activity_id: UUID
    student_id: UUID
    date: date
    status: Literal["PRESENT", "ABSENT", "EXCUSED"]


class ActivityAttendanceResponse(ActivityAttendanceCreate, ORMResponse):
    recorded_by: UUID


class AchievementCreate(BaseModel):
    activity_id: UUID
    student_id: UUID
    title: str = Field(min_length=2, max_length=255)
    details: str | None = Field(default=None, max_length=5000)


class AchievementResponse(AchievementCreate, ORMResponse):
    status: Literal["SUBMITTED", "APPROVED", "REJECTED"]
    submitted_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None
