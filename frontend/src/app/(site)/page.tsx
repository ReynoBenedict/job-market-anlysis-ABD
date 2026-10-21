import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, BarChart3, History, MapPin, Search, Wallet } from "lucide-react";

import { Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate, formatNumber, formatPercent, formatRupiahShort } from "@/lib/format";

const EXAMPLE_SEARCHES = ["admin", "staff gudang", "perawat", "sales", "Bekasi", "Surabaya"];

const TASKS = [
  {
    href: "/lowongan",
    icon: Search,
    title: "Cari lowongan",
    text: "Cari berdasarkan posisi, perusahaan, atau kota, lalu buka halaman sumbernya bila tersedia (lowongan lama mungkin sudah dihapus).",
  },
  {
    href: "/gaji",
    icon: Wallet,
    title: "Cek kisaran gaji",
    text: "Lihat gaji yang dicantumkan di lowongan yang tercatat, per bidang dan per daerah.",
  },
  {
    href: "/ringkasan",
    icon: BarChart3,
    title: "Lihat pasar kerja",
    text: "Bidang dan daerah mana yang paling sering muncul di lowongan yang tercatat.",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="border-b border-line bg-gradient-to-b from-card to-canvas">
        <div className="mx-auto max-w-7xl px-4 pb-12 pt-8 md:px-6 md:pb-14 md:pt-12">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-warn-line bg-warn-wash px-3 py-1 text-[13px] font-medium text-ink sm:text-sm">
            <History aria-hidden className="size-4 shrink-0 text-warn" />
            Arsip lowongan, bukan yang sedang dibuka
          </p>
          <h1 className="max-w-4xl font-display text-[28px] font-bold leading-tight tracking-tight text-ink sm:text-[32px] md:text-[44px]">
            Cari lowongan yang pernah tayang dan pahami <span className="text-teal-text">gaji di daerahmu</span>.
          </h1>
          <p className="mt-4 max-w-3xl text-base text-ink-2 md:text-lg">
            TalentScope menghimpun lowongan kerja Indonesia yang pernah tayang (sebagian besar dari arsip web), dengan
            keterangan asal setiap lowongan, supaya kamu bisa melihat gambaran peluang, gaji yang dicantumkan, dan daerah
            yang paling banyak membuka lowongan.
          </p>

          <form action="/lowongan" role="search" className="card mt-8 flex flex-col gap-3 p-3 sm:flex-row md:p-4">
            <label htmlFor="home-search" className="sr-only">
              Cari posisi, perusahaan, atau kota
            </label>
            <div className="relative flex-1">
              <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-ink-3" />
              <input
                id="home-search"
                name="q"
                type="search"
                maxLength={100}
                placeholder="Posisi, perusahaan, atau kota"
                className="h-12 w-full rounded-md border border-line bg-card pl-11 pr-3 text-base focus:border-teal focus:outline-none focus:ring-[3px] focus:ring-teal/15"
              />
            </div>
            <button type="submit" className="h-12 rounded-md bg-teal px-6 text-base font-semibold text-white hover:bg-teal-hover">
              Cari Lowongan
            </button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-ink-3">Coba:</span>
            {EXAMPLE_SEARCHES.map((example) => (
              <Link
                key={example}
                href={`/lowongan?q=${encodeURIComponent(example)}`}
                className="inline-flex h-9 items-center rounded-full border border-line bg-card px-3 text-ink-2 hover:border-teal hover:text-teal-text"
              >
                {example}
              </Link>
            ))}
          </div>

          <Suspense fallback={<Skeleton className="mt-8 h-24 w-full" />}>
            <DataStatusSummary />
          </Suspense>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 md:px-6">
        <h2 className="text-2xl font-bold text-ink">Apa yang bisa kamu lakukan</h2>
        <ul className="mt-5 grid gap-4 md:grid-cols-3">
          {TASKS.map(({ href, icon: Icon, title, text }) => (
            <li key={href}>
              <Link
                href={href}
                className="card group flex h-full flex-col p-5 transition-shadow hover:border-teal/45 hover:shadow-[var(--shadow-raised)]"
              >
                <span className="flex size-10 items-center justify-center rounded-md bg-teal-wash text-teal-text">
                  <Icon aria-hidden className="size-5" />
                </span>
                <span className="mt-3 text-lg font-semibold text-ink">{title}</span>
                <span className="mt-1 text-sm text-ink-2">{text}</span>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-teal-text">
                  Buka <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            </li>
          ))}
        </ul>

        <Suspense fallback={<Skeleton className="mt-10 h-40 w-full" />}>
          <Highlights />
        </Suspense>
      </section>
    </>
  );
}

