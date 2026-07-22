from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.models.subscriptions import BillingTransaction, TenantSubscription, UsageEvent


def test_subscription_tables_have_current_and_idempotency_guards() -> None:
    subscription_indexes = {item.name for item in TenantSubscription.__table__.constraints | set(TenantSubscription.__table__.indexes)}
    assert "uq_current_tenant_subscription" in subscription_indexes
    usage_constraints = {item.name for item in UsageEvent.__table__.constraints if isinstance(item, UniqueConstraint)}
    assert "uq_usage_event_idempotency" in usage_constraints
    billing_constraints = {item.name for item in BillingTransaction.__table__.constraints if isinstance(item, UniqueConstraint)}
    assert "uq_billing_provider_reference" in billing_constraints


def test_subscription_status_constraint_covers_required_states() -> None:
    checks = " ".join(str(item.sqltext) for item in TenantSubscription.__table__.constraints if isinstance(item, CheckConstraint))
    for status in ("TRIALING", "ACTIVE", "PAST_DUE", "GRACE_PERIOD", "SUSPENDED", "CANCELLED", "EXPIRED", "PENDING"):
        assert status in checks
    assert any(isinstance(item, Index) and item.unique for item in TenantSubscription.__table__.indexes)
