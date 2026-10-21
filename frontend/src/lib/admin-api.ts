import "server-only";

import { headers } from "next/headers";
import { connection } from "next/server";

import { checkAdminAuthorization } from "./admin-auth";
import { apiRequest, type Query, type Schemas } from "./api";

export type AdminSource = Schemas["AdminSource"];
export type RunPage = Schemas["Page_RunOut_"];
export type Run = Schemas["RunOut"];
export type Quality = Schemas["QualityOut"];
export type AuditPage = Schemas["Page_AuditOut_"];

function token(): string {
  const value = process.env.ADMIN_API_TOKEN;
  if (!value) throw new Error("ADMIN_API_TOKEN is not configured");
  return value;
}

/** Re-checks Basic credentials so admin server actions are protected even if called directly. */
export async function assertAdminRequest(): Promise<void> {
  const result = checkAdminAuthorization((await headers()).get("authorization"));
  if (result !== "ok") throw new Error("Tidak berwenang");
}

/** Admin API call; the token is read only at request time, never during prerendering. */
async function adminRequest<T>(path: string, query: Query = {}, body?: unknown): Promise<T> {
  await connection();
  return apiRequest<T>(path, query, { method: body ? "POST" : "GET", body, token: token() });
}

export const adminApi = {
  sources: () => adminRequest<AdminSource[]>("/admin/sources"),
  runs: (query: Query) => adminRequest<RunPage>("/admin/ingestion-runs", query),
  quality: () => adminRequest<Quality>("/admin/data-quality"),
  audit: (query: Query) => adminRequest<AuditPage>("/admin/audit-events", query),
  setPaused: (sourceId: string, paused: boolean, reason: string) =>
    adminRequest<AdminSource>(
      `/admin/sources/${encodeURIComponent(sourceId)}/${paused ? "pause" : "resume"}`,
      {},
      { reason },
    ),
};
