import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TenantBase, TimestampMixin, utcnow


class CatalogBase(Base, TimestampMixin):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class SubscriptionPlan(CatalogBase):
    __tablename__ = "subscription_plans"
    __table_args__ = (CheckConstraint("billing_interval IN ('MONTHLY','TERMLY','ANNUAL','CUSTOM')", name="ck_plan_billing_interval"),)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    billing_interval: Mapped[str] = mapped_column(String(20), default="MONTHLY")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    base_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    annual_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    trial_days: Mapped[int] = mapped_column(Integer, default=0)


class SubscriptionModule(CatalogBase):
    __tablename__ = "subscription_modules"
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class SubscriptionFeature(CatalogBase):
    __tablename__ = "subscription_features"
    __table_args__ = (CheckConstraint("value_type IN ('BOOLEAN','INTEGER','DECIMAL','STRING','JSON')", name="ck_feature_value_type"),)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_modules.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(20), default="BOOLEAN")
    is_metered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PlanEntitlement(CatalogBase):
    __tablename__ = "plan_entitlements"
    __table_args__ = (UniqueConstraint("plan_id", "feature_id", name="uq_plan_feature_entitlement"),)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), index=True)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="CASCADE"), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    value: Mapped[Any | None] = mapped_column(JSON)


class AddOn(CatalogBase):
    __tablename__ = "add_ons"
    __table_args__ = (CheckConstraint("billing_type IN ('RECURRING','ONE_TIME','USAGE_BASED','QUANTITY_BASED')", name="ck_add_on_billing_type"),)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    billing_type: Mapped[str] = mapped_column(String(30), default="RECURRING")
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AddOnEntitlement(CatalogBase):
    __tablename__ = "add_on_entitlements"
    __table_args__ = (UniqueConstraint("add_on_id", "feature_id", name="uq_add_on_feature_entitlement"),)
    add_on_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("add_ons.id", ondelete="CASCADE"), index=True)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="CASCADE"), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    value: Mapped[Any | None] = mapped_column(JSON)


class TenantSubscription(TenantBase):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('TRIALING','ACTIVE','PAST_DUE','GRACE_PERIOD','SUSPENDED','CANCELLED','EXPIRED','PENDING')", name="ck_subscription_status"),
        Index("uq_current_tenant_subscription", "tenant_id", unique=True, postgresql_where=text("is_current")),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_customer_id: Mapped[str | None] = mapped_column(String(160))
    external_subscription_id: Mapped[str | None] = mapped_column(String(160))
    billing_provider: Mapped[str | None] = mapped_column(String(30))
    entitlement_version: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL")
    )
    scheduled_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TenantAddOn(TenantBase):
    __tablename__ = "tenant_add_ons"
    __table_args__ = (CheckConstraint("status IN ('PENDING','ACTIVE','SUSPENDED','EXPIRED','CANCELLED')", name="ck_tenant_add_on_status"),)
    add_on_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("add_ons.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_purchase_id: Mapped[str | None] = mapped_column(String(160))


class TenantEntitlementOverride(TenantBase):
    __tablename__ = "tenant_entitlement_overrides"
    __table_args__ = (CheckConstraint("override_type IN ('GRANT','DENY','SET_VALUE','INCREASE_LIMIT')", name="ck_entitlement_override_type"),)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="RESTRICT"), index=True)
    override_type: Mapped[str] = mapped_column(String(30))
    value: Mapped[Any | None] = mapped_column(JSON)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))


class UsageCounter(TenantBase):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_id", "period_start", "period_end", name="uq_usage_counter_period"),
        CheckConstraint("used_value >= 0 AND reserved_value >= 0", name="ck_usage_values_nonnegative"),
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="RESTRICT"), index=True)
    period_type: Mapped[str] = mapped_column(String(20), default="MONTHLY")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    reserved_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)


class UsageEvent(TenantBase):
    __tablename__ = "usage_events"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_usage_event_idempotency"),)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_features.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    event_type: Mapped[str] = mapped_column(String(30))
    reference_type: Mapped[str | None] = mapped_column(String(80))
    reference_id: Mapped[str | None] = mapped_column(String(160))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class SubscriptionChangeHistory(TenantBase):
    __tablename__ = "subscription_change_history"
    old_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    new_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    change_type: Mapped[str] = mapped_column(String(30), index=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    change_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class BillingTransaction(TenantBase):
    __tablename__ = "billing_transactions"
    __table_args__ = (UniqueConstraint("provider", "external_reference", name="uq_billing_provider_reference"),)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_subscriptions.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    external_reference: Mapped[str] = mapped_column(String(160))
    transaction_type: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transaction_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class BillingWebhookEvent(TenantBase):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "external_event_id", name="uq_webhook_provider_event"),)
    provider: Mapped[str] = mapped_column(String(30))
    external_event_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    processing_status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
