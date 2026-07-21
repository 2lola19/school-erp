from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import (
    Permission,
    Role,
    RoleConflict,
    RolePermission,
    Staff,
    StaffRoleAssignment,
    User,
)


@dataclass(frozen=True)
class RoleTemplate:
    name: str
    code: str
    category: str
    permissions: frozenset[str]
    sensitive: bool = False
    requires_approval: bool = False


SCHOOL_ADMIN_PERMISSIONS = frozenset(
    {
        "academic.setup.manage",
        "academic.setup.read",
        "admissions.approve",
        "admissions.create",
        "admissions.read",
        "attendance.approve",
        "attendance.correct",
        "attendance.mark",
        "attendance.read",
        "audit_logs.read",
        "classes.manage",
        "classes.read",
        "examinations.manage",
        "examinations.read",
        "finance.read",
        "finance.report",
        "health.analytics.read",
        "health.emergency_flags.read",
        "hostel.manage",
        "hostel.read",
        "library.loans.manage",
        "library.manage",
        "library.read",
        "report_cards.approve",
        "report_cards.generate",
        "report_cards.publish",
        "report_cards.read",
        "roles.approve",
        "roles.assign",
        "roles.assign.any",
        "roles.revoke",
        "scores.approve",
        "scores.enter",
        "scores.submit",
        "staff.create",
        "staff.read",
        "students.create",
        "students.read",
        "students.update",
        "subjects.manage",
        "timetable.manage",
        "timetable.read",
        "transport.manage",
        "transport.read",
        "activities.achievement.approve",
        "activities.enroll",
        "activities.manage",
        "activities.read",
    }
)

