from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.entitlements import merge_entitlement_values
from app.services.subscription_changes import calculate_downgrade_impact
from app.services.subscription_status import evaluate_subscription_status


def test_entitlement_precedence_and_numerical_merging() -> None:
    values = merge_entitlement_values(
        {"finance.invoicing": False, "quota.active_students": 200},
        [({"finance.invoicing": True, "quota.active_students": 100}, 2)],
        [
            ("quota.active_students", "INCREASE_LIMIT", 50),
            ("medical.records", "GRANT", None),
            ("finance.invoicing", "DENY", None),
        ],
    )
    assert values["finance.invoicing"] is False
    assert values["medical.records"] is True
    assert Decimal(str(values["quota.active_students"])) == 450


def test_status_policy_preserves_reads_and_blocks_restricted_writes() -> None:
    now = datetime.now(timezone.utc)
    assert evaluate_subscription_status("ACTIVE", now=now).can_write
    assert not evaluate_subscription_status("SUSPENDED", now=now).can_write
    assert evaluate_subscription_status("SUSPENDED", now=now).can_read
    expired_trial = evaluate_subscription_status("TRIALING", now=now, trial_ends_at=now - timedelta(seconds=1))
    assert expired_trial.status == "EXPIRED"
    assert not expired_trial.can_write
    paid_cancel = evaluate_subscription_status("CANCELLED", now=now, current_period_end=now + timedelta(days=1))
    assert paid_cancel.can_write


def test_downgrade_impact_preserves_data_and_reports_over_limit() -> None:
    lost, decreases, over_limit = calculate_downgrade_impact(
        {"finance.invoicing": True, "students.manage": True, "quota.active_students": 1000},
        {"students.manage": True, "quota.active_students": 200},
        {"quota.active_students": 245},
    )
    assert lost == ["finance.invoicing"]
    assert decreases[0]["current_usage"] == 245
    assert decreases[0]["over_limit"] is True
    assert over_limit is True
