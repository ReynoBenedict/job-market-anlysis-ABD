import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { BarList } from "@/components/charts/bar-list";
import { DataScopeNotice } from "@/components/data-scope";
import { FilterNavigationProvider, PendingRegion } from "@/components/explorer/filter-navigation";
import { FilterPanel } from "@/components/explorer/filter-panel";
import { ActiveFilters } from "@/components/explorer/result-controls";
import {
  Card,
  CardFootnote,
  CardHeader,
  CardSkeleton,
  EmptyState,
  ErrorState,
  LinkButton,
  PageHeader,
  StatTile,
} from "@/components/ui";
import { api, apiErrorMessage, type Breakdown, retryHref } from "@/lib/api";
import { jobsHref, toBarItems } from "@/lib/drilldown";
import { buildFilterGroups, filterLabels } from "@/lib/filter-groups";
import { type FilterQuery, type MultiFilter, readFilters, type SearchParamsRecord, serializeFilters } from "@/lib/filters";
import { formatNumber, formatPercent } from "@/lib/format";

export const metadata: Metadata = { title: "Bandingkan Pasar Kerja" };

const PANELS: { dimension: string; filter?: MultiFilter; title: string; note?: string }[] = [
  { dimension: "role_family", filter: "role_family", title: "Bidang pekerjaan" },
  { dimension: "province", filter: "province", title: "Provinsi" },
  { dimension: "city", filter: "city", title: "Kota / kabupaten" },
  { dimension: "employment_type", filter: "employment_type", title: "Jenis pekerjaan" },
  {
    dimension: "work_arrangement",
    filter: "work_arrangement",
    title: "Pengaturan kerja",
    note: "“Tidak dicantumkan” berarti sumber tidak menandai lowongan sebagai remote atau hybrid; itu bukan bukti kerja di kantor.",
  },
  { dimension: "experience", filter: "experience", title: "Pengalaman yang diminta" },
  { dimension: "education", filter: "education", title: "Pendidikan minimum" },
  { dimension: "company", title: "Perusahaan" },
];

export default function MarketPage({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader
        title="Bandingkan Pasar Kerja"
        description="Pilih provinsi, bidang, pendidikan, atau filter lain, dan semua angka di bawah berubah sesuai pilihanmu. Klik baris mana pun untuk melihat lowongannya."
      />
      <Suspense fallback={<CardSkeleton rows={12} />}>
        <Market searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Market({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const query: FilterQuery = readFilters(await searchParams);
  let options, overview, breakdowns: Breakdown[];
  try {
    [options, overview, ...breakdowns] = await Promise.all([
      api.filters(),
      api.overview(query),
      ...PANELS.map((panel) => api.breakdown(panel.dimension, { ...query, limit: 8 })),
    ]);
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref={retryHref(error, "/pasar", serializeFilters(query))} />;
  }

  return (
    <FilterNavigationProvider query={query}>
      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <FilterPanel groups={buildFilterGroups(options)} />
        <PendingRegion label="Hasil analisis pasar">
          <div className="space-y-6">
            <ActiveFilters labels={filterLabels(options)} />
            <DataScopeNotice scope={overview.scope} />
            {overview.total_jobs === 0 ? (
              <EmptyState
                title="Tidak ada lowongan untuk filter ini"
                description="Kurangi filter untuk melihat distribusi."
                action={<LinkButton href="/pasar" variant="secondary">Atur ulang filter</LinkButton>}
              />
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-3">
                  <StatTile
                    label="Lowongan"
                    value={formatNumber(overview.total_jobs)}
                    note={<Link className="font-medium text-teal-text underline" href={jobsHref(query)}>Lihat daftar lowongannya</Link>}
                  />
                  <StatTile label="Perusahaan" value={formatNumber(overview.companies)} note="Nama perusahaan berbeda yang membuka lowongan" />
                  <StatTile
                    label="Mencantumkan gaji"
                    value={formatPercent(overview.salary_disclosed_share)}
                    note={`${formatNumber(overview.salary_disclosed)} lowongan`}
                  />
                </div>
                <div className="grid gap-6 xl:grid-cols-2">
                  {PANELS.map((panel, index) => {
                    const breakdown = breakdowns[index];
                    return (
                      <Card key={panel.dimension}>
                        <CardHeader title={panel.title} />
                        <BarList caption={`Jumlah lowongan per ${panel.title.toLowerCase()}`} items={toBarItems(breakdown, query, panel.filter)} />
                        {breakdown.other_count || panel.note ? (
                          <CardFootnote>
                            {breakdown.other_count
                              ? `${formatNumber(breakdown.other_count)} lowongan di ${breakdown.distinct_values - breakdown.rows.length} kategori lain tidak ditampilkan. `
                              : null}
                            {panel.note}
                          </CardFootnote>
                        ) : null}
                      </Card>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </PendingRegion>
      </div>
    </FilterNavigationProvider>
  );
}
