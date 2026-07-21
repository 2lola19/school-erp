from app.services.role_templates import ROLE_TEMPLATES, SCHOOL_ADMIN_PERMISSIONS


def test_academic_role_templates_have_unique_codes() -> None:
    codes = [template.code for template in ROLE_TEMPLATES]
    assert len(codes) == len(set(codes))
    assert {
        "SCHOOL_ADMIN",
        "PRINCIPAL",
        "VICE_PRINCIPAL_ACADEMIC",
        "VICE_PRINCIPAL_ADMINISTRATION",
        "HEAD_OF_DEPARTMENT",
        "REGISTRAR",
        "EXAMINATION_OFFICER",
        "CLASS_TEACHER",
        "SUBJECT_TEACHER",
    } == set(codes)


def test_school_admin_covers_every_academic_permission() -> None:
    required = {
        permission
        for template in ROLE_TEMPLATES
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
