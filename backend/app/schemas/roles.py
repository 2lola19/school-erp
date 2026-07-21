from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssignmentType = Literal["PRIMARY", "SECONDARY"]
AssignmentStatus = Literal["PENDING", "ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED"]


class RoleAssignmentCreate(BaseModel):
    role_id: UUID
    assignment_type: AssignmentType
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_temporary: bool = False
    scope: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=2000)
    delegated_by: UUID | None = None
    delegation_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> "RoleAssignmentCreate":
        if self.is_temporary and not self.ends_at:
            raise ValueError("Temporary assignments require an end date")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class RoleAssignmentUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    scope: dict[str, Any] | None = None
    reason: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> "RoleAssignmentUpdate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class RoleActionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class RoleAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    staff_id: UUID
    role_id: UUID
    assignment_type: AssignmentType
    status: AssignmentStatus
    starts_at: datetime | None
    ends_at: datetime | None
    is_temporary: bool
    scope: dict[str, Any]
    assigned_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None
    assignment_reason: str
    revoked_by: UUID | None
    revoked_at: datetime | None
    revocation_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionPreview(BaseModel):
    role_id: UUID
    assignment_type: AssignmentType
    proposed_status: AssignmentStatus
    permissions_gained: list[str]
    permissions_lost: list[str] = Field(default_factory=list)
    conflict_warnings: list[str] = Field(default_factory=list)
    approval_required: bool
    scope: dict[str, Any] = Field(default_factory=dict)


class EffectivePermissionsResponse(BaseModel):
    staff_id: UUID
    permission_version: int
    permissions: list[str]


class RoleHistoryResponse(BaseModel):
    assignments: list[RoleAssignmentResponse]


class RoleConflictResponse(BaseModel):
    role_id: UUID
    conflicting_role_id: UUID
    action: str
    reason: str


class StaffCreate(BaseModel):
    user_id: UUID
    employee_number: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    employment_position: str | None = Field(default=None, max_length=150)
    primary_role_id: UUID
    role_scope: dict[str, Any] = Field(default_factory=dict)
    role_reason: str = Field(min_length=3, max_length=2000)


class StaffResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    employee_number: str
    first_name: str
    last_name: str
    employment_position: str | None
    employment_status: str

    model_config = ConfigDict(from_attributes=True)
