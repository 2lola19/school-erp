from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db, get_redis, require_permissions
from app.models.core import AuditLog, Tenant
from app.models.subscriptions import AddOn, AddOnEntitlement, PlanEntitlement, SubscriptionFeature, SubscriptionModule, SubscriptionPlan, TenantAddOn, TenantEntitlementOverride, TenantSubscription, SubscriptionChangeHistory
from app.schemas.auth import CurrentUser
from app.schemas.subscriptions import AddOnCreate, AddOnResponse, AddOnUpdate, EntitlementWrite, FeatureResponse, FeatureUpdate, ModuleResponse, OverrideCreate, PlanCreate, PlanResponse, PlanUpdate, PlatformSubscriptionWrite, TenantAddOnStatus
from app.services.entitlements import EntitlementService

router = APIRouter()


async def _target_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(404, detail="Tenant not found")
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
    return tenant


async def _bump_plan_subscribers(session: AsyncSession, redis_client: redis.Redis, plan_id: UUID) -> None:
    tenants = list((await session.execute(select(Tenant.id))).scalars())
    for tenant_id in tenants:
        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
        subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.plan_id == plan_id, TenantSubscription.is_current.is_(True)))
        if subscription:
            subscription.entitlement_version += 1
            await EntitlementService(session, redis_client).invalidate_cache(tenant_id)


async def _bump_all_subscriptions(session: AsyncSession, redis_client: redis.Redis) -> None:
    tenants = list((await session.execute(select(Tenant.id))).scalars())
    for tenant_id in tenants:
        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
        subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True)))
        if subscription:
            subscription.entitlement_version += 1
            await EntitlementService(session, redis_client).invalidate_cache(tenant_id)


@router.get("/plans", response_model=list[PlanResponse])
async def plans(actor: Annotated[CurrentUser, Depends(require_permissions("plans.read"))], session: Annotated[AsyncSession, Depends(get_db)]) -> list[SubscriptionPlan]:
    return list((await session.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.display_order))).scalars())


@router.get("/modules", response_model=list[ModuleResponse])
async def modules(actor: Annotated[CurrentUser, Depends(require_permissions("plans.read"))], session: Annotated[AsyncSession, Depends(get_db)]) -> list[SubscriptionModule]:
    return list((await session.execute(select(SubscriptionModule).order_by(SubscriptionModule.display_order, SubscriptionModule.code))).scalars())


@router.get("/features", response_model=list[FeatureResponse])
async def features(actor: Annotated[CurrentUser, Depends(require_permissions("plans.read"))], session: Annotated[AsyncSession, Depends(get_db)]) -> list[SubscriptionFeature]:
    return list((await session.execute(select(SubscriptionFeature).order_by(SubscriptionFeature.code))).scalars())


@router.patch("/features/{feature_id}", response_model=FeatureResponse)
async def update_feature(feature_id: UUID, payload: FeatureUpdate, actor: Annotated[CurrentUser, Depends(require_permissions("plans.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> SubscriptionFeature:
    feature = await session.get(SubscriptionFeature, feature_id)
    if feature is None:
        raise HTTPException(404, detail="Feature not found")
    changes = payload.model_dump(exclude_unset=True)
    old = {key: getattr(feature, key) for key in changes}
    for key, value in changes.items():
        setattr(feature, key, value)
    await _bump_all_subscriptions(session, redis_client)
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(actor.tenant_id)})
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="FEATURE_UPDATED", entity_name="SUBSCRIPTION_FEATURE", entity_id=str(feature.id), old_values=old, new_values=changes))
    await session.commit()
    await session.refresh(feature)
    return feature


