"use client";

import { type FormEvent, useState } from "react";
import { SlidersHorizontal } from "lucide-react";

import { Button, cx } from "@/components/ui";
import {
  clearFilters,
  countActiveFilters,
  millionsToRupiah,
  type MultiFilter,
  rupiahToMillions,
  toggleValue,
  withoutPage,
} from "@/lib/filters";
import { formatNumber } from "@/lib/format";

import { useFilterNavigation } from "./filter-navigation";

export interface FilterOption {
  value: string;
  label: string;
  count: number;
}

export interface FilterGroup {
  key: MultiFilter;
  title: string;
  options: FilterOption[];
  /** Options shown before "Tampilkan semua". */
  initiallyVisible?: number;
}

function CheckboxGroup({ group }: { group: FilterGroup }) {
  const { query, navigate, isPending } = useFilterNavigation();
  const [expanded, setExpanded] = useState(false);
  const selected = query[group.key] ?? [];
  const limit = group.initiallyVisible ?? 8;
  // Selected values stay visible even when the list is collapsed.
  const visible = expanded
    ? group.options
    : group.options.filter((option, index) => index < limit || selected.includes(option.value));

  return (
    <div role="group" aria-labelledby={`filter-${group.key}`} className="border-t border-line pt-4">
      <h3 id={`filter-${group.key}`} className="mb-2 font-sans text-xs font-semibold uppercase tracking-wider text-ink-2">
        {group.title}
      </h3>
      <ul className="space-y-1">
        {visible.map((option) => {
          const id = `${group.key}-${option.value}`;
          const checked = selected.includes(option.value);
          return (
            <li key={option.value}>
              <label htmlFor={id} className="flex min-h-9 cursor-pointer items-center gap-2.5 rounded-sm py-1 text-sm text-ink">
                <input
                  id={id}
                  type="checkbox"
                  checked={checked}
                  disabled={isPending}
                  onChange={() => navigate(toggleValue(query, group.key, option.value))}
                  className="size-4 shrink-0 rounded-sm border-line-strong accent-teal"
                />
                <span className="min-w-0 flex-1 break-words">{option.label}</span>
                <span className="tabular text-xs text-ink-3">{formatNumber(option.count)}</span>
              </label>
            </li>
          );
        })}
      </ul>
      {group.options.length > limit ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="mt-1 text-xs font-medium text-teal-text hover:underline"
          aria-expanded={expanded}
        >
          {expanded ? "Tampilkan lebih sedikit" : `Tampilkan semua (${group.options.length})`}
        </button>
      ) : null}
    </div>
  );
}

function SalaryFilter() {
  const { query, navigate, isPending } = useFilterNavigation();
  const [min, setMin] = useState(rupiahToMillions(query.salary_min));
  const [max, setMax] = useState(rupiahToMillions(query.salary_max));
  const [error, setError] = useState<string | null>(null);

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextMin = millionsToRupiah(min);
    const nextMax = millionsToRupiah(max);
    if ((min.trim() && !nextMin) || (max.trim() && !nextMax)) {
      setError("Masukkan angka 0 sampai 10.000 dalam juta rupiah, mis. 7,5.");
      return;
    }
    if (nextMin && nextMax && Number(nextMin) > Number(nextMax)) {
      setError("Batas bawah tidak boleh melebihi batas atas.");
      return;
    }
    setError(null);
    navigate({ ...withoutPage(query), salary_min: nextMin, salary_max: nextMax });
  }

  function toggleDisclosed(checked: boolean) {
    navigate({ ...withoutPage(query), salary_disclosed: checked ? "true" : undefined });
  }

  return (
    <div role="group" aria-labelledby="filter-salary" className="border-t border-line pt-4">
      <h3 id="filter-salary" className="mb-2 font-sans text-xs font-semibold uppercase tracking-wider text-ink-2">
        Gaji bulanan (juta Rp)
      </h3>
      <form onSubmit={apply} noValidate>
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="salary-min">Gaji minimum (juta rupiah)</label>
          <input
            id="salary-min"
            inputMode="decimal"
            placeholder="Min"
            value={min}
            onChange={(event) => setMin(event.target.value)}
            className="h-10 w-full min-w-0 rounded-md border border-line px-2 text-sm focus:border-teal focus:outline-none"
            aria-describedby="salary-help"
          />
          <span aria-hidden className="text-ink-3">–</span>
          <label className="sr-only" htmlFor="salary-max">Gaji maksimum (juta rupiah)</label>
          <input
            id="salary-max"
            inputMode="decimal"
            placeholder="Maks"
            value={max}
            onChange={(event) => setMax(event.target.value)}
            className="h-10 w-full min-w-0 rounded-md border border-line px-2 text-sm focus:border-teal focus:outline-none"
            aria-describedby="salary-help"
          />
          <Button type="submit" variant="secondary" className="px-3" disabled={isPending}>
            Terapkan
          </Button>
        </div>
        <p id="salary-help" className="mt-1.5 text-xs text-ink-3">
          Contoh: 4 sampai 7,5. Menampilkan lowongan yang rentang gajinya beririsan dengan rentang ini.
        </p>
        {error ? (
          <p role="alert" className="mt-1 text-xs text-danger">
            {error}
          </p>
        ) : null}
      </form>
      <label className="mt-3 flex cursor-pointer items-start gap-2.5 rounded-md bg-sunken p-2.5 text-sm">
        <input
          type="checkbox"
          checked={query.salary_disclosed === "true"}
          onChange={(event) => toggleDisclosed(event.target.checked)}
          disabled={isPending}
          className="mt-0.5 size-4 accent-teal"
        />
        Hanya lowongan yang mencantumkan gaji
      </label>
    </div>
  );
}

export function FilterPanel({ groups, resultCount }: { groups: FilterGroup[]; resultCount?: number }) {
  const { query, navigate } = useFilterNavigation();
  const [open, setOpen] = useState(false);
  const active = countActiveFilters(query);
  const clearAll = () => navigate(clearFilters(query));

  return (
    <div>
      <button
        type="button"
        className="mb-3 flex w-full items-center justify-between rounded-md border border-line bg-card px-4 py-2.5 text-sm font-semibold lg:hidden"
        aria-expanded={open}
        aria-controls="filter-panel"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="flex items-center gap-2">
          <SlidersHorizontal aria-hidden className="size-4" /> Filter {active ? `(${active})` : null}
        </span>
        <span className="text-teal-text">{open ? "Tutup" : "Buka"}</span>
      </button>
      <div id="filter-panel" className={cx("card space-y-4 p-5 lg:block", open ? "block" : "hidden")}>
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <SlidersHorizontal aria-hidden className="size-4 text-ink-3" /> Filter
          </h2>
          {active ? (
            <button type="button" onClick={clearAll} className="text-xs font-medium text-teal-text hover:underline">
              Hapus semua filter
            </button>
          ) : null}
        </div>
        <p className="text-xs text-ink-3">Angka di samping pilihan dihitung dari seluruh data, bukan dari hasil saat ini.</p>
        {groups.map((group) => (
          <CheckboxGroup key={group.key} group={group} />
        ))}
        {/* Remount when the bounds change elsewhere (chip removed, Back/Forward, clear all) so the inputs show them. */}
        <SalaryFilter key={`${query.salary_min ?? ""}|${query.salary_max ?? ""}`} />
        <Button type="button" className="w-full lg:hidden" onClick={() => setOpen(false)}>
          {resultCount === undefined ? "Tutup filter" : `Lihat ${formatNumber(resultCount)} hasil`}
        </Button>
      </div>
    </div>
  );
}
