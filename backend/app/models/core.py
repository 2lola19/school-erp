import uuid
from datetime import date, datetime, time
from decimal import Decimal
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
    Numeric,
    String,
    Text,
    Time,
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
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "classroom_id", "date", name="uq_daily_attendance"
        ),
        CheckConstraint(
            "status IN ('PRESENT','ABSENT','LATE','EXCUSED')",
            name="ck_attendance_status",
        ),
        CheckConstraint(
            "workflow_status IN ('DRAFT','SUBMITTED','APPROVED')",
            name="ck_attendance_workflow_status",
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"))
    classroom_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classrooms.id"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    workflow_status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correction_reason: Mapped[str | None] = mapped_column(Text)


class AcademicSession(TenantBase):
    __tablename__ = "academic_sessions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_academic_session_name"),
        CheckConstraint(
            "status IN ('PLANNED','ACTIVE','CLOSED')", name="ck_academic_session_status"
        ),
        CheckConstraint("ends_on > starts_on", name="ck_academic_session_dates"),
    )

    name: Mapped[str] = mapped_column(String(30))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED")


class AcademicTerm(TenantBase):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "session_id", "name", name="uq_academic_term_name"),
        CheckConstraint(
            "status IN ('PLANNED','ACTIVE','CLOSED')", name="ck_academic_term_status"
        ),
        CheckConstraint("ends_on > starts_on", name="ck_academic_term_dates"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_sessions.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(30))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED")


class Guardian(TenantBase):
    __tablename__ = "guardians"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_guardian_email"),)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))


class StudentGuardian(TenantBase):
    __tablename__ = "student_guardians"
    __table_args__ = (
        UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    guardian_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guardians.id", ondelete="CASCADE")
    )
    relationship: Mapped[str] = mapped_column(String(50))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Applicant(TenantBase):
    __tablename__ = "applicants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "application_number", name="uq_application_number"),
        CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','ADMITTED','REJECTED')",
            name="ck_applicant_status",
        ),
    )

    application_number: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guardians.id", ondelete="SET NULL")
    )
    guardian_relationship: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")
    admitted_student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)


class TimetableEntry(TenantBase):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "term_id",
            "classroom_id",
            "weekday",
            "period_label",
            name="uq_class_timetable_slot",
        ),
        UniqueConstraint(
            "tenant_id",
            "term_id",
            "teacher_id",
            "weekday",
            "period_label",
            name="uq_teacher_timetable_slot",
        ),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_timetable_weekday"),
        CheckConstraint("ends_at > starts_at", name="ck_timetable_times"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_terms.id", ondelete="CASCADE")
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE")
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE")
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(Integer)
    period_label: Mapped[str] = mapped_column(String(30))
    starts_at: Mapped[time] = mapped_column(Time)
    ends_at: Mapped[time] = mapped_column(Time)


class ExamCycle(TenantBase):
    __tablename__ = "exam_cycles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "term_id", "name", name="uq_exam_cycle_name"),
        CheckConstraint(
            "status IN ('DRAFT','OPEN','CLOSED','PUBLISHED')",
            name="ck_exam_cycle_status",
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_terms.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentComponent(TenantBase):
    __tablename__ = "assessment_components"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "exam_cycle_id",
            "classroom_id",
            "subject_id",
            "name",
            name="uq_assessment_component",
        ),
        CheckConstraint("maximum_score > 0", name="ck_assessment_maximum_score"),
        CheckConstraint("weight > 0 AND weight <= 100", name="ck_assessment_weight"),
    )

    exam_cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_cycles.id", ondelete="CASCADE")
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE")
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    maximum_score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)


class ReportCard(TenantBase):
    __tablename__ = "report_cards"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "term_id", name="uq_student_report_card"),
        CheckConstraint(
            "status IN ('DRAFT','APPROVED','PUBLISHED')", name="ck_report_card_status"
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_terms.id", ondelete="CASCADE")
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)


class ReportCardEntry(TenantBase):
    __tablename__ = "report_card_entries"
    __table_args__ = (
        UniqueConstraint("report_card_id", "subject_id", name="uq_report_card_subject"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_report_card_score"),
    )

    report_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_cards.id", ondelete="CASCADE")
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE")
    )
    score: Mapped[float] = mapped_column(Float)
    letter_grade: Mapped[str] = mapped_column(String(5))
    remark: Mapped[str | None] = mapped_column(Text)


