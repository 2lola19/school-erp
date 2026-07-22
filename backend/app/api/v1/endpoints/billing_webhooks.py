from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.models.core import Tenant
from app.models.subscriptions import BillingTransaction, BillingWebhookEvent
from app.services.billing_providers import configured_provider
from app.services.billing_webhooks import process_billing_webhook

router = APIRouter()


@router.post("/{provider}", status_code=202)
async def receive_webhook(provider: str, request: Request, tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    body = await request.body()
    try:
        adapter = configured_provider(provider)
        verified = adapter.verify_and_parse_webhook(body, {key.lower(): value for key, value in request.headers.items()})
    except LookupError as exc:
        raise HTTPException(503, detail={"code": "BILLING_PROVIDER_UNAVAILABLE", "message": str(exc)})
    except (ValueError, TypeError):
        raise HTTPException(401, detail={"code": "INVALID_WEBHOOK_SIGNATURE", "message": "Webhook signature verification failed."})
    if not verified.reference or not verified.event_id:
        raise HTTPException(422, detail="Webhook event is missing its transaction reference")

    tenants = list((await session.execute(select(Tenant.id))).scalars())
    transaction = None
    tenant_id = None
    for candidate in tenants:
        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(candidate)})
        transaction = await session.scalar(select(BillingTransaction).where(BillingTransaction.tenant_id == candidate, BillingTransaction.provider == provider.upper(), BillingTransaction.external_reference == verified.reference))
        if transaction:
            tenant_id = candidate
            break
    if transaction is None or tenant_id is None:
        raise HTTPException(404, detail="Billing transaction not found")
    existing = await session.scalar(select(BillingWebhookEvent).where(BillingWebhookEvent.provider == provider.upper(), BillingWebhookEvent.external_event_id == verified.event_id))
    if existing:
        return {"message": "Webhook already accepted"}
    event = BillingWebhookEvent(tenant_id=tenant_id, provider=provider.upper(), external_event_id=verified.event_id, event_type=verified.event_type, payload=verified.payload, processing_status="PENDING")
    session.add(event)
    await session.commit()
    tasks.add_task(process_billing_webhook, tenant_id, event.id)
    return {"message": "Webhook accepted"}
