from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Numeric

from app.db.base_class import Base
from app.models.core import (
    ActivityAchievement,
    HostelAssignment,
    Invoice,
    Payment,
    TransportAssignment,
)
from app.schemas.school_services import (
    HostelAssignmentCreate,
    MedicalConsentCreate,
    PaymentCreate,
)


def test_school_service_tables_are_registered() -> None:
    assert {
        "fee_schedules",
        "invoices",
        "payments",
        "refund_requests",
        "health_records",
        "health_encounters",
        "medical_consents",
        "emergency_health_flags",
        "break_glass_access",
        "counselling_cases",
        "counselling_encounters",
        "library_items",
        "library_loans",
        "transport_routes",
        "transport_assignments",
        "hostels",
        "hostel_rooms",
        "hostel_assignments",
        "activities",
        "activity_enrollments",
        "activity_attendance",
        "activity_achievements",
    } <= set(Base.metadata.tables)


def test_finance_uses_fixed_precision_and_approval_constraints() -> None:
    assert isinstance(Invoice.__table__.c.amount.type, Numeric)
    assert isinstance(Payment.__table__.c.amount.type, Numeric)
    payment_constraints = {constraint.name for constraint in Payment.__table__.constraints}
    assert "ck_payment_status" in payment_constraints


def test_achievements_have_an_official_approval_state() -> None:
    constraints = {constraint.name for constraint in ActivityAchievement.__table__.constraints}
    assert "ck_activity_achievement_status" in constraints


def test_student_service_assignments_preserve_history_with_one_active_record() -> None:
    transport_indexes = {index.name for index in TransportAssignment.__table__.indexes}
    hostel_indexes = {index.name for index in HostelAssignment.__table__.indexes}
    assert "uq_active_student_transport_assignment" in transport_indexes
    assert "uq_active_student_hostel_assignment" in hostel_indexes


def test_medical_consent_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        MedicalConsentCreate(
            student_id=uuid4(),
            consent_type="Emergency treatment",
            status="GRANTED",
            valid_from=date(2026, 9, 2),
            valid_until=date(2026, 9, 1),
        )


def test_hostel_assignment_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        HostelAssignmentCreate(
            room_id=uuid4(),
            student_id=uuid4(),
            starts_on=date(2026, 9, 2),
            ends_on=date(2026, 9, 1),
        )


def test_payment_decimal_payload_is_not_coerced_to_float() -> None:
    payload = PaymentCreate(
        invoice_id=uuid4(),
        amount=Decimal("1234.56"),
        reference="RECEIPT-1",
    )
    assert payload.amount == Decimal("1234.56")
