"""Add subscription, entitlement, quota, add-on, and billing control.

Revision ID: 0004_subscription_entitlements
Revises: 0003_school_services
Create Date: 2026-07-22
"""

import sqlalchemy as sa
from alembic import op

from app.db.base_class import Base
from app.models import core, subscriptions  # noqa: F401

revision = "0004_subscription_entitlements"
down_revision = "0003_school_services"
branch_labels = None
depends_on = None

CATALOG_TABLES = (
    "subscription_plans",
    "subscription_modules",
    "subscription_features",
    "plan_entitlements",
    "add_ons",
    "add_on_entitlements",
)

TENANT_TABLES = (
    "tenant_subscriptions",
    "tenant_add_ons",
    "tenant_entitlement_overrides",
    "usage_counters",
    "usage_events",
    "subscription_change_history",
    "billing_transactions",
    "billing_webhook_events",
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    tables = [
        Base.metadata.tables[name]
        for name in (*CATALOG_TABLES, *TENANT_TABLES)
        if name not in existing
    ]
    if tables:
        Base.metadata.create_all(bind=bind, tables=tables, checkfirst=True)

    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON "{table}"
            AS RESTRICTIVE FOR ALL
            USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
            """
        )

    op.execute(
        """
        CREATE FUNCTION prevent_subscription_history_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'subscription history is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("subscription_change_history", "usage_events"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION prevent_subscription_history_mutation()
            """
        )


def downgrade() -> None:
    for table in ("usage_events", "subscription_change_history"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_subscription_history_mutation")
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"')
        op.drop_table(table)
    for table in reversed(CATALOG_TABLES):
        op.drop_table(table)
