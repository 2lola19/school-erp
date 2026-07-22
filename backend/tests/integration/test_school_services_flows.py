import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.core import (
    Permission,
    Role,
    RolePermission,
    Staff,
    StaffRoleAssignment,
    Student,
    Tenant,
    User,
)
from app.models.subscriptions import SubscriptionPlan, TenantSubscription

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="database-backed integration tests are opt-in",
    ),
]


async def _seed() -> dict[str, str]:
    suffix = uuid4().hex[:10]
    domain = f"services-{suffix}.test"
    password = "Services-integration-password"
    operator_permissions = {
        "activities.achievement.approve",
        "activities.achievement.submit",
        "activities.attendance",
        "activities.enroll",
        "activities.manage",
        "activities.read",
        "counselling.cases.manage",
        "counselling.cases.read",
        "counselling.encounters.write",
        "finance.approve_payment",
        "finance.fees.manage",
        "finance.invoice",
        "finance.read",
        "finance.receive_payment",
        "health.emergency_flags.read",
        "health.break_glass.grant",
        "health.records.read",
        "health.records.write",
        "hostel.manage",
        "hostel.read",
        "library.loans.manage",
        "library.manage",
        "library.read",
        "transport.manage",
        "transport.read",
    }
    approver_permissions = {
        "activities.achievement.approve",
        "finance.approve_payment",
    }
    safety_permissions = {"health.emergency_flags.read"}
    all_permissions = operator_permissions | approver_permissions | safety_permissions

    async with AsyncSessionLocal() as session:
        tenant = Tenant(name=f"Services {suffix}", domain=domain)
        session.add(tenant)
        await session.flush()
        await session.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
            {"tenant_id": str(tenant.id)},
        )
        plan = await session.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.code == "ENTERPRISE_PLUS")
        )
        session.add(
            TenantSubscription(
                tenant_id=tenant.id,
                plan_id=plan.id,
                status="ACTIVE",
                is_current=True,
            )
        )
        permissions = {}
        for name in sorted(all_permissions):
            permission = await session.scalar(select(Permission).where(Permission.name == name))
            if not permission:
                permission = Permission(name=name)
                session.add(permission)
                await session.flush()
            permissions[name] = permission

        async def add_identity(
            label: str, permission_names: set[str]
        ) -> tuple[User, Staff]:
            role = Role(
                tenant_id=tenant.id,
                name=f"{label} {suffix}",
                code=f"{label.upper()}_{suffix}",
                role_category="SUPPORT",
            )
            session.add(role)
            await session.flush()
            for name in permission_names:
                session.add(
                    RolePermission(
                        tenant_id=tenant.id,
                        role_id=role.id,
                        permission_id=permissions[name].id,
                    )
                )
            user = User(
                tenant_id=tenant.id,
                email=f"{label.lower()}-{suffix}@example.com",
                password_hash=get_password_hash(password),
            )
            session.add(user)
            await session.flush()
            staff = Staff(
                tenant_id=tenant.id,
                user_id=user.id,
                employee_number=f"{label[:3].upper()}-{suffix}",
                first_name=label,
                last_name="Integration",
            )
            session.add(staff)
            await session.flush()
            session.add(
                StaffRoleAssignment(
                    tenant_id=tenant.id,
                    staff_id=staff.id,
                    role_id=role.id,
                    assignment_type="PRIMARY",
                    status="ACTIVE",
                    scope={},
                    assigned_by=user.id,
                    assignment_reason="School services integration test",
                )
            )
            return user, staff

        operator, operator_staff = await add_identity("Operator", operator_permissions)
        approver, _ = await add_identity("Approver", approver_permissions)
        safety, _ = await add_identity("Safety", safety_permissions)
        student = Student(
            tenant_id=tenant.id,
            first_name="Service",
            last_name="Student",
            admission_number=f"SVC-{suffix}",
        )
        session.add(student)
        await session.commit()

    return {
        "domain": domain,
        "password": password,
        "operator_email": operator.email,
        "operator_id": str(operator.id),
        "operator_staff_id": str(operator_staff.id),
        "approver_email": approver.email,
        "safety_email": safety.email,
        "safety_id": str(safety.id),
        "student_id": str(student.id),
    }


