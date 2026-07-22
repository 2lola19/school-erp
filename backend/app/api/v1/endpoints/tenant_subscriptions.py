import uuid
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_redis, get_rls_db, require_permissions
from app.core.feature_registry import FeatureCode
from app.models.subscriptions import (
    AddOn,
    BillingTransaction,
    PlanEntitlement,
    SubscriptionChangeHistory,
    SubscriptionFeature,
    SubscriptionModule,
    SubscriptionPlan,
    TenantAddOn,
    TenantSubscription,
)
from app.schemas.auth import CurrentUser
from app.schemas.subscriptions import (
    AddOnPurchase,
    BillingTransactionResponse,
    CancelRequest,
    DowngradePreview,
    EffectiveEntitlementsResponse,
    HistoryResponse,
    PlanChangeRequest,
    SubscriptionResponse,
    UsageItem,
)
from app.services.entitlements import EntitlementService
from app.services.subscription_changes import calculate_downgrade_impact

router = APIRouter()


async def _current(session: AsyncSession, tenant_id: UUID) -> tuple[TenantSubscription, SubscriptionPlan]:
    row = (
        await session.execute(
            select(TenantSubscription, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == TenantSubscription.plan_id)
            .where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True))
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(403, detail={"code": "SUBSCRIPTION_INACTIVE", "message": "No current subscription."})
    return row


def _response(subscription: TenantSubscription, plan: SubscriptionPlan) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan_id=plan.id,
        plan_code=plan.code,
        plan_name=plan.name,
        status=subscription.status,
        starts_at=subscription.starts_at,
        trial_ends_at=subscription.trial_ends_at,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        entitlement_version=subscription.entitlement_version,
        scheduled_plan_id=subscription.scheduled_plan_id,
        scheduled_change_at=subscription.scheduled_change_at,
    )


@router.get("", response_model=SubscriptionResponse)
async def current_subscription(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.read"))], session: Annotated[AsyncSession, Depends(get_rls_db)]) -> SubscriptionResponse:
    return _response(*(await _current(session, actor.tenant_id)))


@router.get("/entitlements", response_model=EffectiveEntitlementsResponse)
async def effective_entitlements(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.read"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> EffectiveEntitlementsResponse:
    return EffectiveEntitlementsResponse.model_validate((await EntitlementService(session, redis_client).get_effective_entitlements(actor.tenant_id)), from_attributes=True)


@router.get("/usage", response_model=list[UsageItem])
async def usage(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.read"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> list[UsageItem]:
    service = EntitlementService(session, redis_client)
    entitlements = await service.get_effective_entitlements(actor.tenant_id)
    items = []
    for code in FeatureCode:
        if not code.value.startswith("quota."):
            continue
        limit = entitlements.get_limit(code)
        if limit is None:
            continue
        current = await service.current_usage(actor.tenant_id, code)
        items.append(UsageItem(feature_code=code.value, limit=float(limit), current_usage=float(current), percent_used=float(current / limit * 100) if limit else 0))
    return items


@router.get("/history", response_model=list[HistoryResponse])
async def history(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.read"))], session: Annotated[AsyncSession, Depends(get_rls_db)]) -> list[HistoryResponse]:
    rows = list((await session.execute(select(SubscriptionChangeHistory).where(SubscriptionChangeHistory.tenant_id == actor.tenant_id).order_by(SubscriptionChangeHistory.created_at.desc()))).scalars())
    return [HistoryResponse(id=row.id, old_plan_id=row.old_plan_id, new_plan_id=row.new_plan_id, change_type=row.change_type, effective_at=row.effective_at, reason=row.reason, metadata=row.change_metadata) for row in rows]


async def _plan_values(session: AsyncSession, plan_id: UUID) -> dict[str, Any]:
    rows = (await session.execute(select(SubscriptionFeature.code, PlanEntitlement.value, PlanEntitlement.is_enabled).join(PlanEntitlement, PlanEntitlement.feature_id == SubscriptionFeature.id).where(PlanEntitlement.plan_id == plan_id))).all()
    return {code: value if value is not None else enabled for code, value, enabled in rows if enabled}


async def _preview(session: AsyncSession, redis_client: redis.Redis, tenant_id: UUID, target: SubscriptionPlan, effective_at: datetime | None) -> DowngradePreview:
    service = EntitlementService(session, redis_client)
    current = await service.get_effective_entitlements(tenant_id)
    target_values = await _plan_values(session, target.id)
    quota_usage = {}
    for code, old_value in current.values.items():
        if code.startswith("quota.") and code in target_values and float(old_value) > float(target_values[code]):
            quota_usage[code] = float(await service.current_usage(tenant_id, code))
    features_lost, decreases, over_limit = calculate_downgrade_impact(
        current.values,
        target_values,
        quota_usage,
    )
    modules = list((await session.execute(select(SubscriptionModule.code).join(SubscriptionFeature, SubscriptionFeature.module_id == SubscriptionModule.id).where(SubscriptionFeature.code.in_(features_lost)).distinct())).scalars()) if features_lost else []
    return DowngradePreview(target_plan_id=target.id, effective_at=effective_at or datetime.now(timezone.utc), features_lost=features_lost, quotas_decreased=decreases, modules_read_only=sorted(modules), unnecessary_add_ons=[], over_limit=over_limit)


@router.post("/upgrade")
async def request_upgrade(payload: PlanChangeRequest, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)]) -> dict[str, Any]:
    subscription, current_plan = await _current(session, actor.tenant_id)
    target = await session.get(SubscriptionPlan, payload.plan_id)
    if target is None or not target.is_active:
        raise HTTPException(404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    if target.display_order <= current_plan.display_order:
        raise HTTPException(422, detail={"code": "INVALID_SUBSCRIPTION_CHANGE", "message": "Use the downgrade endpoint for this plan."})
    reference = f"UPGRADE-{uuid.uuid4()}"
    session.add(BillingTransaction(tenant_id=actor.tenant_id, subscription_id=subscription.id, provider="UNCONFIGURED", external_reference=reference, transaction_type="PLAN_UPGRADE", amount=target.base_price, currency=target.currency, status="PENDING", transaction_metadata={"target_plan_id": str(target.id)}))
    session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, old_plan_id=current_plan.id, new_plan_id=target.id, change_type="UPGRADE_REQUESTED", effective_at=payload.effective_at or datetime.now(timezone.utc), changed_by=actor.id, reason=payload.reason, change_metadata={"billing_reference": reference}))
    await session.commit()
    return {"code": "PAYMENT_REQUIRED", "message": "Upgrade recorded. Access will activate only after verified payment or platform approval.", "billing_reference": reference}


@router.post("/downgrade", response_model=DowngradePreview)
async def request_downgrade(payload: PlanChangeRequest, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> DowngradePreview:
    subscription, current_plan = await _current(session, actor.tenant_id)
    target = await session.get(SubscriptionPlan, payload.plan_id)
    if target is None or not target.is_active:
        raise HTTPException(404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    if target.display_order >= current_plan.display_order:
        raise HTTPException(422, detail={"code": "INVALID_SUBSCRIPTION_CHANGE", "message": "Use the upgrade endpoint for this plan."})
    effective_at = payload.effective_at or subscription.current_period_end or datetime.now(timezone.utc)
    preview = await _preview(session, redis_client, actor.tenant_id, target, effective_at)
    if payload.confirm:
        subscription.scheduled_plan_id = target.id
        subscription.scheduled_change_at = effective_at
        session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, old_plan_id=current_plan.id, new_plan_id=target.id, change_type="DOWNGRADE_SCHEDULED", effective_at=effective_at, changed_by=actor.id, reason=payload.reason, change_metadata={"impact": preview.model_dump(mode="json")}))
        await session.commit()
    return preview


@router.post("/cancel")
async def cancel(payload: CancelRequest, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    subscription, plan = await _current(session, actor.tenant_id)
    subscription.cancel_at_period_end = payload.at_period_end
    subscription.cancelled_at = datetime.now(timezone.utc)
    if not payload.at_period_end:
        subscription.status = "CANCELLED"
    subscription.entitlement_version += 1
    session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, old_plan_id=plan.id, new_plan_id=plan.id, change_type="CANCELLED", effective_at=subscription.current_period_end if payload.at_period_end and subscription.current_period_end else datetime.now(timezone.utc), changed_by=actor.id, reason=payload.reason))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(actor.tenant_id)
    return {"message": "Cancellation scheduled" if payload.at_period_end else "Subscription cancelled"}


