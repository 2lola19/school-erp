import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from app.core.config import settings


@dataclass(frozen=True)
class VerifiedBillingEvent:
    event_id: str
    event_type: str
    reference: str
    successful: bool
    amount: Decimal | None
    currency: str | None
    payload: dict[str, Any]


class BillingProvider(Protocol):
    async def create_customer(self, **kwargs: Any) -> dict[str, Any]: ...
    async def initialize_payment(self, **kwargs: Any) -> dict[str, Any]: ...
    async def create_subscription(self, **kwargs: Any) -> dict[str, Any]: ...
    async def cancel_subscription(self, **kwargs: Any) -> dict[str, Any]: ...
    async def verify_transaction(self, reference: str) -> dict[str, Any]: ...
    def verify_and_parse_webhook(self, body: bytes, headers: dict[str, str]) -> VerifiedBillingEvent: ...


class WebhookOnlyProvider:
    async def create_customer(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("Live billing operations are unavailable until provider credentials and commercial configuration are approved")

    initialize_payment = create_customer
    create_subscription = create_customer
    cancel_subscription = create_customer

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        raise RuntimeError("Remote verification is unavailable until provider credentials are configured")


class PaystackProvider(WebhookOnlyProvider):
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def verify_and_parse_webhook(self, body: bytes, headers: dict[str, str]) -> VerifiedBillingEvent:
        supplied = headers.get("x-paystack-signature", "")
        expected = hmac.new(self.secret_key.encode(), body, hashlib.sha512).hexdigest()
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise ValueError("Invalid Paystack webhook signature")
        payload = json.loads(body)
        data = payload.get("data", {})
        reference = str(data.get("reference", ""))
        event_id = str(data.get("id") or reference)
        amount = Decimal(str(data["amount"])) / 100 if data.get("amount") is not None else None
        return VerifiedBillingEvent(event_id, str(payload.get("event", "unknown")), reference, data.get("status") == "success", amount, data.get("currency"), payload)


class FlutterwaveProvider(WebhookOnlyProvider):
    def __init__(self, secret_hash: str):
        self.secret_hash = secret_hash

    def verify_and_parse_webhook(self, body: bytes, headers: dict[str, str]) -> VerifiedBillingEvent:
        supplied = headers.get("verif-hash", "")
        if not supplied or not hmac.compare_digest(supplied, self.secret_hash):
            raise ValueError("Invalid Flutterwave webhook signature")
        payload = json.loads(body)
        data = payload.get("data", {})
        reference = str(data.get("tx_ref", ""))
        event_id = str(data.get("id") or reference)
        amount = Decimal(str(data["amount"])) if data.get("amount") is not None else None
        successful = str(data.get("status", "")).lower() in {"successful", "success"}
        return VerifiedBillingEvent(event_id, str(payload.get("event") or payload.get("type") or "unknown"), reference, successful, amount, data.get("currency"), payload)


def configured_provider(name: str) -> BillingProvider:
    normalized = name.upper()
    if normalized == "PAYSTACK" and settings.PAYSTACK_SECRET_KEY:
        return PaystackProvider(settings.PAYSTACK_SECRET_KEY)
    if normalized == "FLUTTERWAVE" and settings.FLUTTERWAVE_SECRET_HASH:
        return FlutterwaveProvider(settings.FLUTTERWAVE_SECRET_HASH)
    raise LookupError(f"{normalized} billing is not configured")
