from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.core import AuditLog
from app.models.subscriptions import BillingTransaction, BillingWebhookEvent, SubscriptionChangeHistory, TenantSubscription
from app.services.entitlements import EntitlementService


async def process_billing_webhook(tenant_id: UUID, event_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT set_config('app.current_tenant', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
        event = await session.scalar(select(BillingWebhookEvent).where(BillingWebhookEvent.id == event_id, BillingWebhookEvent.tenant_id == tenant_id).with_for_update())
        if event is None or event.processing_status == "PROCESSED":
            return
        event.attempts += 1
        try:
            data = event.payload.get("data", {})
            reference = str(data.get("reference") or data.get("tx_ref") or "")
            transaction = await session.scalar(select(BillingTransaction).where(BillingTransaction.tenant_id == tenant_id, BillingTransaction.provider == event.provider, BillingTransaction.external_reference == reference).with_for_update())
            if transaction is None:
                raise ValueError("Billing transaction not found")
            successful = str(data.get("status", "")).lower() in {"success", "successful"}
            if not successful:
                transaction.status = "FAILED"
            elif transaction.status != "VERIFIED":
                transaction.status = "VERIFIED"
                transaction.paid_at = datetime.now(timezone.utc)
                subscription = await session.scalar(select(TenantSubscription).where(TenantSubscription.id == transaction.subscription_id).with_for_update())
                target_plan_id = transaction.transaction_metadata.get("target_plan_id")
                if subscription is not None and target_plan_id:
                    old_plan_id = subscription.plan_id
                    subscription.plan_id = UUID(target_plan_id)
                    subscription.status = "ACTIVE"
                    subscription.entitlement_version += 1
                    session.add(SubscriptionChangeHistory(tenant_id=tenant_id, old_plan_id=old_plan_id, new_plan_id=subscription.plan_id, change_type="UPGRADED", effective_at=datetime.now(timezone.utc), reason="Verified billing webhook", change_metadata={"billing_transaction_id": str(transaction.id)}))
                session.add(AuditLog(tenant_id=tenant_id, action="BILLING_TRANSACTION_VERIFIED", entity_name="BILLING_TRANSACTION", entity_id=str(transaction.id), new_values={"provider": event.provider, "reference": reference}))
            event.processing_status = "PROCESSED"
            event.processed_at = datetime.now(timezone.utc)
            event.last_error = None
            session.add(AuditLog(tenant_id=tenant_id, action="PAYMENT_WEBHOOK_PROCESSED", entity_name="BILLING_WEBHOOK_EVENT", entity_id=str(event.id)))
            await session.commit()
            client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                await EntitlementService(session, client).invalidate_cache(tenant_id)
            finally:
                await client.aclose()
        except Exception as exc:
            event.last_error = str(exc)[:2000]
            event.processing_status = "DEAD_LETTER" if event.attempts >= settings.BILLING_WEBHOOK_MAX_ATTEMPTS else "RETRY"
            await session.commit()
