from scripts.migration_preflight import assess_schema


def test_empty_database_is_safe() -> None:
    assert assess_schema([], None) == "EMPTY"


def test_unrelated_database_is_not_mistaken_for_prototype() -> None:
    assert assess_schema(["external_metadata"], None) == "EMPTY"


def test_current_baseline_is_safe() -> None:
    assert assess_schema(["users", "alembic_version"], "0001_initial_schema") == "CURRENT"


def test_academic_operations_revision_is_safe() -> None:
    assert (
        assess_schema(["users", "academic_sessions"], "0002_academic_operations")
        == "CURRENT"
    )


def test_unversioned_managed_tables_are_refused() -> None:
    assert assess_schema(["users", "students"], None) == "PROTOTYPE_OR_UNKNOWN"


def test_old_revision_is_refused() -> None:
    assert (
        assess_schema(["users", "alembic_version"], "450c5a397866")
        == "PROTOTYPE_OR_UNKNOWN"
    )