class FeeSchedule(TenantBase):
    __tablename__ = "fee_schedules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_fee_schedule_name"),
        CheckConstraint("amount > 0", name="ck_fee_schedule_amount"),
    )

    name: Mapped[str] = mapped_column(String(150))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    academic_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_sessions.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(TenantBase):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_number"),
        CheckConstraint("amount > 0", name="ck_invoice_amount"),
        CheckConstraint("balance >= 0", name="ck_invoice_balance"),
        CheckConstraint("status IN ('OPEN','PAID','VOID')", name="ck_invoice_status"),
    )

    invoice_number: Mapped[str] = mapped_column(String(50))
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT")
    )
    fee_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_schedules.id", ondelete="RESTRICT")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    due_on: Mapped[date | None] = mapped_column(Date)
    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class Payment(TenantBase):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "reference", name="uq_payment_reference"),
        CheckConstraint("amount > 0", name="ck_payment_amount"),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')", name="ck_payment_status"
        ),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reference: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    received_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefundRequest(TenantBase):
    __tablename__ = "refund_requests"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_refund_amount"),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')", name="ck_refund_status"
        ),
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HealthRecord(TenantBase):
    __tablename__ = "health_records"
    __table_args__ = (UniqueConstraint("tenant_id", "student_id", name="uq_student_health_record"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    chronic_conditions: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    immunisations: Mapped[list] = mapped_column(JSON, default=list)
    emergency_plan: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class HealthEncounter(TenantBase):
    __tablename__ = "health_encounters"

    health_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("health_records.id", ondelete="CASCADE")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    summary: Mapped[str] = mapped_column(Text)
    treatment: Mapped[str | None] = mapped_column(Text)
    referral: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class MedicalConsent(TenantBase):
    __tablename__ = "medical_consents"
    __table_args__ = (
        CheckConstraint("status IN ('GRANTED','DECLINED','REVOKED')", name="ck_medical_consent_status"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    consent_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class EmergencyHealthFlag(TenantBase):
    __tablename__ = "emergency_health_flags"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(150))
    instructions: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class BreakGlassAccess(TenantBase):
    __tablename__ = "break_glass_access"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','REVIEWED','REVOKED')", name="ck_break_glass_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    reason: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CounsellingCase(TenantBase):
    __tablename__ = "counselling_cases"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','CLOSED')", name="ck_counselling_case_status"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    assigned_counsellor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    referral_reason: Mapped[str] = mapped_column(Text)
    support_plan: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class CounsellingEncounter(TenantBase):
    __tablename__ = "counselling_encounters"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counselling_cases.id", ondelete="CASCADE")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confidential_notes: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class LibraryItem(TenantBase):
    __tablename__ = "library_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "catalogue_code", name="uq_library_catalogue_code"),
        CheckConstraint("total_copies >= 0", name="ck_library_total_copies"),
        CheckConstraint("available_copies >= 0", name="ck_library_available_copies"),
    )

    catalogue_code: Mapped[str] = mapped_column(String(50))
    isbn: Mapped[str | None] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    total_copies: Mapped[int] = mapped_column(Integer, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, default=1)


class LibraryLoan(TenantBase):
    __tablename__ = "library_loans"
    __table_args__ = (
        CheckConstraint("status IN ('ISSUED','RETURNED','LOST')", name="ck_library_loan_status"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("library_items.id", ondelete="RESTRICT")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT")
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    due_on: Mapped[date] = mapped_column(Date)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ISSUED")
    issued_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class TransportRoute(TenantBase):
    __tablename__ = "transport_routes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_transport_route_name"),
        CheckConstraint("capacity > 0", name="ck_transport_route_capacity"),
    )

    name: Mapped[str] = mapped_column(String(150))
    pickup_points: Mapped[list] = mapped_column(JSON, default=list)
    capacity: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TransportAssignment(TenantBase):
    __tablename__ = "transport_assignments"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="ck_transport_assignment_status"),
        Index(
            "uq_active_student_transport_assignment",
            "tenant_id",
            "student_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transport_routes.id", ondelete="RESTRICT")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    pickup_point: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class Hostel(TenantBase):
    __tablename__ = "hostels"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_hostel_name"),
        CheckConstraint("capacity > 0", name="ck_hostel_capacity"),
    )

    name: Mapped[str] = mapped_column(String(150))
    gender_policy: Mapped[str | None] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class HostelRoom(TenantBase):
    __tablename__ = "hostel_rooms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hostel_id", "name", name="uq_hostel_room_name"),
        CheckConstraint("capacity > 0", name="ck_hostel_room_capacity"),
    )

    hostel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hostels.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer)


class HostelAssignment(TenantBase):
    __tablename__ = "hostel_assignments"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="ck_hostel_assignment_status"),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_hostel_assignment_dates",
        ),
        Index(
            "uq_active_student_hostel_assignment",
            "tenant_id",
            "student_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hostel_rooms.id", ondelete="RESTRICT")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class Activity(TenantBase):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_activity_name"),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="ck_activity_status"),
    )

    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(100))
    lead_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class ActivityEnrollment(TenantBase):
    __tablename__ = "activity_enrollments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "activity_id", "student_id", name="uq_activity_enrollment"),
        CheckConstraint("status IN ('ACTIVE','WITHDRAWN')", name="ck_activity_enrollment_status"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class ActivityAttendance(TenantBase):
    __tablename__ = "activity_attendance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "activity_id", "student_id", "date", name="uq_activity_attendance"),
        CheckConstraint("status IN ('PRESENT','ABSENT','EXCUSED')", name="ck_activity_attendance_status"),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class ActivityAchievement(TenantBase):
    __tablename__ = "activity_achievements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED','APPROVED','REJECTED')", name="ck_activity_achievement_status"
        ),
    )

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE")
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
