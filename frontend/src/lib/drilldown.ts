import type { BarListItem } from "@/components/charts/bar-list";

import type { Breakdown } from "./api";
import {
  type FilterQuery,
  type MultiFilter,
  readFilters,
  type SearchParamsRecord,
  serializeFilters,
  withoutPage,
} from "./filters";

/** Link from an aggregate to the job search, keeping the filters that produced it. */
export function jobsHref(query: FilterQuery, key?: MultiFilter, value?: string): string {
  const next = withoutPage(query);
  delete next.by; // the salary page's comparison tab means nothing to the job search
  if (key && value) next[key] = [value];
  const search = serializeFilters(next);
  return search ? `/lowongan?${search}` : "/lowongan";
}

/** Breakdown rows as bar-list items; rows with a null key (unknown) are not linkable. */
export function toBarItems(breakdown: Breakdown, query: FilterQuery, key?: MultiFilter): BarListItem[] {
  return breakdown.rows.map((row) => ({
    key: row.key ?? "__unknown__",
    label: row.label,
    count: row.count,
    share: row.share,
    href: key && row.key ? jobsHref(query, key, row.key) : undefined,
  }));
}

/**
 * The results page a job detail links back to. Its query string travels in `kembali`; it is
 * re-parsed and only known search parameters are kept, so the link always stays on
 * /lowongan (no open redirect) and carries filters, keyword, sort, and page.
 */
export function resultsHref(kembali: string | string[] | undefined): string {
  if (typeof kembali !== "string" || !kembali) return "/lowongan";
  const params = new URLSearchParams(kembali.replace(/^\?/, ""));
  const record: SearchParamsRecord = {};
  for (const key of new Set(params.keys())) record[key] = params.getAll(key);
  const search = serializeFilters(readFilters(record, ["sort", "page"]));
  return search ? `/lowongan?${search}` : "/lowongan";
}
