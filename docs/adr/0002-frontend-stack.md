# ADR-0002: Frontend stack

**Status:** accepted (2026-10-17)

## Context
The Stitch references (docs/design/stitch) define a Tailwind-based, Indonesian-language
analytical UI. Pages must be shareable by URL, usable without heavy client JavaScript,
and must never show build-time or mock data as live data. Streamlit is excluded by the SRS.

## Options
- Next.js (App Router) vs. a client-only SPA (Vite + React).
- Charting: Apache ECharts vs. Recharts vs. hand-built HTML/SVG.

## Decision
- **Next.js 16, React 19, TypeScript, Tailwind CSS v4.** Server components fetch from the
  API on the server, so the API URL and admin token never reach the browser. Filter state
  lives in the URL. Cache Components is on; every API read calls `connection()` so data is
  fetched per request and never prerendered at build.
- **Charts are plain HTML/SVG.** The views need ranked bars, one histogram, and quartile
  ranges. Plain markup keeps values as text (accessible without colour), supports a table
  view, and avoids a ~1 MB charting dependency. Revisit when time-series or maps arrive.
- **lucide-react** for icons (tree-shaken SVGs) instead of the icon font in the Stitch HTML.
- API types are generated from the backend's OpenAPI schema (`npm run gen:api`).

## Consequences
- Stitch's design tokens were translated into a Tailwind `@theme`; muted text colour was
  darkened to meet WCAG AA.
- Generated Stitch HTML was used as a reference only, not copied.
