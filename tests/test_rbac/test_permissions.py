"""Tests for RBAC service."""

from unittest.mock import MagicMock

import pytest

from app.db.models.user import User
from app.services.rbac import get_user_permissions, has_any_permission, has_permission


@pytest.fixture
def admin_user():
    user = MagicMock(spec=User)
    user.is_superuser = True
    user.roles = []
    return user


@pytest.fixture
def regular_user():
    user = MagicMock(spec=User)
    user.is_superuser = False
    role = MagicMock()
    role.permissions = [MagicMock(codename="document:read")]
    user.roles = [role]
    return user


@pytest.mark.asyncio
async def test_admin_has_all_permissions(admin_user):
    assert await has_permission(admin_user, "anything")


@pytest.mark.asyncio
async def test_user_has_specific_permission(regular_user):
    assert await has_permission(regular_user, "document:read")


@pytest.mark.asyncio
async def test_user_lacks_permission(regular_user):
    assert not await has_permission(regular_user, "document:delete")


@pytest.mark.asyncio
async def test_has_any_permission(regular_user):
    assert await has_any_permission(regular_user, ["document:read", "document:delete"])
    assert not await has_any_permission(regular_user, ["document:delete", "document:create"])


@pytest.mark.asyncio
async def test_get_user_permissions(regular_user):
    perms = await get_user_permissions(regular_user)
    assert "document:read" in perms
    assert len(perms) == 1
