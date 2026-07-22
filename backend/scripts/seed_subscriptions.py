"""Idempotently seed subscription catalogs and grandfather existing tenants."""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.core.feature_registry import FEATURE_REGISTRY, FeatureCode
from app.db.session import AsyncSessionLocal
from app.models.core import Permission, Tenant
from app.models.subscriptions import (
    AddOn,
    AddOnEntitlement,
    PlanEntitlement,
    SubscriptionChangeHistory,
    SubscriptionFeature,
    SubscriptionModule,
    SubscriptionPlan,
    TenantSubscription,
)

SUBSCRIPTION_PERMISSIONS = {
    "subscriptions.read",
    "subscriptions.manage",
    "plans.read",
    "plans.manage",
    "add_ons.manage",
    "tenant_entitlements.read",
    "tenant_entitlements.override",
    "billing.read",
    "billing.manage",
}

PLAN_DEFINITIONS = (
    ("STARTER", "Starter", 10, 14),
    ("STANDARD", "Standard", 20, 14),
    ("PROFESSIONAL", "Professional", 30, 14),
    ("ENTERPRISE", "Enterprise", 40, 30),
    ("ENTERPRISE_PLUS", "Enterprise Plus", 50, 30),
)

BASIC = {
    FeatureCode.STUDENTS_MANAGE,
    FeatureCode.STAFF_MANAGE,
    FeatureCode.GUARDIANS_MANAGE,
    FeatureCode.CLASSES_MANAGE,
    FeatureCode.SUBJECTS_MANAGE,
    FeatureCode.ATTENDANCE_MANAGE,
    FeatureCode.TIMETABLE_MANAGE,
    FeatureCode.ANNOUNCEMENTS_MANAGE,
    FeatureCode.REPORTING_BASIC,
}
STANDARD_EXTRA = {
    FeatureCode.ADMISSIONS_MANAGE,
    FeatureCode.RESULTS_MANAGE,
    FeatureCode.RESULTS_PUBLISH,
    FeatureCode.ANALYTICS_ACADEMIC,
    FeatureCode.COMMUNICATIONS_EMAIL,
}
PROFESSIONAL_EXTRA = {
    FeatureCode.FINANCE_INVOICING,
    FeatureCode.FINANCE_PAYMENTS,
    FeatureCode.FINANCE_REFUNDS,
    FeatureCode.MEDICAL_RECORDS,
    FeatureCode.MEDICAL_EMERGENCY_FLAGS,
    FeatureCode.LIBRARY_CIRCULATION,
    FeatureCode.STUDENT_LIFE_ACTIVITIES,
    FeatureCode.COMMUNICATIONS_SMS,
}
ENTERPRISE_EXTRA = {
    FeatureCode.PAYROLL_MANAGE,
    FeatureCode.HOSTEL_MANAGE,
    FeatureCode.TRANSPORT_ROUTES,
    FeatureCode.API_ACCESS,
    FeatureCode.WEBHOOKS_ACCESS,
    FeatureCode.INTEGRATIONS_ACCOUNTING,
    FeatureCode.ANALYTICS_ADVANCED,
    FeatureCode.AI_PERFORMANCE_INSIGHTS,
    FeatureCode.SECURITY_TWO_FACTOR,
    FeatureCode.SECURITY_IP_RESTRICTIONS,
}
ENTERPRISE_PLUS_EXTRA = {
    FeatureCode.COMMUNICATIONS_WHATSAPP,
    FeatureCode.BRANDING_CUSTOM_DOMAIN,
    FeatureCode.BRANDING_WHITE_LABEL,
}

PLAN_FEATURES = {
    "STARTER": BASIC,
    "STANDARD": BASIC | STANDARD_EXTRA,
    "PROFESSIONAL": BASIC | STANDARD_EXTRA | PROFESSIONAL_EXTRA,
    "ENTERPRISE": BASIC | STANDARD_EXTRA | PROFESSIONAL_EXTRA | ENTERPRISE_EXTRA,
    "ENTERPRISE_PLUS": set(FeatureCode) - {code for code in FeatureCode if code.value.startswith("quota.")},
}

PLAN_LIMITS = {
    "STARTER": (200, 10, 1, 5 * 1024**3),
    "STANDARD": (1000, 50, 1, 20 * 1024**3),
    "PROFESSIONAL": (3000, 150, 2, 100 * 1024**3),
    "ENTERPRISE": (100000, 10000, 100, 1024**4),
    "ENTERPRISE_PLUS": (2147483647, 2147483647, 2147483647, 10 * 1024**4),
}

