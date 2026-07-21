from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.base_class import Base
from app.models.core import StaffRoleAssignment
from app.schemas.roles import RoleAssignmentCreate


def test_role_schema_requires_end_date_for_temporary_assignments() -> None:
    with pytest.raises(ValidationError):
        RoleAssignmentCreate(
            role_id=uuid4(),
            assignment_type="SECONDARY",
            is_temporary=True,
            reason="Temporary examination duty",
        )


def test_role_schema_rejects_inverted_dates() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        RoleAssignmentCreate(
            role_id=uuid4(),
            assignment_type="SECONDARY",
            starts_at=now,
            ends_at=now - timedelta(days=1),
            reason="Invalid dates",
        )


def test_database_metadata_contains_role_safety_indexes() -> None:
    table = Base.metadata.tables[StaffRoleAssignment.__tablename__]
    index_names = {index.name for index in table.indexes}
    assert "uq_staff_active_primary_role" in index_names
    assert "uq_staff_active_role_assignment" in index_names


def test_database_metadata_contains_all_identity_tables() -> None:
    assert {
        "users",
        "staff",
        "roles",
        "staff_role_assignments",
        "role_conflicts",
        "role_delegation_rules",
        "permission_bundles",
        "permission_bundle_permissions",
        "role_permission_bundles",
        "audit_logs",
    } <= set(Base.metadata.tables)