@router.post("/plans", response_model=PlanResponse, status_code=201)
async def create_plan(payload: PlanCreate, actor: Annotated[CurrentUser, Depends(require_permissions("plans.manage"))], session: Annotated[AsyncSession, Depends(get_db)]) -> SubscriptionPlan:
    if await session.scalar(select(SubscriptionPlan.id).where(SubscriptionPlan.code == payload.code)):
        raise HTTPException(409, detail="Plan code already exists")
    plan = SubscriptionPlan(**payload.model_dump())
    session.add(plan)
    await session.flush()
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="PLAN_CREATED", entity_name="SUBSCRIPTION_PLAN", entity_id=str(plan.id), new_values=payload.model_dump(mode="json")))
    await session.commit()
    await session.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(plan_id: UUID, payload: PlanUpdate, actor: Annotated[CurrentUser, Depends(require_permissions("plans.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> SubscriptionPlan:
    plan = await session.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    changes = payload.model_dump(exclude_unset=True)
    old = {key: getattr(plan, key) for key in changes}
    for key, value in changes.items():
        setattr(plan, key, value)
    await _bump_plan_subscribers(session, redis_client, plan.id)
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(actor.tenant_id)})
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="PLAN_UPDATED", entity_name="SUBSCRIPTION_PLAN", entity_id=str(plan.id), old_values=old, new_values=changes))
    await session.commit()
    await session.refresh(plan)
    return plan


@router.post("/plans/{plan_id}/entitlements", status_code=201)
async def set_plan_entitlement(plan_id: UUID, payload: EntitlementWrite, actor: Annotated[CurrentUser, Depends(require_permissions("plans.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    plan = await session.get(SubscriptionPlan, plan_id)
    feature = await session.scalar(select(SubscriptionFeature).where(SubscriptionFeature.code == payload.feature_code))
    if plan is None or feature is None:
        raise HTTPException(404, detail="Plan or feature not found")
    item = await session.scalar(select(PlanEntitlement).where(PlanEntitlement.plan_id == plan.id, PlanEntitlement.feature_id == feature.id))
    old: dict[str, Any] = {}
    if item is None:
        item = PlanEntitlement(plan_id=plan.id, feature_id=feature.id)
        session.add(item)
    else:
        old = {"is_enabled": item.is_enabled, "value": item.value}
    item.is_enabled = payload.is_enabled
    item.value = payload.value
    await _bump_plan_subscribers(session, redis_client, plan.id)
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(actor.tenant_id)})
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="PLAN_ENTITLEMENT_CHANGED", entity_name="PLAN_ENTITLEMENT", entity_id=str(item.id), old_values=old, new_values=payload.model_dump(mode="json")))
    await session.commit()
    return {"message": "Plan entitlement updated"}


@router.post("/add-ons", response_model=AddOnResponse, status_code=201)
async def create_add_on(payload: AddOnCreate, actor: Annotated[CurrentUser, Depends(require_permissions("add_ons.manage"))], session: Annotated[AsyncSession, Depends(get_db)]) -> AddOn:
    if await session.scalar(select(AddOn.id).where(AddOn.code == payload.code)):
        raise HTTPException(409, detail="Add-on code already exists")
    item = AddOn(**payload.model_dump())
    session.add(item)
    await session.flush()
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="ADD_ON_CREATED", entity_name="ADD_ON", entity_id=str(item.id), new_values=payload.model_dump(mode="json")))
    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/add-ons/{add_on_id}", response_model=AddOnResponse)
