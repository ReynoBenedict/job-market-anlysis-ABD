# TalentScope web

Next.js 16 app (App Router, React 19, TypeScript, Tailwind CSS v4). See the repository
README for setup and `docs/adr/0002-frontend-stack.md` for design decisions.

| Script | Purpose |
|---|---|
| `npm run dev` | Dev server on http://localhost:3001 (needs `API_BASE_URL` in `.env.local`) |
| `npm run build` / `npm start` | Production build / server (the build does not need the API) |
| `npm run lint` · `npm run typecheck` | ESLint · TypeScript |
| `npm test` | Vitest unit/component tests |
| `npm run test:e2e` | Playwright journeys against a running stack |
| `npm run gen:api` | Regenerate `src/lib/api-schema.ts` from the API's OpenAPI schema |

Structure: `src/app/(site)` home page; `src/app/(app)` app shell pages; `src/app/admin`
admin workspace (protected by `src/proxy.ts`); `src/components` UI, charts, explorer;
`src/lib` API client (server-only), formatting, URL filter state, saved jobs.