ADD_ON_DEFINITIONS = {
    "FINANCE": ("Finance module", {FeatureCode.FINANCE_INVOICING: True, FeatureCode.FINANCE_PAYMENTS: True, FeatureCode.FINANCE_REFUNDS: True}),
    "MEDICAL": ("Medical module", {FeatureCode.MEDICAL_RECORDS: True, FeatureCode.MEDICAL_EMERGENCY_FLAGS: True}),
    "LIBRARY": ("Library module", {FeatureCode.LIBRARY_CIRCULATION: True}),
    "HOSTEL": ("Hostel module", {FeatureCode.HOSTEL_MANAGE: True}),
    "TRANSPORT": ("Transport module", {FeatureCode.TRANSPORT_ROUTES: True}),
    "PAYROLL": ("Payroll module", {FeatureCode.PAYROLL_MANAGE: True}),
    "API_ACCESS": ("Public API access", {FeatureCode.API_ACCESS: True}),
    "EXTRA_STUDENTS_100": ("100 additional students", {FeatureCode.QUOTA_ACTIVE_STUDENTS: 100}),
    "EXTRA_STAFF_25": ("25 additional staff", {FeatureCode.QUOTA_ACTIVE_STAFF: 25}),
    "EXTRA_CAMPUS": ("Additional campus", {FeatureCode.QUOTA_CAMPUSES: 1}),
    "EXTRA_STORAGE_10GB": ("10 GB additional storage", {FeatureCode.QUOTA_STORAGE_BYTES: 10 * 1024**3}),
    "SMS_1000": ("1,000 monthly SMS messages", {FeatureCode.QUOTA_SMS_MONTHLY: 1000}),
    "WHATSAPP_1000": ("1,000 monthly WhatsApp messages", {FeatureCode.QUOTA_WHATSAPP_MONTHLY: 1000}),
    "AI_1000": ("1,000 AI requests", {FeatureCode.QUOTA_AI_REQUESTS_MONTHLY: 1000}),
    "CUSTOM_DOMAIN": ("Custom domain", {FeatureCode.BRANDING_CUSTOM_DOMAIN: True}),
    "ADVANCED_ANALYTICS": ("Advanced analytics", {FeatureCode.ANALYTICS_ADVANCED: True}),
}


async def _get_or_create(session, model, lookup: dict, values: dict):
    item = await session.scalar(select(model).filter_by(**lookup))
    if item is None:
        item = model(**lookup, **values)
        session.add(item)
        await session.flush()
    else:
        for key, value in values.items():
            setattr(item, key, value)
    return item


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for name in sorted(SUBSCRIPTION_PERMISSIONS):
            await _get_or_create(session, Permission, {"name": name}, {"description": "Subscription and billing administration"})

        module_codes = sorted({definition.module_code for definition in FEATURE_REGISTRY.values()})
        modules = {}
        for order, code in enumerate(module_codes, 1):
            modules[code] = await _get_or_create(
                session,
                SubscriptionModule,
                {"code": code},
                {"name": code.replace(".", " ").replace("_", " ").title(), "description": f"{code} subscription module", "is_core": code.startswith("core."), "is_active": True, "display_order": order},
            )

        features = {}
        for definition in FEATURE_REGISTRY.values():
            features[definition.code] = await _get_or_create(
                session,
                SubscriptionFeature,
                {"code": definition.code.value},
                {"module_id": modules[definition.module_code].id, "name": definition.name, "description": definition.description, "value_type": definition.value_type.value, "is_metered": definition.is_metered, "is_active": True},
            )

        plans = {}
        for code, name, order, trial_days in PLAN_DEFINITIONS:
            plans[code] = await _get_or_create(
                session,
                SubscriptionPlan,
                {"code": code},
                {"name": name, "description": f"Configurable {name} subscription", "display_order": order, "billing_interval": "MONTHLY", "is_public": True, "is_active": True, "is_custom": False, "currency": "NGN", "base_price": 0, "annual_price": None, "trial_days": trial_days},
            )

        quota_codes = [FeatureCode.QUOTA_ACTIVE_STUDENTS, FeatureCode.QUOTA_ACTIVE_STAFF, FeatureCode.QUOTA_CAMPUSES, FeatureCode.QUOTA_STORAGE_BYTES]
        for plan_code, plan in plans.items():
            desired = {code: True for code in PLAN_FEATURES[plan_code]}
            desired.update(dict(zip(quota_codes, PLAN_LIMITS[plan_code], strict=True)))
            for code, value in desired.items():
                await _get_or_create(
                    session,
                    PlanEntitlement,
                    {"plan_id": plan.id, "feature_id": features[code].id},
                    {"is_enabled": True, "value": value},
                )

        for code, (name, entitlements) in ADD_ON_DEFINITIONS.items():
            add_on = await _get_or_create(
                session,
                AddOn,
                {"code": code},
                {"name": name, "description": "Price must be configured before sale", "billing_type": "QUANTITY_BASED" if code.startswith("EXTRA_") else "RECURRING", "currency": "NGN", "price": 0, "is_active": True},
            )
            for feature_code, value in entitlements.items():
                await _get_or_create(
                    session,
                    AddOnEntitlement,
                    {"add_on_id": add_on.id, "feature_id": features[feature_code].id},
                    {"is_enabled": True, "value": value},
                )

        await session.flush()
        tenants = list((await session.execute(select(Tenant))).scalars())
        now = datetime.now(timezone.utc)
        for tenant in tenants:
            await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant.id)})
            current = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id, TenantSubscription.is_current.is_(True)))
            if current is None:
                current = TenantSubscription(tenant_id=tenant.id, plan_id=plans["ENTERPRISE_PLUS"].id, status="ACTIVE", is_current=True, starts_at=now, current_period_start=now, entitlement_version=1)
                session.add(current)
                session.add(SubscriptionChangeHistory(tenant_id=tenant.id, old_plan_id=None, new_plan_id=plans["ENTERPRISE_PLUS"].id, change_type="CREATED", effective_at=now, reason="Grandfathered during entitlement-system rollout", change_metadata={"migration_grandfathered": True}))
        await session.commit()
        print(f"Seeded {len(plans)} plans, {len(features)} features, {len(ADD_ON_DEFINITIONS)} add-ons, and {len(tenants)} tenant subscriptions")


if __name__ == "__main__":
    asyncio.run(seed())
