import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.core import (
    Classroom,
    Enrollment,
    Permission,
    Role,
    RolePermission,
    Staff,
    StaffRoleAssignment,
    Student,
    Subject,
    Teacher,
    Tenant,
    User,
    UserPermission,
)
from app.models.subscriptions import SubscriptionPlan, TenantSubscription

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="database-backed integration tests are opt-in",
    ),
]


async def _select_or_create_permissions(
    session: AsyncSession, names: set[str]
) -> dict[str, Permission]:
    permissions: dict[str, Permission] = {}
    for name in sorted(names):
        permission = await session.scalar(select(Permission).where(Permission.name == name))
        if not permission:
            permission = Permission(name=name)
            session.add(permission)
            await session.flush()
        permissions[name] = permission
    return permissions


async def _add_role(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    code: str,
    permissions: dict[str, Permission],
    permission_names: set[str] | None = None,
    sensitive: bool = False,
) -> Role:
    role = Role(
        tenant_id=tenant_id,
        name=name,
        code=code,
        role_category="ACADEMIC",
        is_sensitive=sensitive,
        requires_approval=sensitive,
    )
    session.add(role)
    await session.flush()
    for permission_name in permission_names or set():
        session.add(
            RolePermission(
                tenant_id=tenant_id,
                role_id=role.id,
                permission_id=permissions[permission_name].id,
            )
        )
    return role


async def _add_user_with_staff(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    role: Role,
    email: str,
    password: str,
    employee_number: str,
    scope: dict | None = None,
) -> tuple[User, Staff]:
    user = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=get_password_hash(password),
    )
    session.add(user)
    await session.flush()
    staff = Staff(
        tenant_id=tenant_id,
        user_id=user.id,
        employee_number=employee_number,
        first_name=employee_number,
        last_name="Integration",
    )
    session.add(staff)
    await session.flush()
    session.add(
        StaffRoleAssignment(
            tenant_id=tenant_id,
            staff_id=staff.id,
            role_id=role.id,
            assignment_type="PRIMARY",
            status="ACTIVE",
            scope=scope or {},
            assigned_by=user.id,
            assignment_reason="Integration test setup",
        )
    )
    return user, staff


