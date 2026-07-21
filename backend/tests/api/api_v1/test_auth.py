from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt

from app.api.v1.dependencies import decode_token, require_permissions
from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token, create_refresh_token
from app.schemas.auth import CurrentUser


def test_access_token_contains_only_session_identity_claims() -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    session_id = uuid4()
    token = create_access_token(
        subject=user_id,
        tenant_id=tenant_id,
        permission_version=4,
        session_id=session_id,
    )
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["session_id"] == str(session_id)
    assert payload["permission_version"] == 4
    assert payload["type"] == "access"
    assert "permissions" not in payload
    assert "role" not in payload


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    token = create_refresh_token(
        subject=uuid4(), tenant_id=uuid4(), permission_version=1, session_id=uuid4()
    )
    with pytest.raises(HTTPException) as caught:
        decode_token(token)
    assert caught.value.status_code == 401


@pytest.mark.asyncio
async def test_permission_dependency_returns_403_for_direct_url_access() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        tenant_id=uuid4(),
        email="teacher@example.com",
        permission_version=1,
        permissions={"scores.enter"},
    )
    dependency = require_permissions("scores.approve")
    with pytest.raises(HTTPException) as caught:
        await dependency(current_user)
    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_permission_dependency_allows_exact_atomic_permission() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        tenant_id=uuid4(),
        email="approver@example.com",
        permission_version=1,
        permissions={"scores.approve"},
    )
    dependency = require_permissions("scores.approve")
    assert await dependency(current_user) == current_user
