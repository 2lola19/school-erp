"""Correct tenant RLS policies for non-superuser application roles.

Revision ID: 0005_correct_rls_policies
Revises: 0004_subscription_entitlements
Create Date: 2026-07-22

The original policies were RESTRICTIVE without a PERMISSIVE policy. PostgreSQL
requires at least one permissive policy before restrictive policies can admit a
row, so a proper non-superuser application role would see no tenant data.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_correct_rls_policies"
down_revision = "0004_subscription_entitlements"
branch_labels = None
depends_on = None


def _tenant_tables() -> list[str]:
    inspector = sa.inspect(op.get_bind())
    return sorted(
        table
        for table in inspector.get_table_names()
        if table != "tenants" and "tenant_id" in {column["name"] for column in inspector.get_columns(table)}
    )


def _create_policy(table: str, policy_type: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"')
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON "{table}"
        AS {policy_type} FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
        """
    )


def upgrade() -> None:
    for table in _tenant_tables():
        _create_policy(table, "PERMISSIVE")


def downgrade() -> None:
    for table in _tenant_tables():
        _create_policy(table, "RESTRICTIVE")