async def _seed_authorization_scenario() -> dict[str, object]:
    suffix = uuid4().hex[:10]
    domain_a = f"alpha-{suffix}.test"
    domain_b = f"beta-{suffix}.test"
    shared_email = f"admin-{suffix}@example.com"
    permission_names = {
        "academic.setup.manage",
        "academic.setup.read",
        "admissions.approve",
        "admissions.create",
        "admissions.read",
        "attendance.approve",
        "attendance.correct",
        "attendance.mark",
        "attendance.read",
        "examinations.manage",
        "examinations.read",
        "roles.assign",
        "roles.assign.any",
        "roles.approve",
        "roles.revoke",
        "scores.approve",
        "scores.enter",
        "scores.submit",
        "staff.read",
        "students.create",
        "students.read",
        "report_cards.approve",
        "report_cards.generate",
        "report_cards.publish",
        "report_cards.read",
        "timetable.manage",
        "timetable.read",
    }

    async with AsyncSessionLocal() as session:
        async with session.begin():
            tenant_a = Tenant(name=f"Alpha {suffix}", domain=domain_a)
            tenant_b = Tenant(name=f"Beta {suffix}", domain=domain_b)
            session.add_all([tenant_a, tenant_b])
            await session.flush()
            permissions = await _select_or_create_permissions(session, permission_names)

            await session.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
                {"tenant_id": str(tenant_a.id)},
            )
            plan = await session.scalar(
                select(SubscriptionPlan).where(SubscriptionPlan.code == "ENTERPRISE_PLUS")
            )
            session.add(
                TenantSubscription(
                    tenant_id=tenant_a.id,
                    plan_id=plan.id,
                    status="ACTIVE",
                    is_current=True,
                )
            )
            subject = Subject(tenant_id=tenant_a.id, name="Mathematics", code=f"M{suffix}")
            classroom = Classroom(tenant_id=tenant_a.id, name=f"Class {suffix}")
            other_classroom = Classroom(tenant_id=tenant_a.id, name=f"Other {suffix}")
            student_a = Student(
                tenant_id=tenant_a.id,
                first_name="Alpha",
                last_name="Student",
                admission_number=f"A-{suffix}",
            )
            session.add_all([subject, classroom, other_classroom, student_a])
            await session.flush()
            session.add(
                Enrollment(
                    tenant_id=tenant_a.id,
                    student_id=student_a.id,
                    classroom_id=classroom.id,
                )
            )

            admin_role = await _add_role(
                session,
                tenant_id=tenant_a.id,
                name="Integration Administrator",
                code=f"ADMIN_{suffix}",
                permissions=permissions,
                permission_names={
                    "academic.setup.manage",
                    "academic.setup.read",
                    "admissions.approve",
                    "admissions.create",
                    "admissions.read",
                    "attendance.correct",
                    "attendance.read",
                    "examinations.manage",
                    "examinations.read",
                    "roles.assign",
                    "roles.assign.any",
                    "roles.approve",
                    "roles.revoke",
                    "staff.read",
                    "students.create",
                    "students.read",
                    "report_cards.generate",
                    "report_cards.publish",
                    "report_cards.read",
                    "timetable.manage",
                    "timetable.read",
                },
            )
            teacher_role = await _add_role(
                session,
                tenant_id=tenant_a.id,
                name="Integration Teacher",
                code=f"TEACHER_{suffix}",
                permissions=permissions,
                permission_names={
                    "scores.enter",
                    "scores.submit",
                    "scores.approve",
                    "students.read",
                    "attendance.mark",
                    "attendance.read",
                    "timetable.read",
                },
            )
            approver_role = await _add_role(
                session,
                tenant_id=tenant_a.id,
                name="Integration Approver",
                code=f"APPROVER_{suffix}",
                permissions=permissions,
                permission_names={
                    "attendance.approve",
                    "report_cards.approve",
                    "roles.approve",
                    "scores.approve",
                },
            )
            observer_role = await _add_role(
                session,
                tenant_id=tenant_a.id,
                name="Integration Observer",
                code=f"OBSERVER_{suffix}",
                permissions=permissions,
                permission_names={"students.create", "students.read"},
            )
            sensitive_role = await _add_role(
                session,
                tenant_id=tenant_a.id,
                name="Sensitive Integration Role",
                code=f"SENSITIVE_{suffix}",
                permissions=permissions,
                sensitive=True,
            )
            secondary_roles = [
                await _add_role(
                    session,
                    tenant_id=tenant_a.id,
                    name=f"Secondary {index} {suffix}",
                    code=f"SECONDARY_{index}_{suffix}",
                    permissions=permissions,
                )
                for index in range(5)
            ]

            admin_user, admin_staff = await _add_user_with_staff(
                session,
                tenant_id=tenant_a.id,
                role=admin_role,
                email=shared_email,
                password="Alpha-integration-password",
                employee_number=f"ADM-{suffix}",
            )
            teacher_user, teacher_staff = await _add_user_with_staff(
                session,
                tenant_id=tenant_a.id,
                role=teacher_role,
                email=f"teacher-{suffix}@example.com",
                password="Teacher-integration-password",
                employee_number=f"TCH-{suffix}",
                scope={
                    "classroom_id": str(classroom.id),
                    "subject_id": str(subject.id),
                },
            )
            approver_user, _ = await _add_user_with_staff(
                session,
                tenant_id=tenant_a.id,
                role=approver_role,
                email=f"approver-{suffix}@example.com",
                password="Approver-integration-password",
                employee_number=f"APR-{suffix}",
            )
            observer_user, observer_staff = await _add_user_with_staff(
                session,
                tenant_id=tenant_a.id,
                role=observer_role,
                email=f"observer-{suffix}@example.com",
                password="Observer-integration-password",
                employee_number=f"OBS-{suffix}",
            )
            session.add(
                UserPermission(
                    tenant_id=tenant_a.id,
                    user_id=observer_user.id,
                    permission_id=permissions["students.create"].id,
                    effect="DENY",
                    approved_by=admin_user.id,
                    approved_at=datetime.now(timezone.utc),
                )
            )
            teacher = Teacher(
                tenant_id=tenant_a.id,
                staff_id=teacher_staff.id,
                first_name="Integration",
                last_name="Teacher",
                email=teacher_user.email,
                employee_id=f"TEACHER-{suffix}",
            )
            session.add(teacher)
            await session.flush()

            await session.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
                {"tenant_id": str(tenant_b.id)},
            )
            session.add(
                TenantSubscription(
                    tenant_id=tenant_b.id,
                    plan_id=plan.id,
                    status="ACTIVE",
                    is_current=True,
                )
            )
            tenant_b_role = await _add_role(
                session,
                tenant_id=tenant_b.id,
                name="Beta Reader",
                code=f"BETA_{suffix}",
                permissions=permissions,
                permission_names={"students.read"},
            )
            await _add_user_with_staff(
                session,
                tenant_id=tenant_b.id,
                role=tenant_b_role,
                email=shared_email,
                password="Beta-integration-password",
                employee_number=f"BET-{suffix}",
            )
            student_b = Student(
                tenant_id=tenant_b.id,
                first_name="Beta",
                last_name="Student",
                admission_number=f"B-{suffix}",
            )
            session.add(student_b)
            await session.flush()

    return {
        "domain_a": domain_a,
        "domain_b": domain_b,
        "shared_email": shared_email,
        "admin_password": "Alpha-integration-password",
        "teacher_email": teacher_user.email,
        "teacher_password": "Teacher-integration-password",
        "approver_email": approver_user.email,
        "approver_password": "Approver-integration-password",
        "observer_email": observer_user.email,
        "observer_password": "Observer-integration-password",
        "teacher_staff_id": teacher_staff.id,
        "teacher_id": teacher.id,
        "observer_staff_id": observer_staff.id,
        "sensitive_role_id": sensitive_role.id,
        "secondary_role_ids": [role.id for role in secondary_roles],
        "student_a_id": student_a.id,
        "student_a_admission": student_a.admission_number,
        "student_b_admission": student_b.admission_number,
        "subject_id": subject.id,
        "classroom_id": classroom.id,
        "other_classroom_id": other_classroom.id,
    }


