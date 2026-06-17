# AI Trip Agent Frontend

This is the Next.js frontend for AI Trip Agent. It provides the landing page, conversational planning workspace, itinerary cards, map visualization, session management, and export actions.

## Stack

- Next.js 15 App Router
- React 19 and TypeScript
- Tailwind CSS
- Radix UI primitives
- Zustand local state and persisted session index
- AMap JS API for map rendering
- Playwright for E2E coverage

## Environment

Create `frontend/.env.local` from the root template:

```powershell
Copy-Item ..\.env.example .env.local
```

Frontend variables:

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Browser-visible backend URL, usually `http://localhost:8000`. |
| `API_INTERNAL_URL` | Server-side backend URL used by Next.js when needed. |
| `NEXT_PUBLIC_AMAP_KEY` | AMap JS API key. |
| `NEXT_PUBLIC_AMAP_SECRET` | AMap JS security code. |
| `NEXT_PUBLIC_USE_MOCK` | Set to `true` to use local mock SSE responses. |

## Commands

```powershell
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm dev
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
corepack pnpm test:e2e
```

The development server runs at [http://localhost:3000](http://localhost:3000), with the main workspace at `/chat`.
