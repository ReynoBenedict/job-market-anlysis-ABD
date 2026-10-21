import type { Metadata } from "next";
import { Suspense } from "react";

import { DataScopeNotice } from "@/components/data-scope";
import { FilterNavigationProvider, PendingRegion } from "@/components/explorer/filter-navigation";
import { FilterPanel } from "@/components/explorer/filter-panel";
import { Pagination } from "@/components/explorer/pagination";
import { ActiveFilters, SortSelect } from "@/components/explorer/result-controls";
import { SearchBar } from "@/components/explorer/search-bar";
import { JobCard } from "@/components/jobs/job-card";
import { CardSkeleton, EmptyState, ErrorState, LinkButton, PageHeader, Skeleton } from "@/components/ui";
import { api, apiErrorMessage, retryHref } from "@/lib/api";
import { buildFilterGroups, filterLabels } from "@/lib/filter-groups";
import {
  countActiveFilters,
  MAX_PAGE,
  readFilters,
  type SearchParamsRecord,
  serializeFilters,
  SORT_VALUES,
} from "@/lib/filters";
import { formatNumber } from "@/lib/format";

export const metadata: Metadata = { title: "Cari Lowongan" };

const PAGE_SIZE = 20;

export default function JobsPage({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader
        title="Cari Lowongan"
        description="Cari berdasarkan posisi, perusahaan, atau kota, lalu persempit dengan filter. Setiap lowongan menunjukkan asal datanya dan apakah masih mungkin dibuka."
      />
      <Suspense fallback={<ExplorerSkeleton />}>
        <Explorer searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Explorer({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const query = readFilters(await searchParams, ["sort", "page"]);
  // An unknown sort (edited or outdated link) falls back to the default instead of failing.
  if (query.sort && !(SORT_VALUES as readonly string[]).includes(query.sort)) delete query.sort;
  // Beyond the last page the empty state explains it; beyond the API's limit too.
  const page = Math.min(MAX_PAGE, Math.max(1, Number.parseInt(query.page ?? "1", 10) || 1));

  let options, results, overview;
  try {
    [options, results, overview] = await Promise.all([
      api.filters(),
      api.jobs({ ...query, page, page_size: PAGE_SIZE }),
      api.overview(query),
    ]);
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref={retryHref(error, "/lowongan", serializeFilters(query))} />;
  }
  const first = (page - 1) * PAGE_SIZE + 1;
  const returnQuery = serializeFilters(query);
  const anyAssumedPeriod = results.items.some((job) => job.salary.period_assumed);

  return (
    <FilterNavigationProvider query={query}>
      <div className="card mb-6 p-4 md:p-5">
        {/* Remount when the query changes elsewhere (e.g. its chip is removed) so the box shows it. */}
        <SearchBar key={query.q ?? ""} />
      </div>
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <FilterPanel groups={buildFilterGroups(options)} resultCount={results.total} />
        <PendingRegion label="Hasil pencarian lowongan">
          <div className="mb-4 flex flex-col gap-3">
            <DataScopeNotice scope={overview.scope} />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink-2" aria-live="polite" data-testid="result-summary">
                {results.total ? (
                  <>
                    <strong className="text-ink">{formatNumber(results.total)}</strong> lowongan · menampilkan{" "}
                    {formatNumber(first)}–{formatNumber(first + results.items.length - 1)}
                  </>
                ) : (
                  // The empty state below explains the situation; this line only states the count.
                  <>
                    <strong className="text-ink">0</strong> lowongan
                  </>
                )}
              </p>
              {results.total ? <SortSelect /> : null}
            </div>
            <ActiveFilters labels={filterLabels(options)} />
          </div>

          {results.items.length ? (
            <div className="space-y-3">
              {results.items.map((job) => (
                <JobCard key={job.id} job={job} returnQuery={returnQuery} />
              ))}
            </div>
          ) : (
            <EmptyState
              title={page > results.total_pages && results.total ? "Halaman ini tidak ada" : "Tidak ada lowongan yang cocok"}
              description={
                countActiveFilters(query)
                  ? "Coba kata kunci yang lebih umum atau kurangi filter."
                  : "Belum ada lowongan di basis data. Jalankan impor data terlebih dahulu (lihat README)."
              }
              action={
                countActiveFilters(query) ? (
                  <LinkButton href="/lowongan" variant="secondary">
                    Mulai pencarian baru
                  </LinkButton>
                ) : undefined
              }
            />
          )}

          {anyAssumedPeriod ? (
            <p className="mt-4 text-xs text-ink-3">* Periode gaji tidak tertulis di sumber; kami anggap per bulan.</p>
          ) : null}
          <div className="mt-6">
            <Pagination basePath="/lowongan" query={query} page={page} totalPages={results.total_pages} />
          </div>
        </PendingRegion>
      </div>
    </FilterNavigationProvider>
  );
}

function ExplorerSkeleton() {
  return (
    <div aria-busy="true" aria-label="Memuat lowongan">
      <Skeleton className="mb-6 h-[76px] w-full" />
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <CardSkeleton rows={10} className="hidden lg:block" />
        <div className="space-y-3">
          <CardSkeleton rows={3} />
          <CardSkeleton rows={3} />
          <CardSkeleton rows={3} />
        </div>
      </div>
    </div>
  );
}
