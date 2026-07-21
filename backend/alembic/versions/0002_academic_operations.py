"""Add academic administration and official-record workflows.

Revision ID: 0002_academic_operations
Revises: 0001_initial_schema
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.base_class import Base
from app.models import core  # noqa: F401

revision = "0002_academic_operations"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

NEW_TENANT_TABLES = (
    "academic_sessions",
    "academic_terms",
    "guardians",
    "student_guardians",
    "applicants",
    "timetable_entries",
    "exam_cycles",
    "assessment_components",
    "report_cards",
    "report_card_entries",
)


def _constraint_names(inspector: sa.Inspector, table: str) -> set[str]:
    names = {
        item["name"]
        for item in inspector.get_unique_constraints(table)
        if item.get("name")
    }
    names.update(
        item["name"]
        for item in inspector.get_check_constraints(table)
        if item.get("name")
    )
    return names


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [
        Base.metadata.tables[name]
        for name in NEW_TENANT_TABLES
        if name not in existing_tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables, checkfirst=True)

    inspector = sa.inspect(bind)
    attendance_columns = {column["name"] for column in inspector.get_columns("attendance")}
    if "workflow_status" not in attendance_columns:
        op.add_column(
            "attendance",
            sa.Column(
                "workflow_status",
                sa.String(length=20),
                server_default="DRAFT",
                nullable=False,
            ),
        )
    if "recorded_by" not in attendance_columns:
        op.add_column(
            "attendance",
            sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_attendance_recorded_by_users",
            "attendance",
            "users",
            ["recorded_by"],
            ["id"],
        )
    if "approved_by" not in attendance_columns:
        op.add_column(
            "attendance",
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_attendance_approved_by_users",
            "attendance",
            "users",
            ["approved_by"],
            ["id"],
        )
    if "correction_reason" not in attendance_columns:
        op.add_column("attendance", sa.Column("correction_reason", sa.Text(), nullable=True))

    inspector = sa.inspect(bind)
    attendance_constraints = _constraint_names(inspector, "attendance")
    if "uq_daily_attendance" not in attendance_constraints:
        op.create_unique_constraint(
            "uq_daily_attendance",
            "attendance",
            ["tenant_id", "student_id", "classroom_id", "date"],
        )
    if "ck_attendance_status" not in attendance_constraints:
        op.create_check_constraint(
            "ck_attendance_status",
            "attendance",
            "status IN ('PRESENT','ABSENT','LATE','EXCUSED')",
        )
    if "ck_attendance_workflow_status" not in attendance_constraints:
        op.create_check_constraint(
            "ck_attendance_workflow_status",
            "attendance",
            "workflow_status IN ('DRAFT','SUBMITTED','APPROVED')",
        )

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
    op.drop_constraint("ck_attendance_workflow_status", "attendance", type_="check")
    op.drop_constraint("ck_attendance_status", "attendance", type_="check")
    op.drop_constraint("uq_daily_attendance", "attendance", type_="unique")
    op.drop_constraint("fk_attendance_approved_by_users", "attendance", type_="foreignkey")
    op.drop_constraint("fk_attendance_recorded_by_users", "attendance", type_="foreignkey")
    op.drop_column("attendance", "correction_reason")
    op.drop_column("attendance", "approved_by")
    op.drop_column("attendance", "recorded_by")
    op.drop_column("attendance", "workflow_status")
    for table in reversed(NEW_TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"')
        op.drop_table(table)