async def _login(client: AsyncClient, context: dict[str, str], email_key: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "domain": context["domain"],
            "email": context[email_key],
            "password": context["password"],
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_school_services_security_and_workflows() -> None:
    context = await _seed()
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await redis_client.flushdb()
    await redis_client.aclose()
    transport = ASGITransport(app=app)

    async with (
        AsyncClient(transport=transport, base_url="http://testserver") as operator,
        AsyncClient(transport=transport, base_url="http://testserver") as approver,
        AsyncClient(transport=transport, base_url="http://testserver") as safety,
    ):
        operator_headers = await _login(operator, context, "operator_email")
        approver_headers = await _login(approver, context, "approver_email")
        safety_headers = await _login(safety, context, "safety_email")

        fee = await operator.post(
            "/api/v1/school-services/finance/fee-schedules",
            headers=operator_headers,
            json={"name": "Tuition", "amount": "125000.00"},
        )
        assert fee.status_code == 201, fee.text
        invoice = await operator.post(
            "/api/v1/school-services/finance/invoices",
            headers=operator_headers,
            json={
                "invoice_number": f"INV-{uuid4().hex[:8]}",
                "student_id": context["student_id"],
                "fee_schedule_id": fee.json()["id"],
            },
        )
        assert invoice.status_code == 201, invoice.text
        payment = await operator.post(
            "/api/v1/school-services/finance/payments",
            headers=operator_headers,
            json={
                "invoice_id": invoice.json()["id"],
                "amount": "50000.00",
                "reference": f"PAY-{uuid4().hex[:8]}",
            },
        )
        assert payment.status_code == 201, payment.text
        self_approval = await operator.post(
            f"/api/v1/school-services/finance/payments/{payment.json()['id']}/decision",
            headers=operator_headers,
            json={"decision": "APPROVE", "reason": "Attempt own approval"},
        )
        assert self_approval.status_code == 409
        approved_payment = await approver.post(
            f"/api/v1/school-services/finance/payments/{payment.json()['id']}/decision",
            headers=approver_headers,
            json={"decision": "APPROVE", "reason": "Receipt independently verified"},
        )
        assert approved_payment.status_code == 200, approved_payment.text

        health = await operator.put(
            "/api/v1/school-services/health/records",
            headers=operator_headers,
            json={
                "student_id": context["student_id"],
                "allergies": ["Peanuts"],
                "chronic_conditions": ["Asthma"],
                "medications": ["Inhaler"],
                "immunisations": [],
                "emergency_plan": "Use prescribed inhaler and contact guardian.",
            },
        )
        assert health.status_code == 200, health.text
        full_record_denied = await safety.get(
            f"/api/v1/school-services/health/records/{context['student_id']}",
            headers=safety_headers,
        )
        assert full_record_denied.status_code == 403
        emergency_grant = await operator.post(
            "/api/v1/school-services/health/break-glass",
            headers=operator_headers,
            json={
                "user_id": context["safety_id"],
                "student_id": context["student_id"],
                "reason": "Immediate safeguarding response requires clinical context",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            },
        )
        assert emergency_grant.status_code == 201, emergency_grant.text
        emergency_record = await safety.get(
            f"/api/v1/school-services/health/records/{context['student_id']}",
            headers=safety_headers,
        )
        assert emergency_record.status_code == 200, emergency_record.text
        flag = await operator.post(
            "/api/v1/school-services/health/emergency-flags",
            headers=operator_headers,
            json={
                "student_id": context["student_id"],
                "label": "Severe asthma",
                "instructions": "Use inhaler and call the clinic.",
            },
        )
        assert flag.status_code == 201, flag.text
        limited_flags = await safety.get(
            f"/api/v1/school-services/health/emergency-flags/{context['student_id']}",
            headers=safety_headers,
        )
        assert limited_flags.status_code == 200
        assert limited_flags.json()[0]["label"] == "Severe asthma"
        assert "chronic_conditions" not in limited_flags.json()[0]

        case = await operator.post(
            "/api/v1/school-services/counselling/cases",
            headers=operator_headers,
            json={
                "student_id": context["student_id"],
                "assigned_counsellor_id": context["operator_id"],
                "referral_reason": "Student requested confidential support",
            },
        )
        assert case.status_code == 201, case.text
        encounter = await operator.post(
            "/api/v1/school-services/counselling/encounters",
            headers=operator_headers,
            json={
                "case_id": case.json()["id"],
                "confidential_notes": "Initial support session completed.",
                "outcome": "Follow-up scheduled",
            },
        )
        assert encounter.status_code == 201, encounter.text

        item = await operator.post(
            "/api/v1/school-services/library/items",
            headers=operator_headers,
            json={
                "catalogue_code": f"BOOK-{uuid4().hex[:8]}",
                "title": "Things Fall Apart",
                "author": "Chinua Achebe",
                "total_copies": 1,
            },
        )
        assert item.status_code == 201, item.text
        loan = await operator.post(
            "/api/v1/school-services/library/loans",
            headers=operator_headers,
            json={
                "item_id": item.json()["id"],
                "student_id": context["student_id"],
                "due_on": "2026-10-01",
            },
        )
        assert loan.status_code == 201, loan.text
        returned = await operator.post(
            f"/api/v1/school-services/library/loans/{loan.json()['id']}/return",
            headers=operator_headers,
        )
        assert returned.status_code == 200
        assert returned.json()["status"] == "RETURNED"

        route = await operator.post(
            "/api/v1/school-services/transport/routes",
            headers=operator_headers,
            json={"name": f"North {uuid4().hex[:6]}", "pickup_points": ["Gate A"], "capacity": 1},
        )
        assert route.status_code == 201, route.text
        transport_assignment = await operator.post(
            "/api/v1/school-services/transport/assignments",
            headers=operator_headers,
            json={
                "route_id": route.json()["id"],
                "student_id": context["student_id"],
                "pickup_point": "Gate A",
            },
        )
        assert transport_assignment.status_code == 201, transport_assignment.text

        hostel = await operator.post(
            "/api/v1/school-services/hostels",
            headers=operator_headers,
            json={"name": f"Unity {uuid4().hex[:6]}", "capacity": 1},
        )
        assert hostel.status_code == 201, hostel.text
        room = await operator.post(
            "/api/v1/school-services/hostels/rooms",
            headers=operator_headers,
            json={"hostel_id": hostel.json()["id"], "name": "Room 1", "capacity": 1},
        )
        assert room.status_code == 201, room.text
        hostel_assignment = await operator.post(
            "/api/v1/school-services/hostels/assignments",
            headers=operator_headers,
            json={
                "room_id": room.json()["id"],
                "student_id": context["student_id"],
                "starts_on": "2026-09-01",
            },
        )
        assert hostel_assignment.status_code == 201, hostel_assignment.text

        activity = await operator.post(
            "/api/v1/school-services/activities",
            headers=operator_headers,
            json={
                "name": f"Debate {uuid4().hex[:6]}",
                "category": "Club",
                "lead_staff_id": context["operator_staff_id"],
            },
        )
        assert activity.status_code == 201, activity.text
        enrollment = await operator.post(
            "/api/v1/school-services/activities/enrollments",
            headers=operator_headers,
            json={"activity_id": activity.json()["id"], "student_id": context["student_id"]},
        )
        assert enrollment.status_code == 201, enrollment.text
        attendance = await operator.post(
            "/api/v1/school-services/activities/attendance",
            headers=operator_headers,
            json={
                "activity_id": activity.json()["id"],
                "student_id": context["student_id"],
                "date": "2026-09-15",
                "status": "PRESENT",
            },
        )
        assert attendance.status_code == 201, attendance.text
        achievement = await operator.post(
            "/api/v1/school-services/activities/achievements",
            headers=operator_headers,
            json={
                "activity_id": activity.json()["id"],
                "student_id": context["student_id"],
                "title": "Regional debate finalist",
            },
        )
        assert achievement.status_code == 201, achievement.text
        own_achievement = await operator.post(
            f"/api/v1/school-services/activities/achievements/{achievement.json()['id']}/decision",
            headers=operator_headers,
            json={"decision": "APPROVE", "reason": "Attempt own verification"},
        )
        assert own_achievement.status_code == 409
        approved_achievement = await approver.post(
            f"/api/v1/school-services/activities/achievements/{achievement.json()['id']}/decision",
            headers=approver_headers,
            json={"decision": "APPROVE", "reason": "Competition result verified"},
        )
        assert approved_achievement.status_code == 200, approved_achievement.text
        assert approved_achievement.json()["status"] == "APPROVED"
