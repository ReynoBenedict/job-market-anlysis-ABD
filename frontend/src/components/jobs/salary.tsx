import { BanknoteX, Info, Wallet } from "lucide-react";

import type { JobSummary } from "@/lib/api";
import { formatRupiahRange } from "@/lib/format";

type Salary = JobSummary["salary"];

// Set by the lake when a site shows one identical salary on most of its listings.
const TEMPLATE_SALARY_TEXT = "Nilai gaji berasal dari templat situs dan tidak dipakai";

/**
 * A monthly rupiah salary the API does not consider comparable (reversed range, or a midpoint
 * too low to be a monthly wage, e.g. "Rp 2 – Rp 897"): shown only as source text, never as a salary.
 */
export function isImplausibleSalary(salary: Salary): boolean {
  return (
    salary.status.code === "DISCLOSED" &&
    salary.currency === "IDR" &&
    salary.period.code === "MONTH" &&
    salary.min !== null &&
    salary.max !== null &&
    !salary.comparable
  );
}

export function salaryRangeText(salary: Salary): string | null {
  if (salary.status.code !== "DISCLOSED" || isImplausibleSalary(salary)) return null;
  if (salary.currency === "IDR") return formatRupiahRange(salary.min, salary.max);
  if (salary.min === null || salary.max === null) return null;
  return `${salary.currency ?? ""} ${salary.min.toLocaleString("id-ID")} – ${salary.max.toLocaleString("id-ID")}`.trim();
}

function missingSalaryText(salary: Salary): string {
  if (isImplausibleSalary(salary)) {
    const raw = salary.min === salary.max ? `Rp${salary.min}` : `Rp${salary.min} – Rp${salary.max}`;
    return `Angka di sumber (${raw}) tidak wajar untuk gaji bulanan, jadi tidak ditampilkan sebagai gaji dan tidak dihitung dalam statistik.`;
  }
  if (salary.text === TEMPLATE_SALARY_TEXT) {
    return "Situs asal menampilkan angka gaji yang sama untuk hampir semua lowongannya, jadi angka itu tidak kami anggap sebagai gaji lowongan ini.";
  }
  if (salary.status.code === "NOT_DISCLOSED") return "Pemberi kerja tidak mencantumkan gaji.";
  return `Gaji di sumber tidak dapat dipakai${salary.text ? ` (“${salary.text}”)` : ""}.`;
}

/** Salary block for the job detail page; never shows a missing salary as zero. */
export function SalaryBlock({ salary }: { salary: Salary }) {
  const range = salaryRangeText(salary);
  if (!range) {
    return (
      <div className="flex items-start gap-2 rounded-md bg-sunken px-3 py-2.5 text-sm text-ink-2">
        <BanknoteX aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-3" />
        <span>
          <span className="font-medium text-ink">Gaji tidak tersedia.</span> {missingSalaryText(salary)}
        </span>
      </div>
    );
  }
  return (
    <div className="rounded-md border border-teal-line bg-teal-wash/60 px-3 py-2.5">
      <p className="flex items-center gap-2 text-xs text-ink-3">
        <Wallet aria-hidden className="size-3.5" /> Gaji yang dicantumkan
      </p>
      <p className="tabular mt-0.5 font-display text-lg font-semibold text-teal-text">
        {range}
        <span className="ml-1 text-sm font-normal text-ink-2">{salary.period.label}</span>
      </p>
      {salary.period_assumed ? (
        <p className="mt-1 flex items-start gap-1.5 text-xs text-ink-3">
          <Info aria-hidden className="mt-0.5 size-3 shrink-0" />
          Periode tidak tertulis di sumber; kami anggap per bulan karena begitulah sumber menampilkan gaji.
        </p>
      ) : null}
      <p className="mt-1 text-xs text-ink-3">Gaji di iklan lowongan belum tentu sama dengan gaji yang akhirnya ditawarkan.</p>
    </div>
  );
}
