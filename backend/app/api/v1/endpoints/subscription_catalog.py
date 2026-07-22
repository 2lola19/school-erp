from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.models.subscriptions import AddOn, PlanEntitlement, SubscriptionFeature, SubscriptionModule, SubscriptionPlan
from app.schemas.subscriptions import AddOnResponse, FeatureEntitlementResponse, PlanResponse

router = APIRouter()


@router.get("/subscription-plans", response_model=list[PlanResponse])
async def list_plans(session: Annotated[AsyncSession, Depends(get_db)]) -> list[SubscriptionPlan]:
    return list((await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_public.is_(True), SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.display_order))).scalars())


@router.get("/subscription-plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: UUID, session: Annotated[AsyncSession, Depends(get_db)]) -> SubscriptionPlan:
    plan = await session.get(SubscriptionPlan, plan_id)
    if plan is None or not plan.is_public:
        raise HTTPException(404, detail={"code": "PLAN_NOT_FOUND", "message": "Plan not found."})
    return plan


@router.get("/subscription-plans/{plan_id}/features", response_model=list[FeatureEntitlementResponse])
async def get_plan_features(plan_id: UUID, session: Annotated[AsyncSession, Depends(get_db)]) -> list[FeatureEntitlementResponse]:
    rows = (await session.execute(select(PlanEntitlement, SubscriptionFeature, SubscriptionModule).join(SubscriptionFeature, SubscriptionFeature.id == PlanEntitlement.feature_id).join(SubscriptionModule, SubscriptionModule.id == SubscriptionFeature.module_id).where(PlanEntitlement.plan_id == plan_id))).all()
    return [FeatureEntitlementResponse(id=item.id, feature_id=feature.id, feature_code=feature.code, feature_name=feature.name, module_code=module.code, is_enabled=item.is_enabled, value=item.value) for item, feature, module in rows]


@router.get("/add-ons", response_model=list[AddOnResponse])
async def list_add_ons(session: Annotated[AsyncSession, Depends(get_db)]) -> list[AddOn]:
    return list((await session.execute(select(AddOn).where(AddOn.is_active.is_(True)).order_by(AddOn.name))).scalars())
