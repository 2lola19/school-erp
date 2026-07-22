import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_registry import FeatureCode, feature_definition
from app.models.core import SchoolProfile, Staff, Student
from app.models.subscriptions import (
    AddOnEntitlement,
    PlanEntitlement,
    SubscriptionFeature,
    SubscriptionPlan,
    TenantAddOn,
    TenantEntitlementOverride,
    TenantSubscription,
    UsageCounter,
    UsageEvent,
)
from app.services.subscription_status import evaluate_subscription_status


@dataclass
class EffectiveEntitlements:
    tenant_id: str
    subscription_id: str
    plan_code: str
    status: str
    can_read: bool
    can_write: bool
    entitlement_version: int
    values: dict[str, Any]

    def has_feature(self, code: FeatureCode | str) -> bool:
        return self.values.get(FeatureCode(code).value) is True

    def get_limit(self, code: FeatureCode | str) -> Decimal | None:
        value = self.values.get(FeatureCode(code).value)
        if value is None or isinstance(value, bool):
            return None
        return Decimal(str(value))


def merge_entitlement_values(
    plan: dict[str, Any],
    add_ons: list[tuple[dict[str, Any], int]],
    overrides: list[tuple[str, str, Any]],
) -> dict[str, Any]:
    """Resolve plan < add-on < grant/value < denial precedence."""
    result = dict(plan)
    for values, quantity in add_ons:
        for code, value in values.items():
            if isinstance(value, bool):
                result[code] = result.get(code, False) or value
            elif value is not None:
                result[code] = Decimal(str(result.get(code, 0))) + Decimal(str(value)) * quantity
    denials: set[str] = set()
    for code, override_type, value in overrides:
        if override_type == "DENY":
            denials.add(code)
        elif override_type == "GRANT":
            result[code] = True if value is None else value
        elif override_type == "SET_VALUE":
            result[code] = value
        elif override_type == "INCREASE_LIMIT":
            result[code] = Decimal(str(result.get(code, 0))) + Decimal(str(value or 0))
    for code in denials:
        result[code] = False
    return {code: float(value) if isinstance(value, Decimal) else value for code, value in result.items()}