async def update_add_on(add_on_id: UUID, payload: AddOnUpdate, actor: Annotated[CurrentUser, Depends(require_permissions("add_ons.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> AddOn:
    item = await session.get(AddOn, add_on_id)
    if item is None:
        raise HTTPException(404, detail="Add-on not found")
    changes = payload.model_dump(exclude_unset=True)
    old = {key: getattr(item, key) for key in changes}
    for key, value in changes.items():
        setattr(item, key, value)
    await _bump_all_subscriptions(session, redis_client)
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(actor.tenant_id)})
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="ADD_ON_UPDATED", entity_name="ADD_ON", entity_id=str(item.id), old_values=old, new_values=changes))
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/add-ons/{add_on_id}/entitlements", status_code=201)
async def set_add_on_entitlement(add_on_id: UUID, payload: EntitlementWrite, actor: Annotated[CurrentUser, Depends(require_permissions("add_ons.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    add_on = await session.get(AddOn, add_on_id)
    feature = await session.scalar(select(SubscriptionFeature).where(SubscriptionFeature.code == payload.feature_code))
    if add_on is None or feature is None:
        raise HTTPException(404, detail="Add-on or feature not found")
    item = await session.scalar(select(AddOnEntitlement).where(AddOnEntitlement.add_on_id == add_on.id, AddOnEntitlement.feature_id == feature.id))
    if item is None:
        item = AddOnEntitlement(add_on_id=add_on.id, feature_id=feature.id)
        session.add(item)
    item.is_enabled = payload.is_enabled
    item.value = payload.value
    await _bump_all_subscriptions(session, redis_client)
    await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(actor.tenant_id)})
    session.add(AuditLog(tenant_id=actor.tenant_id, user_id=actor.id, action="ADD_ON_ENTITLEMENT_CHANGED", entity_name="ADD_ON_ENTITLEMENT", entity_id=str(item.id), new_values=payload.model_dump(mode="json")))
    await session.commit()
    return {"message": "Add-on entitlement updated"}


@router.get("/subscriptions")
async def subscriptions(actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.read"))], session: Annotated[AsyncSession, Depends(get_db)]) -> list[dict[str, Any]]:
    tenants = list((await session.execute(select(Tenant))).scalars())
    result = []
    for tenant in tenants:
        await _target_tenant(session, tenant.id)
        row = (await session.execute(select(TenantSubscription, SubscriptionPlan).join(SubscriptionPlan, SubscriptionPlan.id == TenantSubscription.plan_id).where(TenantSubscription.tenant_id == tenant.id, TenantSubscription.is_current.is_(True)))).one_or_none()
        if row:
            subscription, plan = row
            result.append({"tenant_id": str(tenant.id), "tenant_name": tenant.name, "subscription_id": str(subscription.id), "plan_code": plan.code, "status": subscription.status, "entitlement_version": subscription.entitlement_version})
    return result


@router.post("/tenants/{tenant_id}/subscription", status_code=201)
@router.patch("/tenants/{tenant_id}/subscription")
async def assign_subscription(tenant_id: UUID, payload: PlatformSubscriptionWrite, actor: Annotated[CurrentUser, Depends(require_permissions("subscriptions.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    plan = await session.get(SubscriptionPlan, payload.plan_id)
    if plan is None:
        raise HTTPException(404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    await _target_tenant(session, tenant_id)
    current = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True)).with_for_update())
    old_plan_id = current.plan_id if current else None
    if current is None:
        current = TenantSubscription(tenant_id=tenant_id, plan_id=plan.id, status=payload.status, starts_at=payload.starts_at or datetime.now(timezone.utc), current_period_start=payload.starts_at or datetime.now(timezone.utc), current_period_end=payload.current_period_end)
        session.add(current)
        change_type = "CREATED"
    else:
        current.plan_id = plan.id
        current.status = payload.status
        current.current_period_end = payload.current_period_end
        current.scheduled_plan_id = None
        current.scheduled_change_at = None
        current.entitlement_version += 1
        change_type = "UPGRADED" if old_plan_id != plan.id else "STATUS_CHANGED"
    session.add(SubscriptionChangeHistory(tenant_id=tenant_id, old_plan_id=old_plan_id, new_plan_id=plan.id, change_type=change_type, effective_at=datetime.now(timezone.utc), changed_by=actor.id, reason=payload.reason))
    session.add(AuditLog(tenant_id=tenant_id, user_id=actor.id, action="SUBSCRIPTION_ASSIGNED", entity_name="TENANT_SUBSCRIPTION", entity_id=str(current.id), reason=payload.reason, old_values={"plan_id": str(old_plan_id) if old_plan_id else None}, new_values={"plan_id": str(plan.id), "status": payload.status}))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(tenant_id)
    return {"message": "Tenant subscription updated"}


@router.post("/tenants/{tenant_id}/entitlement-overrides", status_code=201)
async def create_override(tenant_id: UUID, payload: OverrideCreate, actor: Annotated[CurrentUser, Depends(require_permissions("tenant_entitlements.override"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    feature = await session.scalar(select(SubscriptionFeature).where(SubscriptionFeature.code == payload.feature_code))
    if feature is None:
        raise HTTPException(404, detail="Feature not found")
    await _target_tenant(session, tenant_id)
    item = TenantEntitlementOverride(tenant_id=tenant_id, feature_id=feature.id, override_type=payload.override_type, value=payload.value, starts_at=payload.starts_at or datetime.now(timezone.utc), ends_at=payload.ends_at, reason=payload.reason, approved_by=actor.id, created_by=actor.id)
    session.add(item)
    subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True)).with_for_update())
    if subscription:
        subscription.entitlement_version += 1
    await session.flush()
    session.add(AuditLog(tenant_id=tenant_id, user_id=actor.id, action="TENANT_OVERRIDE_CREATED", entity_name="TENANT_ENTITLEMENT_OVERRIDE", entity_id=str(item.id), reason=payload.reason, new_values=payload.model_dump(mode="json")))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(tenant_id)
    return {"message": "Tenant override created", "override_id": str(item.id)}


@router.delete("/tenants/{tenant_id}/entitlement-overrides/{override_id}")
async def revoke_override(tenant_id: UUID, override_id: UUID, actor: Annotated[CurrentUser, Depends(require_permissions("tenant_entitlements.override"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    await _target_tenant(session, tenant_id)
    item = await session.scalar(select(TenantEntitlementOverride).where(TenantEntitlementOverride.id == override_id, TenantEntitlementOverride.tenant_id == tenant_id))
    if item is None:
        raise HTTPException(404, detail="Override not found")
    item.ends_at = datetime.now(timezone.utc)
    subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True)).with_for_update())
    if subscription:
        subscription.entitlement_version += 1
    session.add(AuditLog(tenant_id=tenant_id, user_id=actor.id, action="TENANT_OVERRIDE_REVOKED", entity_name="TENANT_ENTITLEMENT_OVERRIDE", entity_id=str(item.id)))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(tenant_id)
    return {"message": "Tenant override revoked"}


@router.patch("/tenants/{tenant_id}/add-ons/{tenant_add_on_id}")
async def set_tenant_add_on_status(tenant_id: UUID, tenant_add_on_id: UUID, payload: TenantAddOnStatus, actor: Annotated[CurrentUser, Depends(require_permissions("add_ons.manage"))], session: Annotated[AsyncSession, Depends(get_db)], redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> dict[str, str]:
    await _target_tenant(session, tenant_id)
    item = await session.scalar(select(TenantAddOn).where(TenantAddOn.id == tenant_add_on_id, TenantAddOn.tenant_id == tenant_id).with_for_update())
    if item is None:
        raise HTTPException(404, detail="Tenant add-on not found")
    if payload.status not in {"ACTIVE", "SUSPENDED", "EXPIRED", "CANCELLED"}:
        raise HTTPException(422, detail="Invalid add-on status")
    old_status = item.status
    item.status = payload.status
    subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id, TenantSubscription.is_current.is_(True)).with_for_update())
    if subscription:
        subscription.entitlement_version += 1
    session.add(SubscriptionChangeHistory(tenant_id=tenant_id, change_type="ADD_ON_ACTIVATED" if payload.status == "ACTIVE" else "ADD_ON_STATUS_CHANGED", effective_at=datetime.now(timezone.utc), changed_by=actor.id, reason=payload.reason, change_metadata={"tenant_add_on_id": str(item.id), "old_status": old_status, "new_status": payload.status}))
    session.add(AuditLog(tenant_id=tenant_id, user_id=actor.id, action="TENANT_ADD_ON_STATUS_CHANGED", entity_name="TENANT_ADD_ON", entity_id=str(item.id), reason=payload.reason, old_values={"status": old_status}, new_values={"status": payload.status}))
    await session.commit()
    await EntitlementService(session, redis_client).invalidate_cache(tenant_id)
    return {"message": "Tenant add-on status updated"}
