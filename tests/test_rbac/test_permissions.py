"""Tests for org-based RBAC via require_org_role."""

import pytest
from fastapi import HTTPException

from app.core.deps import OrganizationContext, require_org_role
from app.core.security import InvalidTokenError, create_access_token, decode_token


class TestOrgRole:
    """Tests for the require_org_role dependency factory."""

    def test_require_org_role_returns_factory(self):
        dep = require_org_role("owner", "admin")
        assert callable(dep)

    @pytest.mark.asyncio
    async def test_require_org_role_checks_role(self):
        dep = require_org_role("admin")
        member = {"role": "viewer", "user_id": "u1"}
        user = {"is_superuser": False, "id": "u1"}
        ctx = OrganizationContext(organization={}, member=member, qdrant_store=None)
        with pytest.raises(HTTPException) as exc:
            await dep(ctx, user)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_org_role_allows_valid_role(self):
        dep = require_org_role("owner", "admin")
        member = {"role": "admin", "user_id": "u1"}
        user = {"is_superuser": False, "id": "u1"}
        ctx = OrganizationContext(organization={}, member=member, qdrant_store=None)
        result = await dep(ctx, user)
        assert result is ctx


class TestToken:
    """JWT token integration with org claims."""

    def test_token_with_org_claims(self):
        token = create_access_token(
            subject="user-uuid",
            extra_claims={
                "org_id": "org-uuid",
                "org_role": "admin",
                "org_name": "Test Org",
            },
        )
        payload = decode_token(token)
        assert payload["org_id"] == "org-uuid"
        assert payload["org_role"] == "admin"
        assert payload["org_name"] == "Test Org"

    def test_token_without_org_claims(self):
        token = create_access_token(subject="user-uuid")
        payload = decode_token(token)
        assert "org_id" not in payload
        assert "org_role" not in payload

    def test_invalid_token_raises(self):
        with pytest.raises(InvalidTokenError):
            decode_token("invalid.token.here")
