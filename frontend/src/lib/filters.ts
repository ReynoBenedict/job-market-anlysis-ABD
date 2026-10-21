/**
 * Filter state lives in the URL so every view is shareable and back/forward works.
 * Parameter names match the API's query parameters one-to-one.
 */

export const MULTI_FILTERS = [
  "province",
  "city",
  "role_family",
  "employment_type",
  "work_arrangement",
  "education",
  "experience",
  "source",
  "freshness",
  "tag",
] as const;
export const SINGLE_FILTERS = ["q", "salary_disclosed", "salary_min", "salary_max"] as const;

/** Sort orders the API accepts; anything else in the URL falls back to the default. */
export const SORT_VALUES = ["relevance", "newest", "salary_desc", "title", "company"] as const;
/** Highest page number the API serves. */
export const MAX_PAGE = 10_000;

export type MultiFilter = (typeof MULTI_FILTERS)[number];
export type SearchParamsRecord = Record<string, string | string[] | undefined>;
export type FilterQuery = Partial<Record<MultiFilter, string[]>> &
  Partial<Record<(typeof SINGLE_FILTERS)[number] | "sort" | "page" | "by", string>>;

function asList(value: string | string[] | undefined): string[] {
  if (value === undefined) return [];
  return (Array.isArray(value) ? value : [value]).filter(Boolean);
}

function first(value: string | string[] | undefined): string | undefined {
  const [head] = asList(value);
  return head;
}

/** Keep only known filter parameters; unknown keys never reach the API. */
export function readFilters(params: SearchParamsRecord, extra: readonly string[] = []): FilterQuery {
  const query: FilterQuery = {};
  for (const key of MULTI_FILTERS) {
    const values = asList(params[key]);
    if (values.length) query[key] = values;
  }
  for (const key of [...SINGLE_FILTERS, ...extra] as const) {
    const value = first(params[key]);
    if (value) (query as Record<string, string>)[key] = value;
  }
  return query;
}

export function countActiveFilters(query: FilterQuery): number {
  const multi = MULTI_FILTERS.reduce((total, key) => total + (query[key]?.length ?? 0), 0);
  const single = SINGLE_FILTERS.filter((key) => query[key]).length;
  return multi + single;
}

/** Turn a filter query back into a query string (without leading "?"). */
export function serializeFilters(query: FilterQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else if (value) params.set(key, value);
  }
  return params.toString();
}

/** Toggle one value of a multi-select filter, resetting pagination. */
export function toggleValue(query: FilterQuery, key: MultiFilter, value: string): FilterQuery {
  const current = query[key] ?? [];
  const next = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
  return { ...withoutPage(query), [key]: next.length ? next : undefined };
}

export function withoutPage(query: FilterQuery): FilterQuery {
  const rest = { ...query };
  delete rest.page;
  return rest;
}

/**
 * Remove the keyword. "Most relevant" ordering needs a keyword, so it is dropped with it
 * (otherwise the sort control would show an option that is no longer offered).
 */
export function withoutKeyword(query: FilterQuery): FilterQuery {
  const next: FilterQuery = { ...withoutPage(query), q: undefined };
  if (next.sort === "relevance") next.sort = undefined;
  return next;
}

/**
 * Remove every filter but keep the keyword and view settings (sort order, comparison tab):
 * "clear all filters" should not silently change how results are ordered or compared.
 */
export function clearFilters(query: FilterQuery): FilterQuery {
  const next: FilterQuery = {};
  if (query.q) next.q = query.q;
  if (query.sort) next.sort = query.sort;
  if (query.by) next.by = query.by;
  return next;
}

/** Highest monthly salary bound the API accepts (Rp 10 miliar). */
export const MAX_SALARY_RUPIAH = 10_000_000_000;

/** Monthly salary bound typed by a user in millions of rupiah ("7,5") to rupiah. */
export function millionsToRupiah(input: string): string | undefined {
  const text = input.trim();
  // Plain decimal numbers only ("7", "7,5", "7.5"); no exponents, signs, or thousands separators.
  if (!/^\d+([.,]\d+)?$/.test(text)) return undefined;
  const rupiah = Math.round(Number(text.replace(",", ".")) * 1_000_000);
  if (!Number.isFinite(rupiah) || rupiah > MAX_SALARY_RUPIAH) return undefined;
  return String(rupiah);
}

export function rupiahToMillions(value: string | undefined): string {
  if (!value) return "";
  const millions = Number(value) / 1_000_000;
  return Number.isFinite(millions) ? String(millions).replace(".", ",") : "";
}
