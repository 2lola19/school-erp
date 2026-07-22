"""Harden public-schema access for the dedicated backend role.

Revision ID: 0006_harden_database_access
Revises: 0005_correct_rls_policies
Create Date: 2026-07-22
"""

from alembic import op

revision = "0006_harden_database_access"
down_revision = "0005_correct_rls_policies"
branch_labels = None
depends_on = None

CATALOG_TABLES = (
    "tenants",
    "permissions",
    "subscription_plans",
    "subscription_modules",
    "subscription_features",
    "plan_entitlements",
    "add_ons",
    "add_on_entitlements",
)


def upgrade() -> None:
    op.execute(
        """
        DO $role$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOREPLICATION NOBYPASSRLS NOINHERIT;
            END IF;
        END
        $role$
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_runtime")
    op.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_runtime")
    op.execute("REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT EXECUTE ON FUNCTIONS TO app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC"
    )

    op.execute(
        """
        DO $api_roles$
        DECLARE
            role_name text;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I',
                        role_name
                    );
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I',
                        role_name
                    );
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM %I',
                        role_name
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL ON TABLES FROM %I',
                        role_name
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL ON SEQUENCES FROM %I',
                        role_name
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL ON FUNCTIONS FROM %I',
                        role_name
                    );
                END IF;
            END LOOP;
        END
        $api_roles$
        """
    )
    op.execute(
        """
        DO $tenant_policies$
        DECLARE
            policy_row record;
        BEGIN
            FOR policy_row IN
                SELECT schemaname, tablename
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND policyname = 'tenant_isolation_policy'
            LOOP
                EXECUTE format(
                    'ALTER POLICY tenant_isolation_policy ON %I.%I TO app_runtime',
                    policy_row.schemaname,
                    policy_row.tablename
                );
            END LOOP;
        END
        $tenant_policies$
        """
    )

    for table in CATALOG_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"""
            CREATE POLICY backend_catalog_access ON "{table}"
            AS PERMISSIVE FOR ALL TO app_runtime
            USING (true) WITH CHECK (true)
            """
        )

    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alembic_version FORCE ROW LEVEL SECURITY")
    op.execute("ALTER FUNCTION prevent_audit_log_mutation() SET search_path = ''")
    op.execute(
        "ALTER FUNCTION prevent_subscription_history_mutation() SET search_path = ''"
    )
    op.execute("REVOKE ALL ON FUNCTION prevent_audit_log_mutation() FROM PUBLIC")
    op.execute(
        "REVOKE ALL ON FUNCTION prevent_subscription_history_mutation() FROM PUBLIC"
    )
    op.execute("GRANT EXECUTE ON FUNCTION prevent_audit_log_mutation() TO app_runtime")
    op.execute(
        "GRANT EXECUTE ON FUNCTION prevent_subscription_history_mutation() TO app_runtime"
    )


def downgrade() -> None:
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE EXECUTE ON FUNCTIONS FROM app_runtime"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO PUBLIC"
    )
    op.execute("GRANT EXECUTE ON FUNCTION prevent_audit_log_mutation() TO PUBLIC")
    op.execute(
        "GRANT EXECUTE ON FUNCTION prevent_subscription_history_mutation() TO PUBLIC"
    )
    op.execute("ALTER FUNCTION prevent_audit_log_mutation() RESET search_path")
    op.execute(
        "ALTER FUNCTION prevent_subscription_history_mutation() RESET search_path"
    )
    op.execute("ALTER TABLE alembic_version NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
    for table in reversed(CATALOG_TABLES):
        op.execute(f'DROP POLICY IF EXISTS backend_catalog_access ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    op.execute(
        """
        DO $tenant_policies$
        DECLARE
            policy_row record;
        BEGIN
            FOR policy_row IN
                SELECT schemaname, tablename
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND policyname = 'tenant_isolation_policy'
            LOOP
                EXECUTE format(
                    'ALTER POLICY tenant_isolation_policy ON %I.%I TO PUBLIC',
                    policy_row.schemaname,
                    policy_row.tablename
                );
            END LOOP;
        END
        $tenant_policies$
        """
    )