class EntitlementService:
    CACHE_TTL_SECONDS = 900

    def __init__(self, session: AsyncSession, redis_client: redis.Redis | None = None):
        self.session = session
        self.redis = redis_client

    async def get_effective_entitlements(self, tenant_id: uuid.UUID) -> EffectiveEntitlements:
        subscription = await self.session.scalar(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.is_current.is_(True),
            )
        )
        if subscription is None:
            raise HTTPException(403, detail={"code": "SUBSCRIPTION_INACTIVE", "message": "This school has no active subscription."})
        key = f"entitlements:{tenant_id}:{subscription.entitlement_version}"
        if self.redis is not None:
            cached = await self.redis.get(key)
            if cached:
                return EffectiveEntitlements(**json.loads(cached))

        now = datetime.now(timezone.utc)
        plan = await self.session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id))
        plan_rows = (
            await self.session.execute(
                select(SubscriptionFeature.code, PlanEntitlement.value, PlanEntitlement.is_enabled)
                .join(PlanEntitlement, PlanEntitlement.feature_id == SubscriptionFeature.id)
                .where(PlanEntitlement.plan_id == subscription.plan_id, SubscriptionFeature.is_active.is_(True))
            )
        ).all()
        plan_values = {code: (value if value is not None else enabled) for code, value, enabled in plan_rows if enabled}

        add_on_rows = (
            await self.session.execute(
                select(TenantAddOn.id, TenantAddOn.quantity, SubscriptionFeature.code, AddOnEntitlement.value, AddOnEntitlement.is_enabled)
                .join(AddOnEntitlement, AddOnEntitlement.add_on_id == TenantAddOn.add_on_id)
                .join(SubscriptionFeature, SubscriptionFeature.id == AddOnEntitlement.feature_id)
                .where(
                    TenantAddOn.tenant_id == tenant_id,
                    TenantAddOn.status == "ACTIVE",
                    TenantAddOn.starts_at <= now,
                    (TenantAddOn.ends_at.is_(None) | (TenantAddOn.ends_at > now)),
                    SubscriptionFeature.is_active.is_(True),
                )
            )
        ).all()
        grouped: dict[uuid.UUID, tuple[dict[str, Any], int]] = {}
        for add_on_id, quantity, code, value, enabled in add_on_rows:
            values, _ = grouped.setdefault(add_on_id, ({}, quantity))
            if enabled:
                values[code] = value if value is not None else True

        override_rows = (
            await self.session.execute(
                select(SubscriptionFeature.code, TenantEntitlementOverride.override_type, TenantEntitlementOverride.value)
                .join(SubscriptionFeature, SubscriptionFeature.id == TenantEntitlementOverride.feature_id)
                .where(
                    TenantEntitlementOverride.tenant_id == tenant_id,
                    TenantEntitlementOverride.starts_at <= now,
                    (TenantEntitlementOverride.ends_at.is_(None) | (TenantEntitlementOverride.ends_at > now)),
                    SubscriptionFeature.is_active.is_(True),
                )
            )
        ).all()
        values = merge_entitlement_values(plan_values, list(grouped.values()), list(override_rows))
        access = evaluate_subscription_status(
            subscription.status,
            now=now,
            trial_ends_at=subscription.trial_ends_at,
            current_period_end=subscription.current_period_end,
            grace_period_ends_at=subscription.grace_period_ends_at,
        )
        effective = EffectiveEntitlements(
            tenant_id=str(tenant_id),
            subscription_id=str(subscription.id),
            plan_code=plan.code if plan else "UNKNOWN",
            status=access.status,
            can_read=access.can_read,
            can_write=access.can_write,
            entitlement_version=subscription.entitlement_version,
            values=values,
        )
        if self.redis is not None:
            await self.redis.setex(key, self.CACHE_TTL_SECONDS, json.dumps(asdict(effective)))
        return effective

    async def has_feature(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str) -> bool:
        return (await self.get_effective_entitlements(tenant_id)).has_feature(feature_code)

    async def require_feature(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str, *, write: bool = True) -> EffectiveEntitlements:
        code = FeatureCode(feature_code)
        entitlements = await self.get_effective_entitlements(tenant_id)
        if write and not entitlements.can_write:
            error = "SUBSCRIPTION_SUSPENDED" if entitlements.status == "SUSPENDED" else "SUBSCRIPTION_EXPIRED" if entitlements.status == "EXPIRED" else "SUBSCRIPTION_READ_ONLY"
            raise HTTPException(403, detail={"code": error, "message": "The current subscription permits read-only access.", "subscription_status": entitlements.status})
        if not write and not entitlements.can_read:
            raise HTTPException(403, detail={"code": "SUBSCRIPTION_INACTIVE", "message": "The subscription does not permit access."})
        if not entitlements.has_feature(code):
            definition = feature_definition(code)
            raise HTTPException(403, detail={"code": "FEATURE_NOT_INCLUDED", "message": f"{definition.name} is not included in the current subscription.", "feature": code.value, "upgrade_required": True})
        return entitlements

    async def get_limit(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str) -> Decimal | None:
        return (await self.get_effective_entitlements(tenant_id)).get_limit(feature_code)

    async def _authoritative_usage(self, tenant_id: uuid.UUID, code: FeatureCode) -> Decimal | None:
        if code == FeatureCode.QUOTA_ACTIVE_STUDENTS:
            return Decimal(await self.session.scalar(select(func.count()).select_from(Student).where(Student.tenant_id == tenant_id)) or 0)
        if code == FeatureCode.QUOTA_ACTIVE_STAFF:
            return Decimal(await self.session.scalar(select(func.count()).select_from(Staff).where(Staff.tenant_id == tenant_id, Staff.employment_status == "ACTIVE")) or 0)
        if code == FeatureCode.QUOTA_CAMPUSES:
            return Decimal(await self.session.scalar(select(func.count()).select_from(SchoolProfile).where(SchoolProfile.tenant_id == tenant_id)) or 0)
        return None

    async def current_usage(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str) -> Decimal:
        code = FeatureCode(feature_code)
        authoritative = await self._authoritative_usage(tenant_id, code)
        if authoritative is not None:
            return authoritative
        feature_id = await self.session.scalar(select(SubscriptionFeature.id).where(SubscriptionFeature.code == code.value))
        if feature_id is None:
            return Decimal(0)
        now = datetime.now(timezone.utc)
        used = await self.session.scalar(
            select(func.coalesce(func.sum(UsageCounter.used_value + UsageCounter.reserved_value), 0)).where(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.feature_id == feature_id,
                UsageCounter.period_start <= now,
                UsageCounter.period_end > now,
            )
        )
        return Decimal(used or 0)

    async def check_quota(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str, requested_amount: Decimal | int = 1) -> tuple[Decimal, Decimal]:
        code = FeatureCode(feature_code)
        limit = await self.get_limit(tenant_id, code)
        if limit is None:
            raise HTTPException(403, detail={"code": "FEATURE_NOT_INCLUDED", "message": "This quota is not included in the current subscription.", "feature": code.value})
        current = await self.current_usage(tenant_id, code)
        if current + Decimal(requested_amount) > limit:
            raise HTTPException(409, detail={"code": "QUOTA_EXCEEDED", "message": f"The {feature_definition(code).name.lower()} limit has been reached.", "quota": code.value, "limit": float(limit), "current_usage": float(current)})
        return current, limit

    async def _counter(self, tenant_id: uuid.UUID, code: FeatureCode) -> UsageCounter:
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start.replace(year=period_start.year + (period_start.month == 12), month=1 if period_start.month == 12 else period_start.month + 1)
        feature_id = await self.session.scalar(select(SubscriptionFeature.id).where(SubscriptionFeature.code == code.value))
        counter = await self.session.scalar(
            select(UsageCounter).where(UsageCounter.tenant_id == tenant_id, UsageCounter.feature_id == feature_id, UsageCounter.period_start == period_start, UsageCounter.period_end == period_end).with_for_update()
        )
        if counter is None:
            counter = UsageCounter(tenant_id=tenant_id, feature_id=feature_id, period_type="MONTHLY", period_start=period_start, period_end=period_end, used_value=0, reserved_value=0)
            self.session.add(counter)
            await self.session.flush()
        return counter

    async def consume_quota(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str, amount: Decimal | int = 1, *, idempotency_key: str) -> None:
        code = FeatureCode(feature_code)
        existing = await self.session.scalar(select(UsageEvent.id).where(UsageEvent.tenant_id == tenant_id, UsageEvent.idempotency_key == idempotency_key))
        if existing:
            return
        await self.check_quota(tenant_id, code, amount)
        counter = await self._counter(tenant_id, code)
        counter.used_value += Decimal(amount)
        self.session.add(UsageEvent(tenant_id=tenant_id, feature_id=counter.feature_id, quantity=amount, event_type="CONSUME", idempotency_key=idempotency_key))

    async def reserve_quota(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str, amount: Decimal | int = 1) -> None:
        code = FeatureCode(feature_code)
        await self.check_quota(tenant_id, code, amount)
        counter = await self._counter(tenant_id, code)
        counter.reserved_value += Decimal(amount)

    async def release_quota(self, tenant_id: uuid.UUID, feature_code: FeatureCode | str, amount: Decimal | int = 1) -> None:
        counter = await self._counter(tenant_id, FeatureCode(feature_code))
        counter.reserved_value = max(Decimal(0), counter.reserved_value - Decimal(amount))

    async def invalidate_cache(self, tenant_id: uuid.UUID) -> None:
        if self.redis is None:
            return
        async for key in self.redis.scan_iter(match=f"entitlements:{tenant_id}:*"):
            await self.redis.delete(key)
