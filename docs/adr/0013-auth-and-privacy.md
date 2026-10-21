# ADR-0013: Authentication, authorization, and privacy

**Status:** accepted (2026-10-17)

- **No end-user accounts.** All public features are read-only. Saved jobs live in the
  browser's localStorage, so TalentScope stores no personal data (Indonesia's PDP Law
  No. 27/2022 is not triggered by the current features).
- **Admin API:** bearer token (`ADMIN_API_TOKEN`), compared in constant time; the admin
  API returns 503 when no token is configured.
- **Admin web pages:** HTTP Basic credentials checked in `proxy.ts` and again inside every
  admin server action; the API token stays on the server. Admin pages return 404 when
  credentials are not configured.
- **Least privilege by design:** the admin UI can only pause/resume eligible sources.
  Changing eligibility requires the CLI with a reason and an evidence URL, and is audited.
  Triggering ingestion over HTTP is intentionally not offered.

Revisit with a real identity provider (OIDC) if more than one operator or user accounts
are introduced.