@router.post("/reactivate")
async def reactivate(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    subscription, plan = await _current(session, actor.tenant_id)
    if subscription.status == "EXPIRED":
        raise HTTPException(409, detail={"code": "PAYMENT_REQUIRED", "message": "An expired subscription requires renewal payment."})
    subscription.cancel_at_period_end = False
    subscription.cancelled_at = None
    subscription.status = "ACTIVE"
    subscription.entitlement_version += 1
    session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, old_plan_id=plan.id, new_plan_id=plan.id, change_type="REACTIVATED", effective_at=datetime.now(timezone.utc), changed_by=actor.id))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(actor.tenant_id)
    return {"message": "Subscription reactivated"}


@router.post("/add-ons", status_code=201)
async def purchase_add_on(payload: AddOnPurchase, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)]) -> dict[str, str]:
    add_on = await session.get(AddOn, payload.add_on_id)
    if add_on is None or not add_on.is_active:
        raise HTTPException(404, detail="Add-on not found")
    item = TenantAddOn(tenant_id=actor.tenant_id, add_on_id=add_on.id, status="PENDING", quantity=payload.quantity)
    session.add(item)
    await session.flush()
    session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, change_type="ADD_ON_REQUESTED", effective_at=datetime.now(timezone.utc), changed_by=actor.id, reason=f"Requested {add_on.code}", change_metadata={"tenant_add_on_id": str(item.id)}))
    await session.commit()
    return {"message": "Add-on request created; access awaits verified payment or platform approval.", "tenant_add_on_id": str(item.id)}


@router.delete("/add-ons/{tenant_add_on_id}")
async def remove_add_on(tenant_add_on_id: UUID, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_rls_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    item = await session.scalar(select(TenantAddOn).where(TenantAddOn.id == tenant_add_on_id, TenantAddOn.tenant_id == actor.tenant_id))
    if item is None:
        raise HTTPException(404, detail="Add-on not found")
    item.status = "CANCELLED"
    subscription, _ = await _current(session, actor.tenant_id)
    subscription.entitlement_version += 1
    session.add(SubscriptionChangeHistory(tenant_id=actor.tenant_id, change_type="ADD_ON_REMOVED", effective_at=datetime.now(timezone.utc), changed_by=actor.id, change_metadata={"tenant_add_on_id": str(item.id)}))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(actor.tenant_id)
    return {"message": "Add-on removed"}


@router.get("/billing", response_model=list[BillingTransactionResponse])
async def billing_history(actor: Annotated[CurrentUser, Depends(require_permissions("billing.read"))], session: Annotated[AsyncSession, Depends(get_rls_db)]) -> list[BillingTransactionResponse]:
    rows = list((await session.execute(select(BillingTransaction).where(BillingTransaction.tenant_id == actor.tenant_id).order_by(BillingTransaction.created_at.desc()))).scalars())
    return [BillingTransactionResponse.model_validate(row, from_attributes=True) for row in rows]
