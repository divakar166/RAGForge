# RAGForge API Reference

Base URL: `http://localhost:8000`
API Prefix: `/api/v1`

- [Auth](#auth)
- [Users](#users)
- [Roles & Permissions](#roles--permissions)
- [Documents](#documents)
- [Search & RAG](#search--rag)
- [Evaluation](#evaluation)
- [Health](#health)

---

## Auth

### `POST /api/v1/auth/register`

Create a new user account. Auto-assigns the `viewer` role. Returns tokens on success.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securePassword123"
}
```

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `email` | string | valid email | |
| `username` (aliased as `full_name`) | string | 3–64 chars | sent as `username` in JSON body |
| `password` | string | 8–128 chars | |

**Response (201):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `409 Conflict` — email/username already taken

---

### `POST /api/v1/auth/login`

Authenticate and receive JWT tokens.

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securePassword123"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `username` | string | username OR email — supply either |
| `email` | string | alternate field, not required if `username` provided |
| `password` | string | |

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `401 Unauthorized` — invalid credentials

---

### `POST /api/v1/auth/refresh`

Exchange a refresh token for a new token pair.

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `401 Unauthorized` — invalid/expired refresh token

---

### `GET /api/v1/auth/me`

Get the currently authenticated user's profile with roles and permissions.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "johndoe",
  "is_active": true,
  "is_superuser": false,
  "roles": [
    {
      "id": "uuid-string",
      "name": "viewer",
      "permissions": ["document:read", "search:query"]
    }
  ],
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

---

## Users

*All endpoints require `admin:full` / `users:manage` (superuser).*

### `GET /api/v1/users`

List all users.

**Response (200):**
```json
[
  {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "johndoe",
    "is_active": true,
    "is_superuser": false,
    "roles": [{"id": "...", "name": "viewer", "permissions": ["..."]}],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `GET /api/v1/users/{user_id}`

Get a single user by UUID.

**Path Params:** `user_id` (UUID string)

**Errors:** `400` — invalid UUID, `404` — not found

---

### `PATCH /api/v1/users/{user_id}`

Update user's active/superuser flags.

**Request Body:**
```json
{
  "is_active": true,
  "is_superuser": false
}
```

Both fields optional.

**Response (200):** `{"detail": "User updated"}`

---

### `POST /api/v1/users/{user_id}/roles`

Replace all role assignments for a user.

**Request Body:**
```json
{
  "role_ids": ["uuid-of-role-1"]
}
```

**Response (200):** Full `UserResponse` object with updated roles.

**Errors:** `404` — user not found

---

## Roles & Permissions

*All endpoints require admin.*

### `GET /api/v1/roles`

List all roles with their permission codenames.

**Response (200):**
```json
[
  {
    "id": "uuid-string",
    "name": "admin",
    "description": "Full system access",
    "is_system_role": true,
    "permissions": ["document:create", "document:read", "..."],
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  }
]
```

---

### `POST /api/v1/roles`

Create a new role.

**Request Body:**
```json
{
  "name": "custom-role",
  "description": "My custom role",
  "permission_ids": ["uuid-of-permission-1"]
}
```

**Response (201):** Full `RoleResponse` object.

---

### `GET /api/v1/roles/permissions`

List all available permissions.

**Response (200):**
```json
[
  {
    "id": "uuid-string",
    "codename": "document:create",
    "name": "Create Documents",
    "description": null,
    "resource_type": "document",
    "action": "create"
  }
]
```

---

### `DELETE /api/v1/roles/{role_id}`

Delete a role (cannot delete system roles).

**Response (200):** `{"detail": "Role deleted"}`

**Errors:** `404` — not found or is system role

---

## Documents

### `POST /api/v1/documents/upload`

Upload a document (file). Triggers async `process_document` Celery task.

**Auth:** Requires `document:create` or `*:*` permission.

**Request:** `multipart/form-data`

| Field | Type | Notes |
|-------|------|-------|
| `file` | file | Allowed: `pdf`, `docx`, `txt`, `md`, `html` (configurable via `ALLOWED_EXTENSIONS`) |

**Response (202):**
```json
{
  "id": "uuid-string",
  "title": "filename.pdf",
  "filename": "filename.pdf",
  "file_type": "pdf",
  "file_size": 12345,
  "status": "uploaded",
  "is_public": false,
  "owner_id": "uuid",
  "allowed_role_ids": [],
  "allowed_user_ids": [],
  "chunk_count": 0,
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:** `400` — disallowed file type, `413` — file too large, `403` — permission denied

---

### `GET /api/v1/documents`

List documents with pagination.

**Auth:** Authenticated user.

**Query Params:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `page` | int | 1 | |
| `per_page` | int | 20 | |

**RBAC:** Superusers see all documents. Regular users see only their own + public docs.

**Response (200):**
```json
{
  "items": [/* DocumentResponse */],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

### `GET /api/v1/documents/{document_id}`

Get a single document.

**Auth:** Superusers can access any. Users can access their own or public documents.

**Errors:** `400` — invalid UUID, `404` — not found, `403` — access denied

---

### `DELETE /api/v1/documents/{document_id}`

Delete a document and its file.

**Auth:** Superusers can delete any. Users can only delete their own.

**Response (200):** `{"detail": "Document deleted"}`

**Errors:** `400`/`404`/`403`

---

### `POST /api/v1/documents/{document_id}/access`

Update access control rules for a document.

**Auth:** Superusers or document owner.

**Request Body:**
```json
{
  "is_public": true,
  "allowed_role_ids": [],
  "allowed_user_ids": []
}
```

**Response (200):** `{"detail": "Access rules updated"}`

---

## Search & RAG

### `POST /api/v1/search/query`

Perform a hybrid dense+sparse vector search.

**Auth:** Requires `search:query` or `*:*` permission.

**Request Body:**
```json
{
  "query": "What is RAG?",
  "top_k": 5
}
```

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `query` | string | — | 1–2000 chars |
| `top_k` | int | 5 | 1–50 |

**Response (200):**
```json
{
  "query": "What is RAG?",
  "results": [
    {
      "id": "uuid",
      "score": 0.95,
      "text": "Chunk content...",
      "content": "Chunk content...",
      "document_id": "uuid",
      "document_filename": "doc.pdf",
      "doc_title": "doc.pdf",
      "metadata": {},
      "chunk_index": 0,
      "section_path": null
    }
  ],
  "total": 3
}
```

---

### `POST /api/v1/search/ask`

Full RAG pipeline: search + LLM answer with citations.

**Auth:** Requires `search:query` or `*:*` permission.

**Request Body:**
```json
{
  "query": "What is RAG?",
  "top_k": 5,
  "stream": false
}
```

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `query` | string | — | 1–2000 chars |
| `top_k` | int | 5 | 1–20 |
| `stream` | bool | false | (placeholder) |

**Response (200):**
```json
{
  "query": "What is RAG?",
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "citations": [/* SearchResultItem entries */],
  "model": "gpt-4o-mini",
  "trace_id": "langfuse-trace-id"
}
```

If no relevant documents found:
```json
{
  "query": "...",
  "answer": "No relevant documents found.",
  "citations": [],
  "model": "none",
  "trace_id": null
}
```

---

### `GET /api/v1/search/history`

Get the last 50 search/ask queries for the authenticated user.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "type": "ask",
    "query": "What is RAG?",
    "created_at": "2025-01-01T00:00:00+00:00"
  }
]
```

`type` values: `"ask"` or `"search"`

---

### `POST /api/v1/search/feedback`

Submit user satisfaction feedback for a RAG response.

**Request Body:**
```json
{
  "trace_id": "langfuse-trace-id",
  "score": 1,
  "comment": "Great answer!"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `trace_id` | string | Langfuse trace ID |
| `score` | int or string | `0`/`1` or `"thumbs_up"`/`"thumbs_down"` |
| `comment` | string | Optional feedback text |

**Response (200):** `{"status": "ok"}`

---

## Evaluation

### `POST /api/v1/evaluate/run`

Run RAGAS evaluation on the golden dataset.

**Auth:** Requires `evaluate:run` or `*:*` permission.

**Response (200):**
```json
[
  {"metric": "faithfulness", "score": 0.85, "threshold": 0.80, "passed": true},
  {"metric": "answer_relevancy", "score": 0.82, "threshold": 0.75, "passed": true},
  {"metric": "context_precision", "score": 0.78, "threshold": 0.70, "passed": true},
  {"metric": "context_recall", "score": 0.75, "threshold": 0.70, "passed": true}
]
```

**Errors:** `404` — no golden dataset found

---

### `GET /api/v1/evaluate/dataset`

Get metadata about the golden evaluation dataset.

**Response (200):**
```json
{
  "name": "Golden Dataset",
  "size": 10
}
```

---

## Health

### `GET /health`

**No auth required.**

```json
{
  "status": "ok",
  "app": "RAGForge"
}
```

---

## Authentication Flow

1. **Register** or **Login** to get `access_token` + `refresh_token`
2. Include `Authorization: Bearer <access_token>` in all protected requests
3. When expired, use **Refresh** to get a new token pair

### JWT Token Payload

| Claim | Value |
|-------|-------|
| `sub` | User UUID (string) |
| `exp` | Expiration timestamp |
| `type` | `"access"` or `"refresh"` |

- Access token lifetime: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token lifetime: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

---

## RBAC / Permission Model

| Permission Codename | Roles | Endpoints |
|---------------------|-------|-----------|
| `document:create` | admin, editor | `POST /documents/upload` |
| `document:read` | admin, editor, viewer | Service-layer on document get |
| `document:update` | admin, editor | `POST /documents/{id}/access` |
| `document:delete` | admin, editor | `DELETE /documents/{id}` |
| `search:query` | admin, editor, viewer | `POST /search/query`, `POST /search/ask` |
| `users:manage` | admin | (admin-only dep) |
| `roles:manage` | admin | (admin-only dep) |
| `evaluate:run` | admin | `POST /evaluate/run` |
| `admin:full` | admin | (superuser check) |

Built-in roles:
- **admin**: all 9 permissions
- **editor**: create, read, update, delete documents + search
- **viewer**: read documents + search (auto-assigned on registration)

---

## Environment / Configuration

Key config values (see `app/core/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `ALLOWED_EXTENSIONS` | `pdf,docx,txt,md,html` | Comma-separated string |
| `MAX_FILE_SIZE` | 52428800 (50MB) | Max upload size |
| `TEI_ENDPOINT` | `http://localhost:8080` | TEI embedding service |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API |
| `QDRANT_HOST` | `localhost` | Vector DB host |
| `LANGFUSE_ENABLED` | `false` | Enable Langfuse tracing |
