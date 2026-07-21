import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base, TenantBase, TimestampMixin, utcnow


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)


class SchoolProfile(TenantBase):
    __tablename__ = "school_profiles"

    school_name: Mapped[str] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    principal_name: Mapped[str | None] = mapped_column(String(255))
    motto: Mapped[str | None] = mapped_column(String(255))
    brand_color: Mapped[str | None] = mapped_column(String(50))


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Role(TenantBase):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_role_name"),
        UniqueConstraint("tenant_id", "code", name="uq_tenant_role_code"),
        CheckConstraint(
            "role_category IN ('PLATFORM','MANAGEMENT','ACADEMIC','FINANCE','HEALTH',"
            "'ADMINISTRATION','STUDENT_LIFE','SUPPORT')",
            name="ck_role_category",
        ),
    )

    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    role_category: Mapped[str] = mapped_column(String(30), default="SUPPORT")
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RolePermission(TenantBase):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), index=True
    )


class PermissionBundle(TenantBase):
    __tablename__ = "permission_bundles"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_permission_bundle_code"),)

    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PermissionBundlePermission(TenantBase):
    __tablename__ = "permission_bundle_permissions"
    __table_args__ = (UniqueConstraint("bundle_id", "permission_id", name="uq_bundle_permission"),)

    bundle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permission_bundles.id", ondelete="CASCADE"))
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"))


class RolePermissionBundle(TenantBase):
    __tablename__ = "role_permission_bundles"
    __table_args__ = (UniqueConstraint("role_id", "bundle_id", name="uq_role_permission_bundle"),)

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"))
    bundle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permission_bundles.id", ondelete="CASCADE"))


class User(TenantBase):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
    )

    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permission_version: Mapped[int] = mapped_column(Integer, default=1)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )


class UserPermission(TenantBase):
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", name="uq_user_permission"),
        CheckConstraint("effect IN ('ALLOW','DENY')", name="ck_user_permission_effect"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), index=True
    )
    effect: Mapped[str] = mapped_column(String(5), default="ALLOW")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Staff(TenantBase):
    __tablename__ = "staff"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_staff_user"),
        UniqueConstraint("tenant_id", "employee_number", name="uq_staff_employee_number"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    employee_number: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    employment_position: Mapped[str | None] = mapped_column(String(150))
    employment_status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class StaffRoleAssignment(TenantBase):
    __tablename__ = "staff_role_assignments"
    __table_args__ = (
        CheckConstraint(
            "assignment_type IN ('PRIMARY','SECONDARY')",
            name="ck_staff_role_assignment_type",
        ),
        CheckConstraint(
            "status IN ('PENDING','ACTIVE','SUSPENDED','EXPIRED','REVOKED')",
            name="ck_staff_role_assignment_status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="ck_staff_role_assignment_dates",
        ),
        Index(
            "uq_staff_active_primary_role",
            "tenant_id",
            "staff_id",
            unique=True,
            postgresql_where=text("assignment_type = 'PRIMARY' AND status = 'ACTIVE'"),
        ),
        Index(
            "uq_staff_active_role_assignment",
            "tenant_id",
            "staff_id",
            "role_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE','PENDING')"),
        ),
    )

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), index=True
    )
    assignment_type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_temporary: Mapped[bool] = mapped_column(Boolean, default=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assigned_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_reason: Mapped[str] = mapped_column(Text)
    delegated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    delegation_reason: Mapped[str | None] = mapped_column(Text)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class RoleConflict(TenantBase):
    __tablename__ = "role_conflicts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_id", "conflicting_role_id", name="uq_role_conflict"),
        CheckConstraint("action IN ('WARN','REQUIRE_APPROVAL','BLOCK')", name="ck_role_conflict_action"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    conflicting_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    conflict_level: Mapped[str] = mapped_column(String(30), default="HIGH")
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)


class RoleDelegationRule(TenantBase):
    __tablename__ = "role_delegation_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "assigner_role_id", "assignable_role_id", name="uq_role_delegation"),
    )

    assigner_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    assignable_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    maximum_scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Teacher(TenantBase):
    __tablename__ = "teachers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_teacher_email"),
        UniqueConstraint("tenant_id", "employee_id", name="uq_teacher_employee_id"),
    )

    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    employee_id: Mapped[str] = mapped_column(String(50))


class Student(TenantBase):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_student_admission_number"),
    )

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    admission_number: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[date | None] = mapped_column(Date)


class Classroom(TenantBase):
    __tablename__ = "classrooms"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_classroom_name"),)

    name: Mapped[str] = mapped_column(String(100))
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL")
    )


class Enrollment(TenantBase):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "classroom_id", name="uq_enrollment"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"))
    classroom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classrooms.id"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subject(TenantBase):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_subject_code"),)

    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(30))


class Grade(TenantBase):
    __tablename__ = "grades"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"))
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id"))
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("classrooms.id"))
    term: Mapped[str] = mapped_column(String(30))
    academic_year: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    workflow_status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    entered_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class Attendance(TenantBase):
    __tablename__ = "attendance"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"))
    classroom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classrooms.id"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))


class AuditLog(TenantBase):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_name: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)
    old_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    new_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    device: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
