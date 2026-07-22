from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SubscriptionAccess:
    status: str
    can_read: bool
    can_write: bool
    reason_code: str | None = None


def evaluate_subscription_status(
    status: str,
    *,
    now: datetime | None = None,
    trial_ends_at: datetime | None = None,
    current_period_end: datetime | None = None,
    grace_period_ends_at: datetime | None = None,
) -> SubscriptionAccess:
    now = now or datetime.now(timezone.utc)
    if status == "TRIALING":
        if trial_ends_at is not None and trial_ends_at <= now:
            return SubscriptionAccess("EXPIRED", True, False, "SUBSCRIPTION_EXPIRED")
        return SubscriptionAccess(status, True, True)
    if status == "ACTIVE":
        return SubscriptionAccess(status, True, True)
    if status == "PAST_DUE":
        if grace_period_ends_at is not None and grace_period_ends_at > now:
            return SubscriptionAccess("GRACE_PERIOD", True, False, "SUBSCRIPTION_PAST_DUE")
        return SubscriptionAccess(status, True, False, "SUBSCRIPTION_PAST_DUE")
    if status == "GRACE_PERIOD":
        return SubscriptionAccess(status, True, False, "SUBSCRIPTION_PAST_DUE")
    if status == "CANCELLED" and current_period_end is not None and current_period_end > now:
        return SubscriptionAccess(status, True, True)
    if status == "SUSPENDED":
        return SubscriptionAccess(status, True, False, "SUBSCRIPTION_SUSPENDED")
    if status in {"CANCELLED", "EXPIRED"}:
        return SubscriptionAccess("EXPIRED", True, False, "SUBSCRIPTION_EXPIRED")
    return SubscriptionAccess(status, False, False, "SUBSCRIPTION_INACTIVE")
