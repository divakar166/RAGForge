"""Comprehensive API endpoint tests — validates request/response contracts."""

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_current_user
from app.core.security import hash_password
from app.db.models.permission import Permission, RolePermission
from app.db.models.role import Role
from app.db.models.user import User
from app.main import app
from app.services.rbac import assign_roles

# ── Helper: seed permissions and roles ───────────────────────────────


async def _seed_roles(db_session: AsyncSession) -> dict[str, Role]:
    perms_data = [
        {"codename": "document:create", "name": "Create Documents", "resource_type": "document", "action": "create"},
        {"codename": "document:read", "name": "Read Documents", "resource_type": "document", "action": "read"},
        {"codename": "document:update", "name": "Update Documents", "resource_type": "document", "action": "update"},
        {"codename": "document:delete", "name": "Delete Documents", "resource_type": "document", "action": "delete"},
        {"codename": "search:query", "name": "Search Documents", "resource_type": "search", "action": "query"},
        {"codename": "users:manage", "name": "Manage Users", "resource_type": "users", "action": "manage"},
        {"codename": "roles:manage", "name": "Manage Roles", "resource_type": "roles", "action": "manage"},
        {"codename": "admin:full", "name": "Full Admin Access", "resource_type": "admin", "action": "*"},
        {"codename": "evaluate:run", "name": "Run Evaluations", "resource_type": "evaluate", "action": "run"},
    ]
    perm_map = {}
    for pd in perms_data:
        p = Permission(**pd)
        db_session.add(p)
        await db_session.flush()
        perm_map[pd["codename"]] = p

    roles_config = [
        ("admin", "Full system access", list(perm_map.values())),
        ("editor", "Can upload and manage documents", [
            perm_map["document:create"], perm_map["document:read"],
            perm_map["document:update"], perm_map["document:delete"],
            perm_map["search:query"],
        ]),
        ("viewer", "Can search and read documents", [perm_map["document:read"], perm_map["search:query"]]),
    ]
    roles = {}
    for rname, rdesc, rperms in roles_config:
        role = Role(name=rname, description=rdesc, is_system_role=True)
        db_session.add(role)
        await db_session.flush()
        for perm in rperms:
            db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        roles[rname] = role
    await db_session.flush()
    return roles