async def _login(
    client: AsyncClient, *, domain: str, email: str, password: str
) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"domain": domain, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_tenant_roles_sessions_and_grade_approval_end_to_end() -> None:
    scenario = await _seed_authorization_scenario()
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await redis_client.flushdb()
    await redis_client.aclose()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as admin_client:
        wrong_tenant = await admin_client.post(
            "/api/v1/auth/login",
            json={
                "domain": scenario["domain_b"],
                "email": scenario["shared_email"],
                "password": scenario["admin_password"],
            },
        )
        assert wrong_tenant.status_code == 401

        admin_token = await _login(
            admin_client,
            domain=str(scenario["domain_a"]),
            email=str(scenario["shared_email"]),
            password=str(scenario["admin_password"]),
        )
        old_refresh = admin_client.cookies.get("school_erp_refresh")
        assert old_refresh
        refresh = await admin_client.post("/api/v1/auth/refresh")
        assert refresh.status_code == 200
        refreshed_admin_token = refresh.json()["access_token"]
        assert refreshed_admin_token != admin_token
        assert (
            await admin_client.get("/api/v1/auth/me", headers=_bearer(admin_token))
        ).status_code == 401

        async with AsyncClient(transport=transport, base_url="http://testserver") as replay:
            replay_response = await replay.post(
                "/api/v1/auth/refresh",
                headers={"Cookie": f"school_erp_refresh={old_refresh}"},
            )
            assert replay_response.status_code == 401

        admin_headers = _bearer(refreshed_admin_token)
        students = await admin_client.get("/api/v1/students/", headers=admin_headers)
        assert students.status_code == 200
        admissions = {student["admission_number"] for student in students.json()}
        assert scenario["student_a_admission"] in admissions
        assert scenario["student_b_admission"] not in admissions

        sensitive_assignment = await admin_client.post(
            f"/api/v1/staff/{scenario['observer_staff_id']}/roles/secondary",
            headers=admin_headers,
            json={
                "role_id": str(scenario["sensitive_role_id"]),
                "assignment_type": "SECONDARY",
                "scope": {},
                "reason": "Exercise dual-control approval",
            },
        )
        assert sensitive_assignment.status_code == 201, sensitive_assignment.text
        assert sensitive_assignment.json()["status"] == "PENDING"
        assignment_id = sensitive_assignment.json()["id"]
        self_approval = await admin_client.post(
            f"/api/v1/staff/{scenario['observer_staff_id']}/roles/{assignment_id}/approve",
            headers=admin_headers,
            json={"reason": "Attempt self approval"},
        )
        assert self_approval.status_code == 409

        for role_id in scenario["secondary_role_ids"][:4]:
            assigned = await admin_client.post(
                f"/api/v1/staff/{scenario['teacher_staff_id']}/roles/secondary",
                headers=admin_headers,
                json={
                    "role_id": str(role_id),
                    "assignment_type": "SECONDARY",
                    "scope": {},
                    "reason": "Exercise secondary role limit",
                },
            )
            assert assigned.status_code == 201, assigned.text
            assert assigned.json()["status"] == "ACTIVE"
        fifth = await admin_client.post(
            f"/api/v1/staff/{scenario['teacher_staff_id']}/roles/secondary",
            headers=admin_headers,
            json={
                "role_id": str(scenario["secondary_role_ids"][4]),
                "assignment_type": "SECONDARY",
                "scope": {},
                "reason": "This fifth role must be rejected",
            },
        )
        assert fifth.status_code == 409

        async with AsyncClient(transport=transport, base_url="http://testserver") as observer_client:
            observer_token = await _login(
                observer_client,
                domain=str(scenario["domain_a"]),
                email=str(scenario["observer_email"]),
                password=str(scenario["observer_password"]),
            )
            denied_create = await observer_client.post(
                "/api/v1/students/",
                headers=_bearer(observer_token),
                json={
                    "first_name": "Denied",
                    "last_name": "Student",
                    "admission_number": f"DENIED-{uuid4().hex[:8]}",
                },
            )
            assert denied_create.status_code == 403

        async with AsyncClient(transport=transport, base_url="http://testserver") as approver_client:
            approver_token = await _login(
                approver_client,
                domain=str(scenario["domain_a"]),
                email=str(scenario["approver_email"]),
                password=str(scenario["approver_password"]),
            )
            approved_assignment = await approver_client.post(
                f"/api/v1/staff/{scenario['observer_staff_id']}/roles/{assignment_id}/approve",
                headers=_bearer(approver_token),
                json={"reason": "Independent approval completed"},
            )
            assert approved_assignment.status_code == 200, approved_assignment.text
            assert approved_assignment.json()["status"] == "ACTIVE"

            async with AsyncClient(transport=transport, base_url="http://testserver") as teacher_client:
                teacher_token = await _login(
                    teacher_client,
                    domain=str(scenario["domain_a"]),
                    email=str(scenario["teacher_email"]),
                    password=str(scenario["teacher_password"]),
                )
                teacher_headers = _bearer(teacher_token)
                context = await teacher_client.get(
                    "/api/v1/auth/me", headers=teacher_headers
                )
                assert context.status_code == 200
                assert len(context.json()["workspaces"]) == 5

                outside_scope = await teacher_client.post(
                    "/api/v1/academic/grades",
                    headers=teacher_headers,
                    json={
                        "student_id": str(scenario["student_a_id"]),
                        "subject_id": str(scenario["subject_id"]),
                        "classroom_id": str(scenario["other_classroom_id"]),
                        "term": "First",
                        "academic_year": "2026/2027",
                        "score": 75,
                    },
                )
                assert outside_scope.status_code == 403

                entered = await teacher_client.post(
                    "/api/v1/academic/grades",
                    headers=teacher_headers,
                    json={
                        "student_id": str(scenario["student_a_id"]),
                        "subject_id": str(scenario["subject_id"]),
                        "classroom_id": str(scenario["classroom_id"]),
                        "term": "First",
                        "academic_year": "2026/2027",
                        "score": 88,
                    },
                )
                assert entered.status_code == 201, entered.text
                grade_id = entered.json()["id"]
                submitted = await teacher_client.post(
                    f"/api/v1/academic/grades/{grade_id}/submit",
                    headers=teacher_headers,
                )
                assert submitted.status_code == 200
                assert submitted.json()["workflow_status"] == "SUBMITTED"
                self_grade_approval = await teacher_client.post(
                    f"/api/v1/academic/grades/{grade_id}/approve",
                    headers=teacher_headers,
                )
                assert self_grade_approval.status_code == 409

            approved_grade = await approver_client.post(
                f"/api/v1/academic/grades/{grade_id}/approve",
                headers=_bearer(approver_token),
            )
            assert approved_grade.status_code == 200, approved_grade.text
            assert approved_grade.json()["workflow_status"] == "APPROVED"

            academic_session = await admin_client.post(
                "/api/v1/academic-admin/sessions",
                headers=admin_headers,
                json={
                    "name": "2026/2027",
                    "starts_on": "2026-09-01",
                    "ends_on": "2027-07-31",
                },
            )
            assert academic_session.status_code == 201, academic_session.text
            session_id = academic_session.json()["id"]
            activated = await admin_client.post(
                f"/api/v1/academic-admin/sessions/{session_id}/activate",
                headers=admin_headers,
                json={"reason": "Start the integration academic year"},
            )
            assert activated.status_code == 200
            assert activated.json()["status"] == "ACTIVE"

            term = await admin_client.post(
                "/api/v1/academic-admin/terms",
                headers=admin_headers,
                json={
                    "session_id": session_id,
                    "name": "First",
                    "starts_on": "2026-09-01",
                    "ends_on": "2026-12-20",
                },
            )
            assert term.status_code == 201, term.text
            term_id = term.json()["id"]

            application_number = f"APP-{uuid4().hex[:8]}"
            applicant = await admin_client.post(
                "/api/v1/academic-admin/applicants",
                headers=admin_headers,
                json={
                    "application_number": application_number,
                    "first_name": "New",
                    "last_name": "Applicant",
                    "date_of_birth": "2015-03-02",
                    "guardian": {
                        "first_name": "Primary",
                        "last_name": "Guardian",
                        "email": f"guardian-{uuid4().hex[:8]}@example.com",
                        "phone": "+2348000000000",
                        "relationship": "Parent",
                    },
                },
            )
            assert applicant.status_code == 201, applicant.text
            admission = await admin_client.post(
                f"/api/v1/academic-admin/applicants/{applicant.json()['id']}/decision",
                headers=admin_headers,
                json={
                    "decision": "ADMIT",
                    "reason": "Applicant met the published criteria",
                    "admission_number": f"NEW-{uuid4().hex[:8]}",
                    "classroom_id": str(scenario["classroom_id"]),
                },
            )
            assert admission.status_code == 200, admission.text
            assert admission.json()["status"] == "ADMITTED"
            assert admission.json()["admitted_student_id"]

            exam_cycle = await admin_client.post(
                "/api/v1/academic-admin/exam-cycles",
                headers=admin_headers,
                json={
                    "term_id": term_id,
                    "name": "First Term Examination",
                    "opens_at": "2026-11-01T08:00:00Z",
                    "closes_at": "2026-12-10T17:00:00Z",
                },
            )
            assert exam_cycle.status_code == 201, exam_cycle.text
            cycle_id = exam_cycle.json()["id"]
            component = await admin_client.post(
                "/api/v1/academic-admin/assessment-components",
                headers=admin_headers,
                json={
                    "exam_cycle_id": cycle_id,
                    "classroom_id": str(scenario["classroom_id"]),
                    "subject_id": str(scenario["subject_id"]),
                    "name": "Examination",
                    "maximum_score": 100,
                    "weight": 100,
                },
            )
            assert component.status_code == 201, component.text
            for action_name, expected_status in (
                ("OPEN", "OPEN"),
                ("CLOSE", "CLOSED"),
                ("PUBLISH", "PUBLISHED"),
            ):
                transitioned = await admin_client.post(
                    f"/api/v1/academic-admin/exam-cycles/{cycle_id}/transition",
                    headers=admin_headers,
                    json={
                        "action": action_name,
                        "reason": f"Move examination cycle to {expected_status}",
                    },
                )
                assert transitioned.status_code == 200, transitioned.text
                assert transitioned.json()["status"] == expected_status

            timetable = await admin_client.post(
                "/api/v1/academic-admin/timetable",
                headers=admin_headers,
                json={
                    "term_id": term_id,
                    "classroom_id": str(scenario["classroom_id"]),
                    "subject_id": str(scenario["subject_id"]),
                    "teacher_id": str(scenario["teacher_id"]),
                    "weekday": 1,
                    "period_label": "P1",
                    "starts_at": "08:00:00",
                    "ends_at": "08:45:00",
                },
            )
            assert timetable.status_code == 201, timetable.text

            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as attendance_client:
                attendance_token = await _login(
                    attendance_client,
                    domain=str(scenario["domain_a"]),
                    email=str(scenario["teacher_email"]),
                    password=str(scenario["teacher_password"]),
                )
                scoped_timetable = await attendance_client.get(
                    f"/api/v1/academic-admin/timetable?term_id={term_id}",
                    headers=_bearer(attendance_token),
                )
                assert scoped_timetable.status_code == 200, scoped_timetable.text
                assert [entry["id"] for entry in scoped_timetable.json()] == [
                    timetable.json()["id"]
                ]
                marked = await attendance_client.post(
                    "/api/v1/academic-admin/attendance",
                    headers=_bearer(attendance_token),
                    json={
                        "student_id": str(scenario["student_a_id"]),
                        "classroom_id": str(scenario["classroom_id"]),
                        "date": "2026-09-15",
                        "status": "PRESENT",
                    },
                )
                assert marked.status_code == 201, marked.text
                attendance_id = marked.json()["id"]
                submitted_attendance = await attendance_client.post(
                    f"/api/v1/academic-admin/attendance/{attendance_id}/submit",
                    headers=_bearer(attendance_token),
                    json={"reason": "Daily register complete"},
                )
                assert submitted_attendance.status_code == 200
                assert submitted_attendance.json()["workflow_status"] == "SUBMITTED"
                scoped_attendance = await attendance_client.get(
                    "/api/v1/academic-admin/attendance",
                    headers=_bearer(attendance_token),
                )
                assert scoped_attendance.status_code == 200, scoped_attendance.text
                assert [entry["id"] for entry in scoped_attendance.json()] == [attendance_id]
                outside_scope = await attendance_client.get(
                    "/api/v1/academic-admin/attendance",
                    headers=_bearer(attendance_token),
                    params={"classroom_id": str(scenario["other_classroom_id"])},
                )
                assert outside_scope.status_code == 403

            approved_attendance = await approver_client.post(
                f"/api/v1/academic-admin/attendance/{attendance_id}/approve",
                headers=_bearer(approver_token),
                json={"reason": "Register independently checked"},
            )
            assert approved_attendance.status_code == 200, approved_attendance.text
            assert approved_attendance.json()["workflow_status"] == "APPROVED"

            generated_report = await admin_client.post(
                "/api/v1/academic-admin/report-cards",
                headers=admin_headers,
                json={
                    "student_id": str(scenario["student_a_id"]),
                    "term_id": term_id,
                    "classroom_id": str(scenario["classroom_id"]),
                    "remarks": "Consistent academic progress",
                },
            )
            assert generated_report.status_code == 201, generated_report.text
            report_id = generated_report.json()["id"]
            assert generated_report.json()["entries"][0]["score"] == 88
            approved_report = await approver_client.post(
                f"/api/v1/academic-admin/report-cards/{report_id}/approve",
                headers=_bearer(approver_token),
                json={"reason": "Results and remarks independently reviewed"},
            )
            assert approved_report.status_code == 200, approved_report.text
            published_report = await admin_client.post(
                f"/api/v1/academic-admin/report-cards/{report_id}/publish",
                headers=admin_headers,
                json={"reason": "Release approved first-term report"},
            )
            assert published_report.status_code == 200, published_report.text
            assert published_report.json()["status"] == "PUBLISHED"

        async with AsyncClient(transport=transport, base_url="http://testserver") as beta_client:
            beta_token = await _login(
                beta_client,
                domain=str(scenario["domain_b"]),
                email=str(scenario["shared_email"]),
                password="Beta-integration-password",
            )
            beta_students = await beta_client.get(
                "/api/v1/students/", headers=_bearer(beta_token)
            )
            assert beta_students.status_code == 200
            beta_admissions = {
                student["admission_number"] for student in beta_students.json()
            }
            assert scenario["student_b_admission"] in beta_admissions
            assert scenario["student_a_admission"] not in beta_admissions

        logout = await admin_client.post(
            "/api/v1/auth/logout", headers=admin_headers
        )
        assert logout.status_code == 204
        assert (
            await admin_client.get("/api/v1/auth/me", headers=admin_headers)
        ).status_code == 401
