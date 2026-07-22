"""Refuse automatic upgrades from the discarded prototype migration chain."""

import asyncio
from collections.abc import Collection

from sqlalchemy import inspect, text

from app.db.session import engine

SAFE_REVISIONS = {
    "0001_initial_schema",
    "0002_academic_operations",
    "0003_school_services",
    "0004_subscription_entitlements",
    "0005_correct_rls_policies",
}
MANAGED_TABLES = {
    "attendance",
    "classrooms",
    "enrollments",
    "grades",
    "roles",
    "staff",
    "students",
    "teachers",
    "users",
}


def assess_schema(table_names: Collection[str], revision: str | None) -> str:
    tables = set(table_names)
    if not tables:
        return "EMPTY"
    if revision in SAFE_REVISIONS:
        return "CURRENT"
    if tables.isdisjoint(MANAGED_TABLES) and not revision:
        return "EMPTY"
    return "PROTOTYPE_OR_UNKNOWN"


async def preflight() -> None:
    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
        revision = None
        if "alembic_version" in table_names:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))

    decision = assess_schema(table_names, revision)
    await engine.dispose()
    if decision == "PROTOTYPE_OR_UNKNOWN":
        raise SystemExit(
            "Migration refused: this database contains the discarded prototype schema. "
            "Back it up, then recreate non-production databases. Production data requires "
            "a reviewed, data-preserving migration; see docs/migration-strategy.md."
        )
    print(f"Migration preflight passed: {decision.lower()} database")


if __name__ == "__main__":
    asyncio.run(preflight())