@pytest_asyncio.fixture
async def seeded_roles(db_session: AsyncSession) -> dict[str, Role]:
    return await _seed_roles(db_session)


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("adminpass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, admin_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_admin, None)


async def _make_user_with_roles(
    db_session: AsyncSession,
    email: str,
    username: str,
    roles_list: list[Role],
) -> User:
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    user = await assign_roles(db_session, str(user.id), [str(r.id) for r in roles_list])
    return user


async def _make_viewer(db_session: AsyncSession, seeded_roles: dict) -> User:
    return await _make_user_with_roles(db_session, "viewer@test.com", "vieweruser", [seeded_roles["viewer"]])


async def _make_editor(db_session: AsyncSession, seeded_roles: dict) -> User:
    return await _make_user_with_roles(db_session, "editor@test.com", "editoruser", [seeded_roles["editor"]])


# ── Auth Tests ────────────────────────────────────────────────────────


class TestAuth:
    async def test_register(self, client: AsyncClient, seeded_roles: dict):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "newuser@test.com"

    async def test_register_duplicate(self, client: AsyncClient, seeded_roles: dict):
        await client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "username": "dupuser", "password": "password123",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "username": "dupuser2", "password": "password123",
        })
        assert resp.status_code == 409

    async def test_login(self, client: AsyncClient, seeded_roles: dict):
        await client.post("/api/v1/auth/register", json={
            "email": "loginuser@test.com", "username": "loginuser", "password": "password123",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "loginuser", "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_by_email(self, client: AsyncClient, seeded_roles: dict):
        await client.post("/api/v1/auth/register", json={
            "email": "emaillogin@test.com", "username": "emaillogin", "password": "password123",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "emaillogin@test.com", "password": "password123",
        })
        assert resp.status_code == 200

    async def test_login_wrong_password(self, client: AsyncClient, seeded_roles: dict):
        await client.post("/api/v1/auth/register", json={
            "email": "badpwd@test.com", "username": "badpwd", "password": "password123",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "badpwd", "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_refresh(self, client: AsyncClient, seeded_roles: dict):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "refreshuser@test.com", "username": "refreshuser", "password": "password123",
        })
        refresh_token = reg.json()["refresh_token"]
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert resp.status_code == 401

    async def test_me(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.get("/api/v1/auth/me")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "roles" in data

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_real_token(self, client: AsyncClient, seeded_roles: dict):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "realtoken@test.com", "username": "realtoken", "password": "password123",
        })
        access_token = reg.json()["access_token"]
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "realtoken@test.com"


# ── Users Endpoint Tests (Admin) ─────────────────────────────────────


class TestUsers:
    async def test_list_users(self, admin_client: AsyncClient, test_user: User):
        resp = await admin_client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(u["email"] == "test@example.com" for u in data)

    async def test_get_user(self, admin_client: AsyncClient, test_user: User):
        resp = await admin_client.get(f"/api/v1/users/{test_user.id}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    async def test_get_user_invalid_id(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/users/not-a-uuid")
        assert resp.status_code == 400

    async def test_get_user_not_found(self, admin_client: AsyncClient):
        resp = await admin_client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_update_user(self, admin_client: AsyncClient, test_user: User):
        resp = await admin_client.patch(
            f"/api/v1/users/{test_user.id}",
            json={"is_superuser": True},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "User updated"

    async def test_assign_roles(self, admin_client: AsyncClient, test_user: User, seeded_roles: dict):
        viewer_role = seeded_roles["viewer"]
        resp = await admin_client.post(
            f"/api/v1/users/{test_user.id}/roles",
            json={"role_ids": [str(viewer_role.id)]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["roles"]) == 1
        assert data["roles"][0]["name"] == "viewer"

    async def test_non_admin_cannot_list_users(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.get("/api/v1/users")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403


# ── Roles & Permissions Tests (Admin) ────────────────────────────────


class TestRoles:
    async def test_list_permissions(self, admin_client: AsyncClient, seeded_roles: dict):
        resp = await admin_client.get("/api/v1/roles/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        codenames = [p["codename"] for p in data]
        assert "document:create" in codenames
        assert "search:query" in codenames

    async def test_list_roles(self, admin_client: AsyncClient, seeded_roles: dict):
        resp = await admin_client.get("/api/v1/roles")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = [r["name"] for r in data]
        assert "admin" in names
        assert "viewer" in names

    async def test_create_role(self, admin_client: AsyncClient, seeded_roles: dict):
        perms = await admin_client.get("/api/v1/roles/permissions")
        read_perm_id = next(p["id"] for p in perms.json() if p["codename"] == "document:read")
        resp = await admin_client.post("/api/v1/roles", json={
            "name": "testrole", "description": "A test role", "permission_ids": [read_perm_id],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "testrole"
        assert data["permissions"] == ["document:read"]

    async def test_delete_role(self, admin_client: AsyncClient, seeded_roles: dict):
        perms = await admin_client.get("/api/v1/roles/permissions")
        read_perm_id = next(p["id"] for p in perms.json() if p["codename"] == "document:read")
        created = await admin_client.post("/api/v1/roles", json={
            "name": "deleteme", "description": "Will be deleted", "permission_ids": [read_perm_id],
        })
        role_id = created.json()["id"]
        resp = await admin_client.delete(f"/api/v1/roles/{role_id}")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Role deleted"

    async def test_delete_system_role_fails(self, admin_client: AsyncClient, seeded_roles: dict):
        viewer_role = seeded_roles["viewer"]
        resp = await admin_client.delete(f"/api/v1/roles/{viewer_role.id}")
        assert resp.status_code == 404


# ── Document Endpoint Tests ──────────────────────────────────────────


class TestDocuments:
    async def test_upload_document(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"Hello, world!", "text/plain")},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 202
        data = resp.json()
        assert data["filename"] == "test.txt"
        assert data["file_type"] == "txt"
        assert data["status"] == "uploaded"

    async def test_upload_document_forbidden(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        viewer = await _make_viewer(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: viewer
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"Hello!", "text/plain")},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_upload_disallowed_extension(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.exe", b"fake", "application/x-msdownload")},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    async def test_list_documents(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        await client.post(
            "/api/v1/documents/upload",
            files={"file": ("list_test.txt", b"data", "text/plain")},
        )
        resp = await client.get("/api/v1/documents")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_get_document(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("get_test.txt", b"data", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.get(f"/api/v1/documents/{doc_id}")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    async def test_get_document_not_found(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        resp = await client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 404

    async def test_delete_document(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("delete_test.txt", b"delete me", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.delete(f"/api/v1/documents/{doc_id}")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Document deleted"

    async def test_delete_other_users_document(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        other = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: other
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("other_test.txt", b"mine", "text/plain")},
        )
        doc_id = upload.json()["id"]

        editor = await _make_user_with_roles(db_session, "editor2@test.com", "editor2", [seeded_roles["editor"]])
        app.dependency_overrides[get_current_user] = lambda: editor
        resp = await client.delete(f"/api/v1/documents/{doc_id}")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_set_document_access(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        editor = await _make_editor(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: editor
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("access_test.txt", b"data", "text/plain")},
        )
        doc_id = upload.json()["id"]
        resp = await client.post(
            f"/api/v1/documents/{doc_id}/access",
            json={"is_public": True, "allowed_role_ids": [], "allowed_user_ids": []},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Access rules updated"


# ── Search Endpoint Tests ────────────────────────────────────────────


class TestSearch:
    async def test_search_query_no_external_deps(
        self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict,
    ):
        viewer = await _make_viewer(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: viewer
        resp = await client.post(
            "/api/v1/search/query",
            json={"query": "test query", "top_k": 5},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code != 403, "Should not get 403 — permission should pass"

    async def test_search_query_forbidden(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        user = await _make_user_with_roles(db_session, "noperm@test.com", "noperm", [])
        app.dependency_overrides[get_current_user] = lambda: user
        resp = await client.post(
            "/api/v1/search/query",
            json={"query": "test", "top_k": 5},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_search_history_empty(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.get("/api/v1/search/history")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_feedback(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
        resp = await client.post(
            "/api/v1/search/feedback",
            json={"trace_id": "test-trace", "score": 1, "comment": "Good"},
        )
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Evaluation Endpoint Tests ────────────────────────────────────────


class TestEvaluate:
    async def test_evaluate_run_no_permission(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        viewer = await _make_viewer(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: viewer
        resp = await client.post("/api/v1/evaluate/run")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_evaluate_run_with_dataset(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        admin_user = await _make_user_with_roles(db_session, "evaladmin@test.com", "evaladmin", [seeded_roles["admin"]])
        app.dependency_overrides[get_current_user] = lambda: admin_user
        resp = await client.post("/api/v1/evaluate/run")
        app.dependency_overrides.pop(get_current_user, None)
        # Dataset exists, returns results (possibly empty if RAGAS not fully available)
        assert resp.status_code == 200

    async def test_evaluate_forbidden(self, client: AsyncClient, db_session: AsyncSession, seeded_roles: dict):
        viewer = await _make_viewer(db_session, seeded_roles)
        app.dependency_overrides[get_current_user] = lambda: viewer
        resp = await client.post("/api/v1/evaluate/run")
        app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 403

    async def test_dataset_info(self, client: AsyncClient, test_user: User):
        app.dependency_overrides[get_current_user] = lambda: test_user
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
