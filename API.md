# RAGForge API Reference

Base URL: `http://localhost:8000`
API Prefix: `/api/v1`

- [Auth](#auth)
- [Invites](#invites)
- [Users & Roles](#users--roles)
- [Org-scoped Endpoints](#org-scoped-endpoints)
  - [Documents](#documents)
  - [Collections](#collections)
  - [Search & RAG](#search--rag)
  - [Conversations](#conversations)
  - [Members](#members)
  - [Invitations](#invitations)
  - [Audit Log](#audit-log)
  - [Evaluation](#evaluation)
- [Health](#health)

---

## Auth

### `POST /api/v1/auth/register`

Create a new user account and organization. User becomes the org owner.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securePassword123",
  "org_name": "My Org",
  "org_slug": "my-org"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "org_id": "uuid",
  "org_name": "My Org",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `409` — email/username/org slug already taken

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

`username` accepts username or email.

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `401` — invalid credentials

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

---

### `GET /api/v1/auth/me`

Get the currently authenticated user's profile with org memberships.

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "is_active": true,
  "is_superuser": false,
  "organizations": [
    {"id": "uuid", "name": "My Org", "slug": "my-org", "role": "owner"}
  ],
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

---

## Invites

### `GET /api/v1/invites/verify`

Verify an invitation token (no auth required).

**Query Params:** `token` (string)

**Response (200):**
```json
{
  "valid": true,
  "email": "invited@example.com",
  "role": "member",
  "org_name": "My Org"
}
```

---

### `POST /api/v1/invites/accept`

Accept an invitation. User must be authenticated (logged in).

**Request Body:**
```json
{
  "token": "invite-token-string"
}
```

**Response (200):**
```json
{
  "detail": "Invitation accepted"
}
```

---

## Users & Roles

*All endpoints require `token` (owner/admin).*

### `GET /api/v1/users`

List all users.

**Response (200):** Array of user objects.

---

### `GET /api/v1/users/{user_id}`

Get a single user by UUID.

---

### `PATCH /api/v1/users/{user_id}`

Update user's active/superuser flags.

---

### `GET /api/v1/roles`

List all roles.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "admin",
    "description": "Full access",
    "is_system_role": true,
    "permissions": ["document:create", "document:read", "..."],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `POST /api/v1/roles`

Create a new role.

---

### `GET /api/v1/roles/permissions`

List all available permission codenames.

---

### `DELETE /api/v1/roles/{role_id}`

Delete a role (cannot delete system roles).

---

## Org-scoped Endpoints

All org-scoped endpoints are prefixed with `/api/v1/orgs/{org_id}/`. All require `Authorization: Bearer <access_token>` header.

---

### Documents

#### `GET /orgs/{org_id}/documents`

List documents with pagination. Respects RBAC (`allowed_roles`).

**Query Params:** `page` (1), `per_page` (20)

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "doc.pdf",
      "filename": "doc.pdf",
      "file_type": "pdf",
      "file_size": 12345,
      "status": "indexed",
      "allowed_roles": ["member"],
      "uploaded_by_id": "uuid",
      "organization_id": "uuid",
      "collection_id": null,
      "chunk_count": 12,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

#### `POST /orgs/{org_id}/documents/upload`

Upload a document. Triggers Celery `process_document` task.

**Request:** `multipart/form-data` with `file` field.
Allowed: `pdf`, `docx`, `txt`, `md`, `html`.

**Response (202):** Document object with `status: "uploaded"`.

---

#### `GET /orgs/{org_id}/documents/{document_id}`

Get a single document's metadata.

---

#### `PATCH /orgs/{org_id}/documents/{document_id}`

Update document fields (e.g., `collection_id`, `title`).

**Request Body:**
```json
{
  "collection_id": "uuid-or-null",
  "title": "new-title.pdf"
}
```

---

#### `DELETE /orgs/{org_id}/documents/{document_id}`

Delete a document and its file.

---

#### `POST /orgs/{org_id}/documents/{document_id}/access`

Update document access control.

**Auth:** `owner` or `admin`.

**Request Body:**
```json
{
  "allowed_roles": ["admin", "editor"]
}
```

---

#### `GET /orgs/{org_id}/documents/{document_id}/download`

Download the original file with proper Content-Type.

**Response:** Binary file stream.

---

### Collections

#### `GET /orgs/{org_id}/collections`

List all collections with document counts.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "organization_id": "uuid",
    "name": "Resumes",
    "description": "Candidate resumes",
    "is_public": false,
    "document_count": 3,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

#### `POST /orgs/{org_id}/collections`

Create a collection.

---

#### `GET /orgs/{org_id}/collections/{collection_id}`

Get collection detail with its documents.

---

#### `PATCH /orgs/{org_id}/collections/{collection_id}`

Update collection.

---

#### `DELETE /orgs/{org_id}/collections/{collection_id}`

Delete a collection (documents remain, `collection_id` set to null).

---

### Search & RAG

#### `POST /orgs/{org_id}/search/query`

Hybrid dense+sparse vector search with RBAC filter.

**Request Body:**
```json
{
  "query": "What is RAG?",
  "top_k": 5
}
```

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
      "chunk_index": 0,
      "section_path": null
    }
  ],
  "total": 3
}
```

---

#### `POST /orgs/{org_id}/search/ask`

Full RAG pipeline: hybrid search + LLM answer generation with citations.

**Request Body:**
```json
{
  "query": "What is RAG?",
  "top_k": 5,
  "conversation_id": null
}
```

When `conversation_id` is provided, prior Q&A from that conversation is included as context for follow-ups.

**Response (200):**
```json
{
  "query": "...",
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "citations": [/* SearchResultItem */],
  "trace_id": "langfuse-trace-id"
}
```

---

#### `GET /orgs/{org_id}/search/history`

Get search/ask history for the user, scoped to org.

---

#### `POST /orgs/{org_id}/search/feedback`

Submit feedback on a RAG response.

**Request Body:**
```json
{
  "trace_id": "langfuse-trace-id",
  "score": 1,
  "comment": "Great answer!"
}
```

---

### Conversations

#### `GET /orgs/{org_id}/conversations`

List conversation threads for the current user.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "title": "New Chat",
    "message_count": 5,
    "created_at": "..."
  }
]
```

---

#### `POST /orgs/{org_id}/conversations`

Create a new empty conversation thread.

**Response (200):** `{"id": "uuid", "title": "New Chat"}`

---

#### `GET /orgs/{org_id}/conversations/{thread_id}`

Get a conversation thread with all its messages.

---

#### `DELETE /orgs/{org_id}/conversations/{thread_id}`

Delete a conversation thread and all its messages.

---

### Members

#### `GET /orgs/{org_id}/members`

List all org members.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "role": "owner",
    "is_active": true,
    "created_at": "..."
  }
]
```

---

#### `PATCH /orgs/{org_id}/members/{member_id}`

Update member role or active status. Only `owner` and `admin` can manage members.

**Request Body:**
```json
{
  "role": "admin",
  "is_active": true
}
```

---

#### `DELETE /orgs/{org_id}/members/{member_id}`

Remove a member from the org.

---

### Invitations

#### `GET /orgs/{org_id}/invites`

List pending invitations for the org.

---

#### `POST /orgs/{org_id}/invites`

Create a new invitation.

**Request Body:**
```json
{
  "email": "invited@example.com",
  "role": "member"
}
```

---

#### `DELETE /orgs/{org_id}/invites/{invite_id}`

Cancel a pending invitation.

---

### Audit Log

#### `GET /orgs/{org_id}/audit`

Get paginated audit log entries for the org.

**Query Params:** `page` (1), `per_page` (20), `action` (optional filter)

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "action": "document:upload",
      "resource_type": "document",
      "resource_id": "uuid",
      "details": {},
      "actor_email": "user@example.com",
      "created_at": "..."
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

---

### Evaluation

#### `POST /orgs/{org_id}/evaluate/run`

Run RAGAS evaluation against the golden dataset.

**Response (200):**
```json
[
  {"metric": "faithfulness", "score": 0.85, "threshold": 0.80, "passed": true},
  {"metric": "answer_relevancy", "score": 0.82, "threshold": 0.75, "passed": true},
  {"metric": "context_precision", "score": 0.78, "threshold": 0.70, "passed": true},
  {"metric": "context_recall", "score": 0.75, "threshold": 0.70, "passed": true}
]
```

---

## Health

### `GET /health`

No auth required.

```json
{
  "status": "ok",
  "app": "RAGForge"
}
```

---

## Authentication Flow

1. **Register** — creates user + org, returns tokens
2. **Login** — get `access_token` + `refresh_token`
3. Include `Authorization: Bearer <access_token>` in all requests
4. When expired, use **Refresh** to get a new token pair
5. **Accept invite** — join an existing org via invitation token

### JWT Token Payload

| Claim | Value |
|-------|-------|
| `sub` | User UUID |
| `exp` | Expiration |
| `type` | `"access"` or `"refresh"` |

- Access: 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh: 7 days (`REFRESH_TOKEN_EXPIRE_DAYS`)

---

## RBAC Model

| Role | Scope |
|------|-------|
| `owner` | Full org access, can delete org |
| `admin` | Manage members, documents, settings |
| `member` | Upload/read documents, search |

Document-level access is controlled via `allowed_roles` (Qdrant payload pre-filter):

- Documents default to `["member"]` — all members can view
- Owners/admins can restrict to `["admin"]` or specific roles

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | — | Service role key |
| `SUPABASE_MODE` | `false` | Enable Supabase REST client |
| `SECRET_KEY` | `change-me` | JWT signing key |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant gRPC endpoint |
| `QDRANT_API_KEY` | — | Qdrant Cloud API key |
| `QDRANT_COLLECTION` | `documents` | Collection name |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible LLM |
| `LLM_API_KEY` | — | LLM API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `ALLOWED_EXTENSIONS` | `pdf,docx,txt,md,html` | Comma-separated string |
| `UPLOAD_DIR` | `./uploads` | File storage |
| `LANGFUSE_ENABLED` | `false` | Opt-in tracing |
