"""API endpoint tests — validates request/response contracts for multi-tenant org model."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_current_user
from app.core.security import hash_password
from app.db.models.organization import Organization, OrganizationMember
from app.db.models.user import User
from app.main import app

pytestmark = pytest.mark.asyncio


AUTH_HEADER = "Authorization"


async def _register_org(client: AsyncClient, suffix: str = "") -> dict:
    """Register a user + org and return tokens + org_id."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": f"owner{suffix}@test.com",
        "username": f"owner{suffix}",
        "password": "password123",
        "org_name": f"Test Org {suffix}" if suffix else "Test Org",
        "org_slug": f"test-org{suffix}" if suffix else "test-org",
    })
    assert resp.status_code == 201
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "org_id": data["org_id"],
        "org_name": data["org_name"],
        "refresh_token": data["refresh_token"],
    }


async def _auth(client: AsyncClient, token: str) -> None:
    client.headers[AUTH_HEADER] = f"Bearer {token}"


def _deauth(client: AsyncClient) -> None:
    client.headers.pop(AUTH_HEADER, None)


# ── Auth Tests ────────────────────────────────────────────────────────


class TestAuth:
    async def test_register(self, client: AsyncClient):
        result = await _register_org(client, "reg1")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["org_id"] is not None

    async def test_register_duplicate(self, client: AsyncClient):
        await _register_org(client, "dup")
        resp = await client.post("/api/v1/auth/register", json={
            "email": "ownerdup@test.com",
            "username": "ownerdup",
            "password": "password123",
            "org_name": "Test Org dup",
            "org_slug": "test-orgdup",
        })
        assert resp.status_code == 409

    async def test_login(self, client: AsyncClient):
        await _register_org(client, "login1")
        resp = await client.post("/api/v1/auth/login", json={
            "username": "ownerlogin1", "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_by_email(self, client: AsyncClient):
        await _register_org(client, "login2")
        resp = await client.post("/api/v1/auth/login", json={
            "username": "ownerlogin2@test.com", "password": "password123",
        })
        assert resp.status_code == 200

    async def test_login_wrong_password(self, client: AsyncClient):
        await _register_org(client, "login3")
        resp = await client.post("/api/v1/auth/login", json={
            "username": "ownerlogin3", "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_refresh(self, client: AsyncClient):
        result = await _register_org(client, "ref1")
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": result["refresh_token"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_refresh_invalid(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert resp.status_code == 401

    async def test_me(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.get("/api/v1/auth/me")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "organizations" in data

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_real_token(self, client: AsyncClient):
        result = await _register_org(client, "me1")
        await _auth(client, result["access_token"])
        resp = await client.get("/api/v1/auth/me")
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json()["email"] == "ownerme1@test.com"


# ── Users Endpoint Tests (Admin) ─────────────────────────────────────


class TestUsers:
    async def test_list_users(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_admin] = lambda: test_user
        resp = await client.get("/api/v1/users")
        app.dependency_overrides.pop(get_current_admin, None)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(u["email"] == "test@example.com" for u in data)

    async def test_get_user(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_admin] = lambda: test_user
        resp = await client.get(f"/api/v1/users/{test_user.id}")
        app.dependency_overrides.pop(get_current_admin, None)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    async def test_get_user_invalid_id(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_admin] = lambda: test_user
        resp = await client.get("/api/v1/users/not-a-uuid")
        app.dependency_overrides.pop(get_current_admin, None)
        assert resp.status_code == 400

    async def test_get_user_not_found(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_admin] = lambda: test_user
        resp = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        app.dependency_overrides.pop(get_current_admin, None)
        assert resp.status_code == 404

    async def test_update_user(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_admin] = lambda: test_user
        resp = await client.patch(
            f"/api/v1/users/{test_user.id}",
            json={"is_superuser": True},
        )
        app.dependency_overrides.pop(get_current_admin, None)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "User updated"

    async def test_non_admin_cannot_list_users(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.get("/api/v1/users")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403


# ── Org Document Endpoint Tests ──────────────────────────────────────


class TestOrgDocuments:
    async def _setup(self, client: AsyncClient, suffix: str) -> dict:
        result = await _register_org(client, suffix)
        await _auth(client, result["access_token"])
        return result

    async def test_upload_document(self, client: AsyncClient, db_session: AsyncSession):
        setup = await self._setup(client, "doc1")
        org_id = setup["org_id"]
        resp = await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("test.txt", b"Hello, world!", "text/plain")},
        )
        _deauth(client)
        assert resp.status_code == 202
        data = resp.json()
        assert data["title"] == "test.txt"
        assert data["file_type"] == "txt"
        assert data["status"] == "uploaded"
        assert data["organization_id"] == org_id

    async def test_upload_disallowed_extension(self, client: AsyncClient):
        setup = await self._setup(client, "doc2")
        org_id = setup["org_id"]
        resp = await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("test.exe", b"fake", "application/x-msdownload")},
        )
        _deauth(client)
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    async def test_list_documents(self, client: AsyncClient):
        setup = await self._setup(client, "doc3")
        org_id = setup["org_id"]
        await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("list_test.txt", b"data", "text/plain")},
        )
        resp = await client.get(f"/api/v1/orgs/{org_id}/documents")
        _deauth(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_get_document(self, client: AsyncClient):
        setup = await self._setup(client, "doc4")
        org_id = setup["org_id"]
        upload = await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("get_test.txt", b"data", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.get(f"/api/v1/orgs/{org_id}/documents/{doc_id}")
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    async def test_get_document_not_found(self, client: AsyncClient):
        setup = await self._setup(client, "doc5")
        org_id = setup["org_id"]
        resp = await client.get(
            f"/api/v1/orgs/{org_id}/documents/00000000-0000-0000-0000-000000000000"
        )
        _deauth(client)
        assert resp.status_code == 404

    async def test_delete_document(self, client: AsyncClient):
        setup = await self._setup(client, "doc6")
        org_id = setup["org_id"]
        upload = await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("delete_test.txt", b"delete me", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.delete(f"/api/v1/orgs/{org_id}/documents/{doc_id}")
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Document deleted"

    async def test_set_document_access(self, client: AsyncClient):
        setup = await self._setup(client, "doc7")
        org_id = setup["org_id"]
        upload = await client.post(
            f"/api/v1/orgs/{org_id}/documents/upload",
            files={"file": ("access_test.txt", b"data", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.post(
            f"/api/v1/orgs/{org_id}/documents/{doc_id}/access",
            json={"is_public_in_org": True},
        )
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Access rules updated"


# ── Org Search Endpoint Tests ────────────────────────────────────────


class TestOrgSearch:
    async def test_search_history_empty(self, client: AsyncClient):
        result = await _register_org(client, "srch1")
        await _auth(client, result["access_token"])
        resp = await client.get(f"/api/v1/orgs/{result['org_id']}/search/history")
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_feedback_no_trace(self, client: AsyncClient):
        result = await _register_org(client, "srch2")
        await _auth(client, result["access_token"])
        resp = await client.post(
            f"/api/v1/orgs/{result['org_id']}/search/feedback",
            json={"trace_id": "test-trace", "score": 1, "comment": "Good"},
        )
        _deauth(client)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Org Members Endpoint Tests ───────────────────────────────────────


class TestOrgMembers:
    async def test_list_members(self, client: AsyncClient):
        result = await _register_org(client, "mem1")
        await _auth(client, result["access_token"])
        resp = await client.get(f"/api/v1/orgs/{result['org_id']}/members")
        _deauth(client)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(m["role"] == "owner" for m in data)

    async def test_non_owner_cannot_remove(self, client: AsyncClient):
        from unittest.mock import MagicMock

        from app.core.deps import OrganizationContext, get_org_context

        async def mock_org_ctx():
            member = MagicMock(spec=OrganizationMember)
            member.organization_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            member.user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
            member.role = "viewer"
            member.is_active = True
            member.user = MagicMock(spec=User)
            member.user.is_superuser = False

            org = MagicMock(spec=Organization)
            org.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            org.is_active = True

            return OrganizationContext(
                organization=org,
                member=member,
                qdrant_store=None,
            )

        app.dependency_overrides[get_org_context] = mock_org_ctx
        resp = await client.delete(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000001/members/00000000-0000-0000-0000-000000000004"
        )
        app.dependency_overrides.pop(get_org_context, None)
        assert resp.status_code == 403


# ── Evaluation Endpoint Tests ────────────────────────────────────────


class TestEvaluate:
    async def test_evaluate_forbidden_for_non_superuser(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.post("/api/v1/evaluate/run")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_dataset_info(self, client: AsyncClient):
        superuser = User(
            id=uuid.UUID("10000000-0000-0000-0000-000000000000"),
            email="super@test.com",
            username="super",
            hashed_password=hash_password("pass"),
            is_superuser=True,
        )
        app.dependency_overrides[get_current_user] = lambda: superuser
        resp = await client.get("/api/v1/evaluate/dataset")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "size" in data


# ── Health Endpoint ──────────────────────────────────────────────────


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "RAGForge"
