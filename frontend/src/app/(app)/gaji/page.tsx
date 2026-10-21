import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Histogram } from "@/components/charts/histogram";
import { QuartileChart } from "@/components/charts/quartile-chart";
import { DataScopeNotice } from "@/components/data-scope";
import { FilterNavigationProvider, PendingRegion } from "@/components/explorer/filter-navigation";
import { FilterPanel } from "@/components/explorer/filter-panel";
import { ActiveFilters } from "@/components/explorer/result-controls";
import {
  Card,
  CardFootnote,
  CardHeader,
  CardSkeleton,
  cx,
  ErrorState,
  PageHeader,
  SampleSize,
} from "@/components/ui";
import { api, apiErrorMessage, retryHref } from "@/lib/api";
import { jobsHref } from "@/lib/drilldown";
import { buildFilterGroups, filterLabels } from "@/lib/filter-groups";
import { countActiveFilters, type MultiFilter, readFilters, type SearchParamsRecord, serializeFilters } from "@/lib/filters";
import { formatNumber, formatPercent, formatRupiahShort } from "@/lib/format";

export const metadata: Metadata = { title: "Gaji" };

const COMPARISONS: { by: string; filter: MultiFilter; label: string }[] = [
  { by: "role_family", filter: "role_family", label: "Bidang" },
  { by: "province", filter: "province", label: "Provinsi" },
  { by: "experience", filter: "experience", label: "Pengalaman" },
  { by: "employment_type", filter: "employment_type", label: "Jenis pekerjaan" },
  { by: "education", filter: "education", label: "Pendidikan" },
];

