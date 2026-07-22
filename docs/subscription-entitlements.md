# Subscription and entitlement architecture

## Access decision

Operational API access requires tenant entitlement, subscription status, user
permission, tenant scope, and record scope. Frontend gates improve usability but
never authorize a request. Stable feature codes live in
`app/core/feature_registry.py`; plan names are never used as application logic.

Resolution order is default deny, plan entitlement, active add-on, active
tenant grant/value override, tenant denial, and finally the platform feature's
`is_active` security restriction. Explicit denials win. Effective values are
cached at `entitlements:{tenant_id}:{entitlement_version}`; every management
change increments the version and removes older keys.

## Status and data retention

`ACTIVE` and valid `TRIALING` subscriptions permit writes. `PAST_DUE`,
`GRACE_PERIOD`, `SUSPENDED`, and `EXPIRED` preserve controlled reads but block
operational writes. A cancelled subscription remains active until its paid
period ends. Expiry and downgrade never delete school data.

Downgrade preview reports lost features, reduced quotas, current usage,
read-only modules, and the effective date. Confirmed downgrades are scheduled;
over-limit data stays readable while further creation remains blocked.

## Quotas and add-ons

Active-student, active-staff, and campus limits use authoritative database
counts. Metered quotas use row-locked period counters plus append-only,
idempotent usage events. Quantity add-ons multiply numerical entitlement values.
Add-on requests remain `PENDING` until verified payment or platform approval.

## Billing security

School-fee `payments` remain separate from platform `billing_transactions`.
Paystack and Flutterwave adapters verify webhook signatures before persistence.
Events are unique by provider/event ID, processed in the background, track
attempts, and move to `DEAD_LETTER` after the configured attempt limit. A
subscription is not activated before a matching successful transaction is
verified. Live payment initialization is intentionally unavailable until real
provider credentials and commercial plan prices are configured.

## Operations

Run these in order:

```sh
python -m scripts.migration_preflight
alembic upgrade head
python -m scripts.seed_subscriptions
python -m scripts.sync_role_templates
```

Existing tenants without a subscription are grandfathered to Enterprise Plus
during the first seed so rollout does not cause an unplanned lockout. New
tenants receive the configured Starter trial. Review grandfathered tenants and
assign commercial plans before launch.

Use a non-superuser application database role in production. Migration 0005
corrects legacy restrictive-only RLS policies and forces RLS on every table with
a `tenant_id` column.
