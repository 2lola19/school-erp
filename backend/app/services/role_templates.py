from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Permission, Role, RolePermission, Staff, StaffRoleAssignment, User


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