/** What the data is (and is not), with the real counts behind each statement. */
async function DataStatusSummary() {
  let data;
  try {
    data = await Promise.all([api.overview(), api.filters()]);
  } catch {
    return (
      <p className="mt-8 text-sm text-ink-3">
        Ringkasan data belum dapat dimuat. Coba muat ulang halaman beberapa saat lagi.
      </p>
    );
  }
  const [overview, options] = data;
  const statusCount = (code: string) => options.freshness.find((option) => option.value === code)?.count ?? 0;
  const expired = statusCount("EXPIRED_BY_SOURCE");
  const recent = statusCount("POTENTIALLY_ACTIVE");
  const { scope } = overview;
  const range = (from: string | null, to: string | null) => (from && to ? `${formatDate(from)} – ${formatDate(to)}` : null);
  const published = range(scope.published_from, scope.published_to);
  // observed_from/to are min/max last_seen_at (archive capture or snapshot date), not posting dates.
  const observed = range(scope.observed_from, scope.observed_to);
  const dates = [
    published ? `Tanggal tayang ${published}` : null,
    observed ? `${published ? "terakhir" : "Terakhir"} terlihat ${observed}` : null,
  ]
    .filter(Boolean)
    .join("; ");

  return (
    <section aria-labelledby="status-data" className="mt-8 rounded-lg border border-warn-line bg-warn-wash p-4 text-sm md:p-5">
      <h2 id="status-data" className="font-sans text-sm font-semibold tracking-normal text-ink">
        {/* "Kumpulan data" are ingestion datasets; publisher sites are the websites the archive pages came from. */}
        {formatNumber(overview.total_jobs)} lowongan tercatat dari {formatNumber(scope.sources.length)} kumpulan data dan{" "}
        {formatNumber(overview.publisher_sites)} situs asal.
      </h2>
      {dates ? <p className="mt-1 text-ink-2">{dates}.</p> : null}
      <ul className="mt-2 grid gap-1.5 text-ink-2 md:grid-cols-3 md:gap-4">
        <li>
          {/* No status means "verified open" (lib/status.ts), so this count is structurally zero. */}
          <strong className="text-ink">0 yang terverifikasi masih dibuka.</strong> TalentScope belum memeriksa ulang
          lowongan ke situs asalnya
          {recent ? `; ${formatNumber(recent)} terlihat dalam ${scope.freshness_window_days} hari terakhir` : ""}.
        </li>
        <li>
          <strong className="text-ink">{formatPercent(expired / Math.max(overview.total_jobs, 1))}</strong> sudah lewat
          batas lamaran menurut situs asalnya; sisanya tidak diketahui statusnya.
        </li>
        <li>
          Sebagian besar berasal dari situs info lowongan daerah; sebagian situs itu menayangkan ulang lowongan dari
          sumber lain.{" "}
          <Link href="/sumber-data" className="font-medium text-teal-text underline">
            Lihat sumbernya
          </Link>
        </li>
      </ul>
    </section>
  );
}

async function Highlights() {
  let data;
  try {
    data = await Promise.all([
      api.salaryOverview(),
      api.breakdown("role_family", { limit: 3 }),
      api.breakdown("province", { limit: 3 }),
    ]);
  } catch {
    return null;
  }
  const [salary, roles, provinces] = data;
  // "Other / unclassified" is not a finding; show the largest named field instead.
  const topRole = roles.rows.find((row) => row.key && row.key !== "OTHER");
  const topProvince = provinces.rows.find((row) => row.key);

  const cards = [
    salary.percentiles
      ? {
          label: "Gaji tengah yang dicantumkan",
          value: `${formatRupiahShort(salary.percentiles.p50)}/bulan`,
          note: `Dari ${formatNumber(salary.eligible)} lowongan yang mencantumkan gaji (${formatPercent(salary.eligible_share)} dari semua): separuh di bawah angka ini, separuh di atasnya.`,
          href: "/gaji",
          action: "Lihat gaji",
        }
      : null,
    topRole
      ? {
          label: "Bidang yang paling sering muncul",
          value: topRole.label,
          note: `${formatNumber(topRole.count)} lowongan (${formatPercent(topRole.share)} dari semua)${
            roles.rows[0]?.key === "OTHER" ? ", di luar judul yang belum terklasifikasi" : ""
          }.`,
          href: `/lowongan?role_family=${topRole.key}`,
          action: "Lihat lowongannya",
        }
      : null,
    topProvince
      ? {
          label: "Provinsi dengan lowongan terbanyak",
          value: topProvince.label,
          note: `${formatNumber(topProvince.count)} lowongan (${formatPercent(topProvince.share)}).`,
          href: `/lowongan?province=${encodeURIComponent(topProvince.key ?? "")}`,
          action: "Lihat lowongannya",
        }
      : null,
  ].filter((card) => card !== null);

  if (!cards.length) return null;
  return (
    <div className="mt-12">
      <h2 className="text-2xl font-bold text-ink">Sekilas dari data</h2>
      <p className="mt-1 text-sm text-ink-3">Dihitung dari lowongan yang tercatat, bukan dari seluruh pasar kerja Indonesia.</p>
      <ul className="mt-5 grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <li key={card.label} className="card flex flex-col p-5">
            <p className="text-sm text-ink-3">{card.label}</p>
            <p className="mt-1 font-display text-2xl font-bold text-ink">{card.value}</p>
            <p className="mt-2 text-sm text-ink-2">{card.note}</p>
            <Link href={card.href} className="mt-auto inline-flex items-center gap-1 pt-4 text-sm font-semibold text-teal-text hover:underline">
              {card.action} <ArrowRight aria-hidden className="size-4" />
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-6 flex items-start gap-2 text-sm text-ink-3">
        <MapPin aria-hidden className="mt-0.5 size-4 shrink-0" />
        Lowongan tercatat tidak merata antardaerah: {provinces.rows.filter((row) => row.key).map((row) => row.label).join(", ")}{" "}
        mendominasi, sehingga angka untuk provinsi lain dihitung dari sampel yang jauh lebih kecil.
      </p>
    </div>
  );
}
