import hashlib
import hmac
import json

import pytest

from app.services.billing_providers import FlutterwaveProvider, PaystackProvider


def test_paystack_signature_and_amount_parsing() -> None:
    secret = "paystack-test-secret"
    body = json.dumps({"event": "charge.success", "data": {"id": 12, "reference": "REF-1", "status": "success", "amount": 125000, "currency": "NGN"}}, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    event = PaystackProvider(secret).verify_and_parse_webhook(body, {"x-paystack-signature": signature})
    assert event.successful is True
    assert str(event.amount) == "1250"
    with pytest.raises(ValueError):
        PaystackProvider(secret).verify_and_parse_webhook(body, {"x-paystack-signature": "forged"})


def test_flutterwave_hash_is_required() -> None:
    body = json.dumps({"event": "charge.completed", "data": {"id": 99, "tx_ref": "REF-2", "status": "successful", "amount": 3000, "currency": "NGN"}}).encode()
    event = FlutterwaveProvider("verified-hash").verify_and_parse_webhook(body, {"verif-hash": "verified-hash"})
    assert event.reference == "REF-2"
    with pytest.raises(ValueError):
        FlutterwaveProvider("verified-hash").verify_and_parse_webhook(body, {})
