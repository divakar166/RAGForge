# RAGForge Frontend

This directory will contain the frontend application for RAGForge — a document management and RAG query interface.

## Quick Start

```bash
# Create Next.js app
npx create-next-app@latest . --typescript --tailwind --app

# Or with pnpm
pnpm create next-app . --typescript --tailwind --app
```

## Recommended Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js 14+ (App Router) | SSR, API routes if needed, great DX |
| Styling | Tailwind CSS v4 | Utility-first, ships with Next.js |
| UI Components | shadcn/ui | Accessible, themeable, copy-paste |
| State / Server | React Query (TanStack Query) | Caching, stale-while-revalidate |
| HTTP Client | fetch (built-in) or ky | Lightweight, no extra deps |
| Auth | JWT stored in httpOnly cookie | Secure against XSS |
| Forms | React Hook Form + Zod | Validation, type-safe |
| File Upload | react-dropzone | Drag-and-drop UX |

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login, returns JWT tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Get current user profile |

### Users (admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List all users |
| GET | `/users/{id}` | Get user details |
| PATCH | `/users/{id}` | Update user |
| POST | `/users/{id}/roles` | Assign roles to user |

### Roles & Permissions (admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/roles` | List all roles |
| POST | `/roles` | Create a new role |
| DELETE | `/roles/{id}` | Delete a role |
| GET | `/roles/permissions` | List all available permissions |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/upload` | Upload a document (multipart) |
| GET | `/documents` | List user's documents |
| GET | `/documents/{id}` | Get document details |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/documents/{id}/access` | Set document access rules |

### Search & Ask

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search/query` | Hybrid search (returns chunks) |
| POST | `/search/ask` | RAG query (returns answer + citations) |
| GET | `/search/history` | User's search history |
| POST | `/search/feedback` | Submit thumbs up/down for a trace |

Request body for `/search/query`:
```json
{
  "query": "What is RAGForge?",
  "top_k": 5
}
```

Request body for `/search/ask`:
```json
{
  "query": "How does RBAC work?",
  "top_k": 5,
  "stream": false
}
```

### Evaluation (admin)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/evaluate/run` | Run RAGAS evaluation on golden dataset |
| GET | `/evaluate/dataset` | Get golden dataset info |

### General

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

## Authentication

All endpoints except `/auth/register`, `/auth/login`, `/health` require a valid JWT.

Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Pages to Build

### Public / Auth
- `/login` — Login form
- `/register` — Registration form

### Dashboard (authenticated)
- `/dashboard` — Overview with stats (doc count, recent searches)
- `/documents` — Document list with upload button, search/filter
- `/documents/{id}` — Document detail view with access control panel
- `/search` — Full query interface with results + RAG answer panel
- `/history` — Search history with re-run capability

### Admin (role: admin)
- `/admin/users` — User management (list, edit roles)
- `/admin/roles` — Role & permission management
- `/admin/evaluate` — RAGAS evaluation dashboard with pass/fail metrics
- `/admin/settings` — System settings (if applicable)

## Next Steps

1. Scaffold Next.js app with TypeScript + Tailwind
2. Set up API client module (`lib/api.ts`) with JWT handling
3. Build auth pages (login/register)
4. Build document upload + list page
5. Build search/ask query interface
6. Build admin user/role management pages
7. Build evaluation dashboard
8. Containerize with Docker (optional)
