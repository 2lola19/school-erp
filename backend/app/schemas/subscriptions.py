from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    display_order: int
    billing_interval: str
    is_public: bool
    is_active: bool
    is_custom: bool
    currency: str
    base_price: Decimal
    annual_price: Decimal | None
    trial_days: int
    model_config = ConfigDict(from_attributes=True)


class PlanCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    name: str
    description: str | None = None
    display_order: int = 0
    billing_interval: str = "MONTHLY"
    is_public: bool = False
    is_active: bool = True
    is_custom: bool = True
    currency: str = "NGN"
    base_price: Decimal = Decimal("0")
    annual_price: Decimal | None = None
    trial_days: int = 0


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    display_order: int | None = None
    billing_interval: str | None = None
    is_public: bool | None = None
    is_active: bool | None = None
    currency: str | None = None
    base_price: Decimal | None = None
    annual_price: Decimal | None = None
    trial_days: int | None = None


class FeatureEntitlementResponse(BaseModel):
    id: UUID | None = None
    feature_id: UUID
    feature_code: str
    feature_name: str
    module_code: str
    is_enabled: bool
    value: Any = None


class EntitlementWrite(BaseModel):
    feature_code: str
    is_enabled: bool = True
    value: Any = None


class AddOnResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    billing_type: str
    currency: str
    price: Decimal
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class AddOnCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    name: str
    description: str | None = None
    billing_type: str = "RECURRING"
    currency: str = "NGN"
    price: Decimal = Decimal("0")
    is_active: bool = True


class AddOnUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    billing_type: str | None = None
    currency: str | None = None
    price: Decimal | None = None
    is_active: bool | None = None


class ModuleResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    is_core: bool
    is_active: bool
    display_order: int
    model_config = ConfigDict(from_attributes=True)


class FeatureResponse(BaseModel):
    id: UUID
    module_id: UUID
    code: str
    name: str
    description: str | None
    value_type: str
    is_metered: bool
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class FeatureUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TenantAddOnStatus(BaseModel):
    status: str
    reason: str


class SubscriptionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    plan_code: str
    plan_name: str
    status: str
    starts_at: datetime
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    entitlement_version: int
    scheduled_plan_id: UUID | None
    scheduled_change_at: datetime | None


class EffectiveEntitlementsResponse(BaseModel):
    tenant_id: str
    subscription_id: str
    plan_code: str
    status: str
    can_read: bool
    can_write: bool
    entitlement_version: int
    values: dict[str, Any]


class UsageItem(BaseModel):
    feature_code: str
    limit: float
    current_usage: float
    percent_used: float


class PlanChangeRequest(BaseModel):
    plan_id: UUID
    effective_at: datetime | None = None
    reason: str | None = None
    confirm: bool = False


class DowngradePreview(BaseModel):
    target_plan_id: UUID
    effective_at: datetime
    features_lost: list[str]
    quotas_decreased: list[dict[str, Any]]
    modules_read_only: list[str]
    unnecessary_add_ons: list[str]
    over_limit: bool


class AddOnPurchase(BaseModel):
    add_on_id: UUID
    quantity: int = Field(default=1, ge=1)


class CancelRequest(BaseModel):
    reason: str
    at_period_end: bool = True


class PlatformSubscriptionWrite(BaseModel):
    plan_id: UUID
    status: str = "ACTIVE"
    starts_at: datetime | None = None
    current_period_end: datetime | None = None
    reason: str


class OverrideCreate(BaseModel):
    feature_code: str
    override_type: str
    value: Any = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str


class HistoryResponse(BaseModel):
    id: UUID
    old_plan_id: UUID | None
    new_plan_id: UUID | None
    change_type: str
    effective_at: datetime
    reason: str | None
    metadata: dict[str, Any]


class BillingTransactionResponse(BaseModel):
    id: UUID
    provider: str
    external_reference: str
    transaction_type: str
    amount: Decimal
    currency: str
    status: str
    paid_at: datetime | None
    created_at: datetime
