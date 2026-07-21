"""Create the stable academic and identity baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-21

The repository previously contained an unreleased migration chain that created
grades before students and classrooms. This baseline intentionally replaces
that broken prototype history.
"""

from alembic import op

from app.db.base_class import Base
from app.models import core  # noqa: F401 - registers all metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "school_profiles",
    "roles",
    "role_permissions",
    "permission_bundles",
    "permission_bundle_permissions",
    "role_permission_bundles",
    "users",
    "user_permissions",
    "staff",
    "staff_role_assignments",
    "role_conflicts",
    "role_delegation_rules",
    "teachers",
    "students",
    "classrooms",
    "enrollments",
    "subjects",
    "grades",
    "attendance",
    "audit_logs",
)


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

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
        CREATE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation")
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    Base.metadata.drop_all(bind=op.get_bind())