ROLE_TEMPLATES = (
    RoleTemplate(
        "School Administrator",
        "SCHOOL_ADMIN",
        "MANAGEMENT",
        SCHOOL_ADMIN_PERMISSIONS,
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Principal",
        "PRINCIPAL",
        "MANAGEMENT",
        SCHOOL_ADMIN_PERMISSIONS,
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Vice Principal, Academic",
        "VICE_PRINCIPAL_ACADEMIC",
        "MANAGEMENT",
        frozenset(
            {
                "academic.setup.manage",
                "academic.setup.read",
                "attendance.approve",
                "attendance.read",
                "classes.manage",
                "classes.read",
                "examinations.manage",
                "examinations.read",
                "report_cards.approve",
                "report_cards.generate",
                "report_cards.publish",
                "report_cards.read",
                "scores.approve",
                "staff.read",
                "students.read",
                "subjects.manage",
                "timetable.manage",
                "timetable.read",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Vice Principal, Administration",
        "VICE_PRINCIPAL_ADMINISTRATION",
        "MANAGEMENT",
        frozenset(
            {
                "admissions.approve",
                "admissions.read",
                "attendance.approve",
                "attendance.correct",
                "attendance.read",
                "audit_logs.read",
                "staff.create",
                "staff.read",
                "students.create",
                "students.read",
                "students.update",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Head of Department",
        "HEAD_OF_DEPARTMENT",
        "ACADEMIC",
        frozenset(
            {
                "attendance.read",
                "classes.read",
                "examinations.read",
                "report_cards.read",
                "scores.approve",
                "staff.read",
                "students.read",
                "timetable.read",
            }
        ),
        requires_approval=True,
    ),
    RoleTemplate(
        "Registrar / Admissions Officer",
        "REGISTRAR",
        "ADMINISTRATION",
        frozenset(
            {
                "admissions.approve",
                "admissions.create",
                "admissions.read",
                "classes.read",
                "students.create",
                "students.read",
                "students.update",
            }
        ),
    ),
    RoleTemplate(
        "Examination Officer",
        "EXAMINATION_OFFICER",
        "ACADEMIC",
        frozenset(
            {
                "examinations.manage",
                "examinations.read",
                "report_cards.generate",
                "report_cards.publish",
                "report_cards.read",
                "scores.approve",
                "students.read",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Class Teacher",
        "CLASS_TEACHER",
        "ACADEMIC",
        frozenset(
            {
                "attendance.correct",
                "attendance.mark",
                "attendance.read",
                "report_cards.read",
                "students.read",
                "timetable.read",
            }
        ),
    ),
    RoleTemplate(
        "Subject Teacher",
        "SUBJECT_TEACHER",
        "ACADEMIC",
        frozenset(
            {
                "attendance.mark",
                "attendance.read",
                "scores.enter",
                "scores.submit",
                "students.read",
                "timetable.read",
            }
        ),
    ),
    RoleTemplate(
        "Bursar / Accountant",
        "BURSAR",
        "FINANCE",
        frozenset(
            {
                "finance.fees.manage",
                "finance.invoice",
                "finance.read",
                "finance.receive_payment",
                "finance.refund.request",
                "finance.report",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Payment Approver",
        "PAYMENT_APPROVER",
        "FINANCE",
        frozenset(
            {
                "finance.approve_payment",
                "finance.read",
                "finance.refund.approve",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Medical Officer",
        "MEDICAL_OFFICER",
        "HEALTH",
        frozenset(
            {
                "health.analytics.read",
                "health.break_glass.grant",
                "health.consents.manage",
                "health.emergency_flags.read",
                "health.records.read",
                "health.records.write",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "School Nurse",
        "SCHOOL_NURSE",
        "HEALTH",
        frozenset(
            {
                "health.consents.manage",
                "health.emergency_flags.read",
                "health.records.read",
                "health.records.write",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Health Records Auditor",
        "HEALTH_RECORDS_AUDITOR",
        "HEALTH",
        frozenset(
            {
                "health.break_glass.review",
                "health.records.read",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Guidance Counsellor",
        "GUIDANCE_COUNSELLOR",
        "HEALTH",
        frozenset(
            {
                "counselling.cases.manage",
                "counselling.cases.read",
                "counselling.encounters.write",
            }
        ),
        sensitive=True,
        requires_approval=True,
    ),
    RoleTemplate(
        "Librarian",
        "LIBRARIAN",
        "SUPPORT",
        frozenset({"library.loans.manage", "library.manage", "library.read"}),
    ),
    RoleTemplate(
        "Transport Manager",
        "TRANSPORT_MANAGER",
        "SUPPORT",
        frozenset({"transport.manage", "transport.read"}),
    ),
    RoleTemplate(
        "Hostel Supervisor",
        "HOSTEL_SUPERVISOR",
        "STUDENT_LIFE",
        frozenset(
            {
                "health.emergency_flags.read",
                "hostel.manage",
                "hostel.read",
            }
        ),
    ),
    RoleTemplate(
        "Activity Patron",
        "ACTIVITY_PATRON",
        "STUDENT_LIFE",
        frozenset(
            {
                "activities.achievement.submit",
                "activities.attendance",
                "activities.enroll",
                "activities.read",
                "health.emergency_flags.read",
            }
        ),
    ),
    RoleTemplate(
        "Activity Coordinator",
        "ACTIVITY_COORDINATOR",
        "STUDENT_LIFE",
        frozenset(
            {
                "activities.achievement.approve",
                "activities.enroll",
                "activities.manage",
                "activities.read",
            }
        ),
        requires_approval=True,
    ),
)

ROLE_CONFLICT_TEMPLATES = (
    (
        "BURSAR",
        "PAYMENT_APPROVER",
        "BLOCK",
        "Payment recording and payment approval must remain separated.",
    ),
    (
        "MEDICAL_OFFICER",
        "HEALTH_RECORDS_AUDITOR",
        "BLOCK",
        "Clinical record maintenance and independent health audit must remain separated.",
    ),
)


async def ensure_tenant_role_templates(session: AsyncSession, tenant_id: UUID) -> int:
    permission_names = set().union(*(template.permissions for template in ROLE_TEMPLATES))
    permissions: dict[str, Permission] = {}
    for name in sorted(permission_names):
        permission = await session.scalar(select(Permission).where(Permission.name == name))
        if not permission:
            permission = Permission(name=name)
            session.add(permission)
            await session.flush()
        permissions[name] = permission

    changed_role_ids: set[UUID] = set()
    roles_by_code: dict[str, Role] = {}
    changes = 0
    for template in ROLE_TEMPLATES:
        role = await session.scalar(
            select(Role).where(Role.tenant_id == tenant_id, Role.code == template.code)
        )
        if not role:
            role = Role(
                tenant_id=tenant_id,
                name=template.name,
                code=template.code,
                role_category=template.category,
                is_system_role=True,
                is_sensitive=template.sensitive,
                requires_approval=template.requires_approval,
            )
            session.add(role)
            await session.flush()
            changes += 1
        else:
            expected = {
                "name": template.name,
                "role_category": template.category,
                "is_system_role": True,
                "is_sensitive": template.sensitive,
                "requires_approval": template.requires_approval,
                "is_active": True,
            }
            if any(getattr(role, field) != value for field, value in expected.items()):
                for field, value in expected.items():
                    setattr(role, field, value)
                changed_role_ids.add(role.id)
                changes += 1
        for permission_name in template.permissions:
            permission = permissions[permission_name]
            link = await session.scalar(
                select(RolePermission.id).where(
                    RolePermission.tenant_id == tenant_id,
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if not link:
                session.add(
                    RolePermission(
                        tenant_id=tenant_id,
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )
                changed_role_ids.add(role.id)
                changes += 1
        roles_by_code[template.code] = role

    for left_code, right_code, action, reason in ROLE_CONFLICT_TEMPLATES:
        left = roles_by_code[left_code]
        right = roles_by_code[right_code]
        conflict = await session.scalar(
            select(RoleConflict.id).where(
                RoleConflict.tenant_id == tenant_id,
                RoleConflict.role_id == left.id,
                RoleConflict.conflicting_role_id == right.id,
            )
        )
        if not conflict:
            session.add(
                RoleConflict(
                    tenant_id=tenant_id,
                    role_id=left.id,
                    conflicting_role_id=right.id,
                    conflict_level="CRITICAL",
                    action=action,
                    reason=reason,
                )
            )
            changes += 1

    if changed_role_ids:
        users = await session.execute(
            select(User)
            .join(Staff, Staff.user_id == User.id)
            .join(StaffRoleAssignment, StaffRoleAssignment.staff_id == Staff.id)
            .where(
                User.tenant_id == tenant_id,
                StaffRoleAssignment.tenant_id == tenant_id,
                StaffRoleAssignment.role_id.in_(changed_role_ids),
                StaffRoleAssignment.status == "ACTIVE",
            )
            .with_for_update()
        )
        for user in set(users.scalars().all()):
            user.permission_version += 1
    return changes
