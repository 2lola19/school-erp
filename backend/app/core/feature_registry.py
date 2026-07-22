from dataclasses import dataclass
from enum import Enum


class FeatureValueType(str, Enum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    STRING = "STRING"
    JSON = "JSON"


class FeatureCode(str, Enum):
    STUDENTS_MANAGE = "students.manage"
    STAFF_MANAGE = "staff.manage"
    GUARDIANS_MANAGE = "guardians.manage"
    CLASSES_MANAGE = "classes.manage"
    SUBJECTS_MANAGE = "subjects.manage"
    ATTENDANCE_MANAGE = "attendance.manage"
    TIMETABLE_MANAGE = "timetable.manage"
    ANNOUNCEMENTS_MANAGE = "announcements.manage"
    REPORTING_BASIC = "reporting.basic"
    ADMISSIONS_MANAGE = "admissions.manage"
    RESULTS_MANAGE = "results.manage"
    RESULTS_PUBLISH = "results.publish"
    ANALYTICS_ACADEMIC = "analytics.academic"
    FINANCE_INVOICING = "finance.invoicing"
    FINANCE_PAYMENTS = "finance.payments"
    FINANCE_REFUNDS = "finance.refunds"
    MEDICAL_RECORDS = "medical.records"
    MEDICAL_EMERGENCY_FLAGS = "medical.emergency_flags"
    LIBRARY_CIRCULATION = "library.circulation"
    STUDENT_LIFE_ACTIVITIES = "student_life.activities"
    HOSTEL_MANAGE = "hostel.manage"
    TRANSPORT_ROUTES = "transport.routes"
    PAYROLL_MANAGE = "payroll.manage"
    COMMUNICATIONS_EMAIL = "communications.email"
    COMMUNICATIONS_SMS = "communications.sms"
    COMMUNICATIONS_WHATSAPP = "communications.whatsapp"
    API_ACCESS = "api.access"
    WEBHOOKS_ACCESS = "webhooks.access"
    INTEGRATIONS_ACCOUNTING = "integrations.accounting"
    ANALYTICS_ADVANCED = "analytics.advanced"
    AI_PERFORMANCE_INSIGHTS = "ai.performance_insights"
    BRANDING_CUSTOM_DOMAIN = "branding.custom_domain"
    BRANDING_WHITE_LABEL = "branding.white_label"
    SECURITY_TWO_FACTOR = "security.two_factor"
    SECURITY_IP_RESTRICTIONS = "security.ip_restrictions"
    QUOTA_ACTIVE_STUDENTS = "quota.active_students"
    QUOTA_ACTIVE_STAFF = "quota.active_staff"
    QUOTA_CAMPUSES = "quota.campuses"
    QUOTA_STORAGE_BYTES = "quota.storage_bytes"
    QUOTA_SMS_MONTHLY = "quota.sms_monthly"
    QUOTA_WHATSAPP_MONTHLY = "quota.whatsapp_monthly"
    QUOTA_EMAIL_MONTHLY = "quota.email_monthly"
    QUOTA_API_REQUESTS_MONTHLY = "quota.api_requests_monthly"
    QUOTA_AI_REQUESTS_MONTHLY = "quota.ai_requests_monthly"
    QUOTA_REPORT_EXPORTS_MONTHLY = "quota.report_exports_monthly"
    QUOTA_BULK_IMPORT_ROWS_MONTHLY = "quota.bulk_import_rows_monthly"
    QUOTA_INTEGRATIONS = "quota.integrations"
    QUOTA_CUSTOM_ROLES = "quota.custom_roles"
    QUOTA_SCHOOL_ADMINS = "quota.school_admins"


@dataclass(frozen=True)
class FeatureDefinition:
    code: FeatureCode
    module_code: str
    name: str
    description: str
    value_type: FeatureValueType = FeatureValueType.BOOLEAN
    is_metered: bool = False


def _feature(
    code: FeatureCode,
    module: str,
    name: str,
    *,
    value_type: FeatureValueType = FeatureValueType.BOOLEAN,
    metered: bool = False,
) -> FeatureDefinition:
    return FeatureDefinition(code, module, name, name, value_type, metered)


FEATURE_REGISTRY: dict[FeatureCode, FeatureDefinition] = {
    definition.code: definition
    for definition in (
        _feature(FeatureCode.STUDENTS_MANAGE, "core.students", "Student management"),
        _feature(FeatureCode.STAFF_MANAGE, "core.staff", "Staff management"),
        _feature(FeatureCode.GUARDIANS_MANAGE, "core.guardians", "Guardian management"),
        _feature(FeatureCode.CLASSES_MANAGE, "academic.core", "Class management"),
        _feature(FeatureCode.SUBJECTS_MANAGE, "academic.core", "Subject management"),
        _feature(FeatureCode.ATTENDANCE_MANAGE, "academic.attendance", "Attendance"),
        _feature(FeatureCode.TIMETABLE_MANAGE, "academic.timetable", "Timetable"),
        _feature(FeatureCode.ANNOUNCEMENTS_MANAGE, "communications", "Announcements"),
        _feature(FeatureCode.REPORTING_BASIC, "analytics", "Basic reporting"),
        _feature(FeatureCode.ADMISSIONS_MANAGE, "academic.admissions", "Admissions"),
        _feature(FeatureCode.RESULTS_MANAGE, "academic.results", "Result processing"),
        _feature(FeatureCode.RESULTS_PUBLISH, "academic.results", "Result publishing"),
        _feature(FeatureCode.ANALYTICS_ACADEMIC, "analytics", "Academic analytics"),
        _feature(FeatureCode.FINANCE_INVOICING, "finance", "Finance invoicing"),
        _feature(FeatureCode.FINANCE_PAYMENTS, "finance", "Payment recording"),
        _feature(FeatureCode.FINANCE_REFUNDS, "finance", "Refund processing"),
        _feature(FeatureCode.MEDICAL_RECORDS, "medical", "Medical records"),
        _feature(FeatureCode.MEDICAL_EMERGENCY_FLAGS, "medical", "Emergency medical flags"),
        _feature(FeatureCode.LIBRARY_CIRCULATION, "library", "Library circulation"),
        _feature(FeatureCode.STUDENT_LIFE_ACTIVITIES, "student_life", "Activities and clubs"),
        _feature(FeatureCode.HOSTEL_MANAGE, "hostel", "Hostel management"),
        _feature(FeatureCode.TRANSPORT_ROUTES, "transport", "Transport management"),
        _feature(FeatureCode.PAYROLL_MANAGE, "payroll", "Payroll"),
        _feature(FeatureCode.COMMUNICATIONS_EMAIL, "communications", "Email notifications"),
        _feature(FeatureCode.COMMUNICATIONS_SMS, "communications", "SMS notifications"),
        _feature(FeatureCode.COMMUNICATIONS_WHATSAPP, "communications", "WhatsApp notifications"),
        _feature(FeatureCode.API_ACCESS, "integrations", "Public API"),
        _feature(FeatureCode.WEBHOOKS_ACCESS, "integrations", "Outbound webhooks"),
        _feature(FeatureCode.INTEGRATIONS_ACCOUNTING, "integrations", "Accounting integrations"),
        _feature(FeatureCode.ANALYTICS_ADVANCED, "analytics", "Advanced analytics"),
        _feature(FeatureCode.AI_PERFORMANCE_INSIGHTS, "ai", "AI performance insights"),
        _feature(FeatureCode.BRANDING_CUSTOM_DOMAIN, "branding", "Custom domain"),
        _feature(FeatureCode.BRANDING_WHITE_LABEL, "branding", "White-labelled platform"),
        _feature(FeatureCode.SECURITY_TWO_FACTOR, "security", "Two-factor authentication"),
        _feature(FeatureCode.SECURITY_IP_RESTRICTIONS, "security", "IP restrictions"),
        *(
            _feature(code, "quotas", code.value.removeprefix("quota.").replace("_", " ").title(), value_type=FeatureValueType.INTEGER, metered="monthly" in code.value)
            for code in FeatureCode
            if code.value.startswith("quota.")
        ),
    )
}


def feature_definition(code: FeatureCode | str) -> FeatureDefinition:
    return FEATURE_REGISTRY[FeatureCode(code)]
