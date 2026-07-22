from fastapi import APIRouter
from app.api.v1.endpoints import (
    academic,
    academic_admin,
    auth,
    billing_webhooks,
    school_services,
    subscription_catalog,
    tenant_subscriptions,
    platform_subscriptions,
    staff_roles,
    students,
    tenant,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(subscription_catalog.router, tags=["Subscription catalog"])
api_router.include_router(billing_webhooks.router, prefix="/billing/webhooks", tags=["Billing webhooks"])

api_router.include_router(tenant.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(tenant_subscriptions.router, prefix="/tenant/subscription", tags=["Tenant subscription"])
api_router.include_router(platform_subscriptions.router, prefix="/platform", tags=["Platform subscriptions"])
api_router.include_router(students.router, prefix="/students", tags=["students"])

api_router.include_router(academic.router, prefix="/academic", tags=["Academic Operations"])
api_router.include_router(
    academic_admin.router,
    prefix="/academic-admin",
    tags=["Academic Administration"],
)
api_router.include_router(staff_roles.router, prefix="/staff", tags=["Staff roles and permissions"])
api_router.include_router(
    school_services.router,
    prefix="/school-services",
    tags=["School Services"],
)
