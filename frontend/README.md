# RAGForge Frontend

Next.js 16 dashboard for the RAGForge platform — document management, chat UI, search, and admin panels.

## Tech Stack
- Next.js 16 (App Router, Turbopack)
- TypeScript
- Tailwind CSS + shadcn/ui
- TanStack React Query (data fetching)
- Lucide React (icons)
- Sonner (toasts)

## Pages

| Route | Description |
|-------|-------------|
| `/login` | Login |
| `/register` | Registration + org creation |
| `/dashboard` | Home |
| `/dashboard/documents` | Document list |
| `/dashboard/documents/[id]` | Document detail + download + collection selector |
| `/dashboard/collections` | Collection list |
| `/dashboard/collections/[id]` | Collection detail with documents |
| `/dashboard/search` | Search interface |
| `/dashboard/chat` | Chat UI with thread sidebar |
| `/dashboard/history` | Conversation history |
| `/dashboard/admin/users` | User management |
| `/dashboard/admin/roles` | Role management |
| `/dashboard/admin/members` | Org member management |
| `/dashboard/admin/invites` | Invitation management |
| `/dashboard/admin/audit` | Audit log viewer |
| `/dashboard/admin/evaluate` | RAGAS evaluation runner |
| `/invite` | Invite acceptance |

## Development

```bash
npm install
npm run dev     # :3000
npm run build   # production build
```

## API Client

All endpoints in `lib/api.ts` — auto-includes auth headers, org context.
Types in `lib/types.ts`.
