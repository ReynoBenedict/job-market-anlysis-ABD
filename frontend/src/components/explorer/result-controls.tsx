"use client";

import { X } from "lucide-react";

import { formatRupiahShort } from "@/lib/format";
import { type FilterQuery, MULTI_FILTERS, type MultiFilter, toggleValue, withoutKeyword, withoutPage } from "@/lib/filters";

import { useFilterNavigation } from "./filter-navigation";

export const SORT_OPTIONS = [
  { value: "newest", label: "Tanggal tayang terbaru" },
  { value: "relevance", label: "Paling relevan (perlu kata kunci)" },
  { value: "salary_desc", label: "Gaji tertinggi" },
  { value: "title", label: "Judul (A–Z)" },
  { value: "company", label: "Perusahaan (A–Z)" },
] as const;

export function SortSelect() {
  const { query, navigate, isPending } = useFilterNavigation();
  // "relevance" without a keyword (e.g. an edited URL) is not offered, so show the API's fallback.
  const current = query.sort && (query.sort !== "relevance" || query.q) ? query.sort : query.q ? "relevance" : "newest";
  return (
    <label className="flex items-center gap-2 text-sm text-ink-2">
      Urutkan
      <select
        value={current}
        disabled={isPending}
        onChange={(event) => navigate({ ...withoutPage(query), sort: event.target.value })}
        className="h-9 rounded-md border border-line bg-card px-2 text-sm text-ink focus:border-teal focus:outline-none"
      >
        {SORT_OPTIONS.filter((option) => option.value !== "relevance" || query.q).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Removable chips for every active filter, labelled with the same text as the panel. */
export function ActiveFilters({ labels }: { labels: Partial<Record<MultiFilter, Record<string, string>>> }) {
  const { query, navigate } = useFilterNavigation();
  const chips: { key: string; label: string; next: FilterQuery }[] = [];

  if (query.q) chips.push({ key: "q", label: `“${query.q}”`, next: withoutKeyword(query) });
  for (const key of MULTI_FILTERS) {
    for (const value of query[key] ?? []) {
      const label = key === "tag" ? `Tag: ${value}` : (labels[key]?.[value] ?? value);
      chips.push({ key: `${key}:${value}`, label, next: toggleValue(query, key, value) });
    }
  }
  if (query.salary_disclosed === "true") {
    chips.push({ key: "salary_disclosed", label: "Gaji dicantumkan", next: { ...withoutPage(query), salary_disclosed: undefined } });
  }
  if (query.salary_min) {
    chips.push({ key: "salary_min", label: `Gaji ≥ ${formatRupiahShort(Number(query.salary_min))}`, next: { ...withoutPage(query), salary_min: undefined } });
  }
  if (query.salary_max) {
    chips.push({ key: "salary_max", label: `Gaji ≤ ${formatRupiahShort(Number(query.salary_max))}`, next: { ...withoutPage(query), salary_max: undefined } });
  }
  if (!chips.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-ink-3">Filter aktif:</span>
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={() => navigate(chip.next)}
          className="inline-flex items-center gap-1 rounded-md border border-blue-line bg-blue-wash px-2.5 py-1 text-blue hover:border-blue/40"
          aria-label={`Hapus filter ${chip.label}`}
        >
          {chip.label} <X aria-hidden className="size-3.5" />
        </button>
      ))}
    </div>
  );
}
