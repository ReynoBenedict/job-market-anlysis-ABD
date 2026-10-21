import "server-only";

import { connection } from "next/server";

import type { components } from "./api-schema";

export type Schemas = components["schemas"];
export type JobSummary = Schemas["JobSummary"];
export type JobDetail = Schemas["JobDetail"];
export type JobPage = Schemas["Page_JobSummary_"];
export type FilterOptions = Schemas["FilterOptions"];
export type MarketOverview = Schemas["MarketOverview"];
export type Breakdown = Schemas["BreakdownOut"];
export type SalaryOverview = Schemas["SalaryOverviewOut"];
export type SalaryComparison = Schemas["SalaryComparisonOut"];
export type TagStats = Schemas["TagStatsOut"];
export type SourceCoverage = Schemas["SourceCoverage"];
export type DatasetScope = Schemas["DatasetScope"];

export type QueryValue = string | number | boolean | null | undefined | readonly string[];
export type Query = Record<string, QueryValue>;

/** An API error carrying the backend's error envelope code. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function baseUrl(): string {
  const url = process.env.API_BASE_URL;
  if (!url) throw new Error("API_BASE_URL is not set; see .env.example");
  return url.replace(/\/$/, "");
}

export function toSearchParams(query: Query): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else params.append(key, String(value));
  }
  return params;
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
}

/**
 * Server-side call to the TalentScope API. Never imported by client components, so
 * the API location and admin token stay on the server.
 */
export async function apiRequest<T>(path: string, query: Query = {}, options: RequestOptions = {}): Promise<T> {
  // API data reflects the live database, so it is always read per request and never
  // baked into the prerendered shell at build time (when the API may not even run).
  await connection();
  const params = toSearchParams(query).toString();
  const url = `${baseUrl()}/api/v1${path}${params ? `?${params}` : ""}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(10_000),
    });
  } catch (cause) {
    throw new ApiError(503, "api_unreachable", `TalentScope API tidak dapat dihubungi (${String(cause)})`);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { code?: string; message?: string } } | null;
    throw new ApiError(
      response.status,
      body?.error?.code ?? "http_error",
      body?.error?.message ?? `Permintaan API gagal (HTTP ${response.status})`,
    );
  }
  return (await response.json()) as T;
}

/**
 * User-facing message for an expected API failure. Anything that is not an ApiError
 * is a programming error and is re-thrown to the route's error boundary.
 */
export function apiErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) throw error;
  if (error.status === 422) return "Parameter pencarian tidak valid. Periksa filter atau atur ulang pencarian.";
  if (error.status === 404) return "Data yang diminta tidak ditemukan.";
  if (error.code === "api_unreachable" || error.status >= 500) {
    return "Layanan data TalentScope sedang tidak tersedia. Silakan coba beberapa saat lagi.";
  }
  return error.message;
}

/**
 * Where "Coba lagi" should lead. Invalid parameters fail again on retry, so they lead to the
 * page without parameters; anything else (API down, timeout) retries the same view.
 */
export function retryHref(error: unknown, path: string, search = ""): string {
  if (error instanceof ApiError && error.status === 422) return path;
  return search ? `${path}?${search}` : path;
}

export const api = {
  jobs: (query: Query) => apiRequest<JobPage>("/jobs", query),
  job: (id: string) => apiRequest<JobDetail>(`/jobs/${encodeURIComponent(id)}`),
  filters: () => apiRequest<FilterOptions>("/filters"),
  overview: (query: Query = {}) => apiRequest<MarketOverview>("/market/overview", query),
  breakdown: (dimension: string, query: Query = {}) =>
    apiRequest<Breakdown>(`/market/breakdown/${dimension}`, query),
  salaryOverview: (query: Query = {}) => apiRequest<SalaryOverview>("/salaries/overview", query),
  salaryCompare: (query: Query) => apiRequest<SalaryComparison>("/salaries/compare", query),
  sourceTags: (query: Query = {}) => apiRequest<TagStats>("/skills/source-tags", query),
  sources: () => apiRequest<SourceCoverage[]>("/sources/coverage"),
};
