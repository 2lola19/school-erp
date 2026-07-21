"""Add finance, welfare, student-life, and school-service modules.

Revision ID: 0003_school_services
Revises: 0002_academic_operations
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

from app.db.base_class import Base
from app.models import core  # noqa: F401

revision = "0003_school_services"
down_revision = "0002_academic_operations"
branch_labels = None
depends_on = None

NEW_TENANT_TABLES = (
    "fee_schedules",
    "invoices",
    "payments",
    "refund_requests",
    "health_records",
    "health_encounters",
    "medical_consents",
    "emergency_health_flags",
    "break_glass_access",
    "counselling_cases",
    "counselling_encounters",
    "library_items",
    "library_loans",
    "transport_routes",
    "transport_assignments",
    "hostels",
    "hostel_rooms",
    "hostel_assignments",
    "activities",
    "activity_enrollments",
    "activity_attendance",
    "activity_achievements",
)


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    missing_tables = [
        Base.metadata.tables[name]
        for name in NEW_TENANT_TABLES
        if name not in existing_tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables, checkfirst=True)

    for table in NEW_TENANT_TABLES:
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


def downgrade() -> None:
    for table in reversed(NEW_TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"')
        op.drop_table(table)
