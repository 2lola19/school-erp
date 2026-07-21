import json
from uuid import uuid4

import pytest

from app.models.core import User
from app.services.access_control import (
    bump_permission_version,
    get_effective_permissions,
    permission_cache_key,
    scope_contains,
)


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeResult:
    def __init__(self, scalar_values=None, rows=None):
        self.scalar_values = scalar_values or []
        self.rows = rows or []

    def scalars(self):
        return FakeScalars(self.scalar_values)

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, results):
        self.results = iter(results)

    async def execute(self, _query):
        return next(self.results)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.deleted = []

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, _ttl, value):
        self.values[key] = value

    async def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


def test_scope_matching_is_strict_and_supports_lists() -> None:
    assert scope_contains({}, {"classroom_id": "class-a"})
    assert scope_contains(
        {"classroom_id": ["class-a", "class-b"], "subject_id": "math"},
        {"classroom_id": "class-b", "subject_id": "math"},
    )
    assert not scope_contains(
        {"classroom_id": "class-a", "subject_id": "math"},
        {"classroom_id": "class-b", "subject_id": "math"},
    )
    assert not scope_contains({"classroom_id": "class-a"}, {"subject_id": "math"})


@pytest.mark.asyncio
async def test_explicit_deny_overrides_role_allowance() -> None:
    user = User(
        id=uuid4(),
        tenant_id=uuid4(),
        email="teacher@example.com",
        password_hash="not-used",
        permission_version=2,
    )
    session = FakeSession(
        [
            FakeResult(scalar_values=["scores.enter", "scores.approve"]),
            FakeResult(scalar_values=[]),
            FakeResult(rows=[("scores.approve", "DENY"), ("students.read", "ALLOW")]),
        ]
    )
    cache = FakeRedis()
    permissions = await get_effective_permissions(session, cache, user)
    assert permissions == {"scores.enter", "students.read"}
    cached = json.loads(cache.values[permission_cache_key(user.tenant_id, user.id, 2)])
    assert cached == ["scores.enter", "students.read"]


@pytest.mark.asyncio
async def test_permission_version_change_invalidates_old_cache() -> None:
    user = User(
        id=uuid4(),
        tenant_id=uuid4(),
        email="teacher@example.com",
        password_hash="not-used",
        permission_version=7,
    )
    cache = FakeRedis()
    old_key = permission_cache_key(user.tenant_id, user.id, 7)
    cache.values[old_key] = "[]"
    await bump_permission_version(FakeSession([]), cache, user=user)
    assert user.permission_version == 8
    assert cache.deleted == [old_key]
