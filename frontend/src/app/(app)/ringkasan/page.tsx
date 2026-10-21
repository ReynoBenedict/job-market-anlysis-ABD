import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, SlidersHorizontal } from "lucide-react";

import { BarList } from "@/components/charts/bar-list";
import { DataScopeNotice } from "@/components/data-scope";
import { Card, CardFootnote, CardHeader, CardSkeleton, ErrorState, LinkButton, PageHeader, StatTile } from "@/components/ui";
import { api, apiErrorMessage, type Breakdown } from "@/lib/api";
import { toBarItems } from "@/lib/drilldown";
import { formatNumber, formatPercent, formatRupiahShort } from "@/lib/format";

export const metadata: Metadata = { title: "Pasar Kerja" };

export default function OverviewPage() {
  return (
    <>
      <PageHeader
        title="Pasar Kerja"
        description="Bidang, daerah, dan perusahaan yang paling sering membuka lowongan, dihitung dari semua lowongan yang tercatat. Klik baris mana pun untuk melihat lowongannya."
        aside={
          <LinkButton href="/pasar" variant="secondary">
            <SlidersHorizontal aria-hidden className="size-4" /> Bandingkan dengan filter
          </LinkButton>
        }
      />
      <Suspense fallback={<OverviewSkeleton />}>
        <Overview />
      </Suspense>
    </>
  );
}

/** Footnote naming what a ranked list leaves out, so shares are not misread as complete. */
function RemainderNote({ breakdown, noun }: { breakdown: Breakdown; noun: string }) {
  const hidden = breakdown.distinct_values - breakdown.rows.length;
  if (hidden <= 0) return null;
  return (
    <>
      {formatNumber(breakdown.other_count)} lowongan lain tersebar di {formatNumber(hidden)} {noun} yang tidak ditampilkan.{" "}
    </>
  );
}

async function Overview() {
  let data;
  try {
    data = await Promise.all([
      api.overview(),
      api.breakdown("role_family", { limit: 10 }),
      api.breakdown("province", { limit: 8 }),
      api.breakdown("city", { limit: 8 }),
      api.breakdown("employment_type", { limit: 6 }),
      api.breakdown("company", { limit: 8 }),
      api.salaryOverview(),
    ]);
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/ringkasan" />;
  }
  const [overview, roles, provinces, cities, employment, companies, salary] = data;

  if (!overview.total_jobs) {
    return <ErrorState title="Belum ada data" message="Basis data masih kosong. Jalankan `talentscope bootstrap` (lihat README)." />;
  }
  const median = salary.percentiles?.p50;

  return (
    <div className="space-y-6">
      <DataScopeNotice scope={overview.scope} />

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile
          label="Lowongan tercatat"
          value={formatNumber(overview.total_jobs)}
          note={`Dari ${formatNumber(overview.companies)} perusahaan di ${formatNumber(overview.provinces)} provinsi. Lowongan yang sama di beberapa situs dihitung sekali.`}
        />
        <StatTile
          label="Mencantumkan gaji"
          value={formatPercent(overview.salary_disclosed_share)}
          note={`${formatNumber(overview.salary_disclosed)} lowongan. Sisanya tidak mencantumkan gaji, atau angkanya tidak bisa dipercaya.`}
        />
        <StatTile
          label="Gaji tengah per bulan"
          value={median ? formatRupiahShort(median) : "Belum cukup data"}
          note={
            <>
              Dari {formatNumber(salary.eligible)} lowongan bergaji.{" "}
              <Link href="/gaji" className="font-medium text-teal-text underline">
                Lihat analisis gaji
              </Link>
            </>
          }
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Bidang pekerjaan" description="Dikelompokkan dari judul lowongan." />
          <BarList caption="Jumlah lowongan per bidang pekerjaan" items={toBarItems(roles, {}, "role_family")} />
          <CardFootnote>
            <RemainderNote breakdown={roles} noun="bidang" />
            Bidang ditentukan dari kata di judul, jadi sebagian judul yang tidak umum masuk “Lainnya”.
          </CardFootnote>
        </Card>
        <Card>
          <CardHeader title="Provinsi" description="Lokasi kerja yang tertulis di lowongan." />
          <BarList caption="Jumlah lowongan per provinsi" items={toBarItems(provinces, {}, "province")} />
          <CardFootnote>
            <RemainderNote breakdown={provinces} noun="provinsi" />
            Banyaknya lowongan di suatu provinsi juga dipengaruhi situs mana yang tercatat, bukan hanya jumlah lowongan
            sebenarnya.
          </CardFootnote>
        </Card>
        <Card>
          <CardHeader title="Kota dan kabupaten" />
          <BarList caption="Jumlah lowongan per kota atau kabupaten" items={toBarItems(cities, {}, "city")} />
          <CardFootnote>
            <RemainderNote breakdown={cities} noun="kota/kabupaten" />
          </CardFootnote>
        </Card>
        <Card>
          <CardHeader title="Perusahaan dengan lowongan terbanyak" />
          <BarList caption="Perusahaan dengan lowongan terbanyak" items={toBarItems(companies, {})} />
          <CardFootnote>
            Nama perusahaan ditulis seperti di sumber, jadi satu perusahaan bisa muncul dengan beberapa nama (mis. dengan
            atau tanpa “PT”). Sebagian adalah penyalur tenaga kerja.
          </CardFootnote>
        </Card>
      </div>

      <Card>
        <CardHeader title="Jenis pekerjaan" description="Penuh waktu, kontrak, magang, dan lainnya, sesuai yang tertulis di lowongan." />
        <BarList caption="Jumlah lowongan per jenis pekerjaan" items={toBarItems(employment, {}, "employment_type")} />
      </Card>

      <Link
        href="/pasar"
        className="card flex items-center justify-between gap-4 p-5 hover:border-teal/45 hover:shadow-[var(--shadow-raised)]"
      >
        <span>
          <span className="block font-semibold text-ink">Ingin membandingkan daerah atau bidang tertentu?</span>
          <span className="mt-0.5 block text-sm text-ink-2">
            Pilih provinsi, bidang, pendidikan, atau pengalaman, lalu lihat semua angka berubah sesuai pilihanmu.
          </span>
        </span>
        <ArrowRight aria-hidden className="size-5 shrink-0 text-teal-text" />
      </Link>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }, (_, index) => (
          <CardSkeleton key={index} rows={2} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <CardSkeleton rows={8} />
        <CardSkeleton rows={8} />
      </div>
    </div>
  );
}