export default function SalaryPage({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader
        title="Gaji"
        description="Berapa gaji yang dicantumkan di lowongan, per bidang, daerah, pengalaman, dan pendidikan. Gunakan filter untuk mempersempit."
      />
      <Suspense fallback={<CardSkeleton rows={12} />}>
        <Salary searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Salary({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const params = await searchParams;
  const query = readFilters(params, ["by"]);
  const comparison = COMPARISONS.find((item) => item.by === query.by) ?? COMPARISONS[0];

  let options, overview, compare;
  try {
    [options, overview, compare] = await Promise.all([
      api.filters(),
      api.salaryOverview(query),
      api.salaryCompare({ ...query, by: comparison.by, limit: 20 }),
    ]);
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref={retryHref(error, "/gaji", serializeFilters(query))} />;
  }
  const percentiles = overview.percentiles;
  const flagged = Object.values(overview.flag_counts).reduce((sum, count) => sum + count, 0);
  const tabHref = (by: string) => `/gaji?${serializeFilters({ ...query, by })}`;

  return (
    <FilterNavigationProvider query={query}>
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <FilterPanel groups={buildFilterGroups(options)} />
        <PendingRegion label="Hasil analisis gaji">
          <div className="space-y-6">
            <ActiveFilters labels={filterLabels(options)} />
            <DataScopeNotice scope={overview.scope} />

            <section aria-labelledby="ringkasan-gaji" className="card p-5 md:p-6">
              <h2 id="ringkasan-gaji" className="text-sm font-medium text-ink-3">
                Gaji tengah yang dicantumkan{countActiveFilters(query) ? " (sesuai filter)" : ""}
              </h2>
              {percentiles ? (
                <>
                  <p className="tabular mt-1 font-display text-4xl font-bold text-ink">
                    {formatRupiahShort(percentiles.p50)}
                    <span className="ml-1 text-lg font-medium text-ink-2">/bulan</span>
                  </p>
                  <p className="mt-2 max-w-2xl text-ink-2">
                    Separuh lowongan di tengah mencantumkan gaji antara{" "}
                    <strong className="tabular text-ink">{formatRupiahShort(percentiles.p25)}</strong> dan{" "}
                    <strong className="tabular text-ink">{formatRupiahShort(percentiles.p75)}</strong> per bulan.
                  </p>
                </>
              ) : (
                <p className="mt-1 text-ink-2">
                  Belum cukup data: perlu minimal {overview.min_records_for_statistics} lowongan bergaji untuk filter ini.
                </p>
              )}
              <p className="mt-3 text-sm text-ink-3">
                Dihitung dari {formatNumber(overview.eligible)} lowongan yang mencantumkan gaji bulanan dalam rupiah (
                {formatPercent(overview.eligible_share)} dari {formatNumber(overview.total_jobs)} lowongan). Lowongan tanpa
                gaji tidak dihitung, bukan dianggap nol.
                {overview.excluded_implausible
                  ? ` ${formatNumber(overview.excluded_implausible)} gaji yang tidak wajar (rentang terbalik atau titik tengah di bawah ${formatRupiahShort(overview.min_monthly_midpoint)}/bulan) juga tidak dihitung.`
                  : null}
              </p>
              <details className="mt-3 text-sm text-ink-2">
                <summary className="cursor-pointer font-medium text-teal-text">Apa arti angka ini?</summary>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  <li>
                    <strong>Gaji tengah (median)</strong>: separuh lowongan mencantumkan gaji di bawah angka ini dan separuh
                    di atasnya. Ini bukan jaminan gaji yang akan kamu terima.
                  </li>
                  <li>Jika lowongan mencantumkan rentang (mis. 4–6 juta), yang dipakai adalah titik tengahnya (5 juta).</li>
                  <li>Gaji per jam, per hari, atau dalam mata uang asing tidak dicampur dengan gaji bulanan.</li>
                  {overview.period_assumed ? (
                    <li>
                      {formatNumber(overview.period_assumed)} gaji tidak menyebut periode; kami anggap per bulan karena begitu
                      cara sumbernya menampilkan gaji.
                    </li>
                  ) : null}
                  <li>Gaji di iklan lowongan belum tentu sama dengan gaji yang akhirnya ditawarkan.</li>
                </ul>
              </details>
            </section>

            <Card>
              <CardHeader
                title={`Bandingkan per ${comparison.label.toLowerCase()}`}
                description={`Batang menunjukkan rentang gaji separuh lowongan di tengah (p25–p75); garis tegak adalah median. Kelompok dengan kurang dari ${compare.min_records_for_statistics} lowongan bergaji tidak diberi angka, dan di bawah ${compare.small_sample_threshold} ditandai "sampel kecil".`}
              />
              <nav aria-label="Bandingkan berdasarkan" className="mb-5 flex flex-wrap gap-2">
                {COMPARISONS.map((item) => (
                  <Link
                    key={item.by}
                    href={tabHref(item.by)}
                    aria-current={item.by === comparison.by ? "page" : undefined}
                    scroll={false}
                    className={cx(
                      "inline-flex h-10 items-center rounded-md border px-3 text-sm font-medium",
                      item.by === comparison.by
                        ? "border-teal bg-teal text-white"
                        : "border-line bg-card text-ink-2 hover:border-line-strong",
                    )}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
              <QuartileChart
                minRecords={compare.min_records_for_statistics}
                rows={compare.groups.map((group) => ({
                  key: group.key ?? "unknown",
                  label: group.label,
                  n: group.n,
                  jobsInGroup: group.jobs_in_group,
                  p25: group.p25 ?? null,
                  median: group.median ?? null,
                  p75: group.p75 ?? null,
                  smallSample: group.small_sample,
                  href: group.key ? jobsHref({ ...query, salary_disclosed: "true" }, comparison.filter, group.key) : undefined,
                }))}
              />
              <CardFootnote>
                Perbedaan antarkelompok mencerminkan lowongan dalam sampel ini, bukan upah pasar secara umum. Sumber dengan
                cakupan berbeda dapat menghasilkan angka yang berbeda.
              </CardFootnote>
            </Card>
            <Card>
              <CardHeader
                title="Sebaran gaji bulanan"
                description="Berapa banyak lowongan di setiap rentang gaji (titik tengah rentang yang dicantumkan)."
                action={<SampleSize n={overview.eligible} />}
              />
              {overview.histogram.length ? (
                <Histogram bins={overview.histogram} caption="Jumlah lowongan per rentang titik tengah gaji bulanan (lebar kelas Rp 2 juta)" />
              ) : (
                <p className="text-sm text-ink-2">Tidak ada gaji yang dapat dianalisis untuk filter ini.</p>
              )}
              <CardFootnote>
                {flagged
                  ? `${formatNumber(overview.flag_counts.SALARY_HIGH_OUTLIER ?? 0)} gaji di atas Rp100 juta/bulan dan ${formatNumber(overview.flag_counts.SALARY_WIDE_RANGE ?? 0)} rentang sangat lebar ditandai sebagai anomali tetapi tetap dihitung; median dan persentil tidak banyak terpengaruh oleh nilai ekstrem. `
                  : null}
                Median gaji minimum: {overview.median_min ? formatRupiahShort(overview.median_min) : "–"} · median gaji maksimum:{" "}
                {overview.median_max ? formatRupiahShort(overview.median_max) : "–"}.{" "}
                <Link className="font-medium text-teal-text underline" href="/metodologi#gaji">
                  Cara perhitungan
                </Link>
              </CardFootnote>
            </Card>

          </div>
        </PendingRegion>
      </div>
    </FilterNavigationProvider>
  );
}
