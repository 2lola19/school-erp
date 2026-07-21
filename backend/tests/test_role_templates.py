from app.services.role_templates import (
    ROLE_CONFLICT_TEMPLATES,
    ROLE_TEMPLATES,
    SCHOOL_ADMIN_PERMISSIONS,
)

ACADEMIC_ROLE_CODES = {
    "SCHOOL_ADMIN",
    "PRINCIPAL",
    "VICE_PRINCIPAL_ACADEMIC",
    "VICE_PRINCIPAL_ADMINISTRATION",
    "HEAD_OF_DEPARTMENT",
    "REGISTRAR",
    "EXAMINATION_OFFICER",
    "CLASS_TEACHER",
    "SUBJECT_TEACHER",
}


def test_academic_role_templates_have_unique_codes() -> None:
    codes = [template.code for template in ROLE_TEMPLATES]
    assert len(codes) == len(set(codes))
    assert ACADEMIC_ROLE_CODES <= set(codes)


def test_school_admin_covers_every_academic_permission() -> None:
    required = {
        permission
        for template in ROLE_TEMPLATES
        if template.code in ACADEMIC_ROLE_CODES
        for permission in template.permissions
        if permission != "staff.create"
    }
    assert required <= SCHOOL_ADMIN_PERMISSIONS


def test_high_impact_roles_require_approval() -> None:
    templates = {template.code: template for template in ROLE_TEMPLATES}
    for code in {
        "SCHOOL_ADMIN",
        "PRINCIPAL",
        "VICE_PRINCIPAL_ACADEMIC",
        "VICE_PRINCIPAL_ADMINISTRATION",
        "EXAMINATION_OFFICER",
    }:
        assert templates[code].requires_approval


def test_school_services_use_specialized_roles_and_separation_of_duty() -> None:
    templates = {template.code: template for template in ROLE_TEMPLATES}
    assert {
        "BURSAR",
        "PAYMENT_APPROVER",
        "MEDICAL_OFFICER",
        "SCHOOL_NURSE",
        "GUIDANCE_COUNSELLOR",
        "LIBRARIAN",
        "TRANSPORT_MANAGER",
        "HOSTEL_SUPERVISOR",
        "ACTIVITY_PATRON",
    } <= templates.keys()
    assert any(
        {left, right} == {"BURSAR", "PAYMENT_APPROVER"} and action == "BLOCK"
        for left, right, action, _ in ROLE_CONFLICT_TEMPLATES
    )
    assert "health.records.read" not in SCHOOL_ADMIN_PERMISSIONS
    assert "counselling.cases.read" not in SCHOOL_ADMIN_PERMISSIONS
