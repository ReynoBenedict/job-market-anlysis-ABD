import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Badge, Card, CardSkeleton, ErrorState, PageHeader } from "@/components/ui";
import { api, apiErrorMessage, type SourceCoverage } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { METHOD_EXPLANATION } from "@/lib/status";

export const metadata: Metadata = { title: "Sumber Data" };

/** Unused sources grouped by why they are unused, most restrictive first. */
const UNUSED_GROUPS: { status: string[]; title: string; text: string; tone: "danger" | "warn" | "neutral" | "teal" }[] = [
  {
    status: ["BLOCKED"],
    title: "Diblokir",
    text: "Ketentuan situsnya melarang pengambilan data otomatis tanpa izin tertulis, jadi kami tidak mengambil data dari situs ini. Lowongan Glints di TalentScope hanya berasal dari satu snapshot lama (lihat di atas).",
    tone: "danger",
  },
  {
    status: ["REQUIRES_WRITTEN_PERMISSION"],
    title: "Perlu izin tertulis",
    text: "Baru bisa dipakai jika pemilik situs memberi izin tertulis.",
    tone: "warn",
  },
  {
    status: ["NEEDS_REVIEW", "DISCOVERED"],
    title: "Belum selesai diperiksa",
    text: "Ketentuannya belum bisa dipastikan, misalnya halaman ketentuan tidak dapat dibuka. Kami tidak mengambil datanya sampai ketentuannya jelas.",
    tone: "neutral",
  },
  {
    status: ["APPROVED", "APPROVED_WITH_CONDITIONS", "PAUSED", "RETIRED"],
    title: "Boleh dipakai, tetapi belum diimpor",
    text: "Lisensinya mengizinkan, tetapi datanya belum diimpor karena hanya berisi angka ringkasan, bukan lowongan.",
    tone: "teal",
  },
];

/** The reviewer's English decision record, kept available but behind a disclosure. */
function ReviewNote({ reason, reviewedAt }: { reason: string; reviewedAt: string | null }) {
  return (
    <details className="mt-2 text-sm text-ink-2">
      <summary className="cursor-pointer font-medium text-teal-text">Catatan teknis peninjauan (bahasa Inggris)</summary>
      <p className="mt-2 text-xs text-ink-3">Ditinjau {reviewedAt ? formatDate(reviewedAt) : "–"}.</p>
      <p lang="en" className="mt-1 text-xs text-ink-2 [overflow-wrap:anywhere]">
        {reason}
      </p>
    </details>
  );
}

export default function SourcesPage() {
  return (
    <>
      <PageHeader
        title="Sumber Data"
        description="Dari mana lowongan di TalentScope berasal, dan situs mana yang sengaja tidak kami ambil datanya. Halaman yang bisa dibuka publik belum tentu boleh dikumpulkan atau ditampilkan ulang."
        aside={
          <Link href="/metodologi" className="text-sm font-medium text-teal-text underline">
            Cara kami menghitung →
          </Link>
        }
      />
      <Suspense fallback={<CardSkeleton rows={10} />}>
        <Sources />
      </Suspense>
    </>
  );
}

async function Sources() {
  let sources: SourceCoverage[];
  let publisherSites: number | null = null;
  try {
    const [coverage, overview] = await Promise.all([api.sources(), api.overview().catch(() => null)]);
    sources = coverage;
    publisherSites = overview?.publisher_sites ?? null;
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/sumber-data" />;
  }
  const contributing = sources.filter((source) => source.job_count > 0);
  const unused = sources.filter((source) => source.job_count === 0);

  return (
    <div className="space-y-6">
      <section aria-labelledby="sumber-aktif">
        <h2 id="sumber-aktif" className="mb-3 text-xl font-semibold text-ink">
          Kumpulan data yang dipakai ({contributing.length})
        </h2>
        {publisherSites ? (
          <p className="-mt-1 mb-3 text-sm text-ink-2">
            Lowongan yang punya tautan ke halaman asalnya berasal dari {formatNumber(publisherSites)} situs asal; satu kumpulan
            data arsip web bisa memuat halaman dari banyak situs.
          </p>
        ) : null}
        <div className="grid gap-4 lg:grid-cols-2">
          {contributing.map((source) => (
            <Card key={source.id}>
              {/* Both badges sit in one row under the title so cards with long and short names line up. */}
              <h3 className="text-lg font-semibold text-ink">{source.name}</h3>
              <p className="text-sm text-ink-3">{METHOD_EXPLANATION[source.method.code]}</p>
              <p className="mt-3 flex flex-wrap gap-2">
                <Badge tone="blue" pill>
                  {source.method.label}
                </Badge>
                <Badge tone="teal" pill title="Status penggunaan menurut peninjauan ketentuan sumber">
                  {source.public_label ?? source.permission_status.label}
                </Badge>
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-ink-3">Lowongan ditampilkan</dt>
                  <dd className="tabular text-lg font-semibold text-ink">{formatNumber(source.job_count)}</dd>
                </div>
                <div>
                  <dt className="text-ink-3">Terakhir diimpor ke TalentScope</dt>
                  <dd className="font-medium text-ink">
                    {source.last_successful_run_at ? formatDate(source.last_successful_run_at) : "–"}
                  </dd>
                </div>
              </dl>
              {source.coverage_note ? <p className="mt-3 text-sm text-ink-2">{source.coverage_note}</p> : null}
              {source.attribution ? <p className="mt-2 text-sm text-ink-2">{source.attribution}</p> : null}
              {source.public_condition ? (
                <p className="mt-3 text-sm text-ink-2">
                  <strong className="font-semibold text-ink">Syarat penggunaan:</strong> {source.public_condition}
                </p>
              ) : null}
              {source.decision_reason ? <ReviewNote reason={source.decision_reason} reviewedAt={source.reviewed_at} /> : null}
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="sumber-lain">
        <h2 id="sumber-lain" className="text-xl font-semibold text-ink">
          Sumber lain yang sudah kami periksa ({unused.length})
        </h2>
        <p className="mt-1 text-sm text-ink-2">
          Tidak ada lowongan dari sumber-sumber ini di TalentScope. Setiap keputusan didasarkan pada ketentuan penggunaan,
          dokumentasi API, atau lisensi yang kami baca; bila halamannya tidak bisa dibuka, sumbernya belum kami pakai.
        </p>
        <div className="mt-4 space-y-3">
          {UNUSED_GROUPS.map((group) => {
            const members = unused.filter((source) => group.status.includes(source.permission_status.code));
            if (!members.length) return null;
            return (
              <details key={group.title} className="card group p-4 md:p-5">
                <summary className="flex cursor-pointer list-none flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4 [&::-webkit-details-marker]:hidden">
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-1 font-semibold text-ink">
                      {group.title}
                      <Badge tone={group.tone} pill className="whitespace-nowrap">
                        {members.length} sumber
                      </Badge>
                    </span>
                    <span className="mt-0.5 block text-sm text-ink-2">{group.text}</span>
                  </span>
                  <span className="shrink-0 text-sm font-medium text-teal-text">
                    <span className="group-open:hidden">Lihat daftar</span>
                    <span className="hidden group-open:inline">Tutup daftar</span>
                  </span>
                </summary>
                <ul className="mt-4 divide-y divide-sunken border-t border-line">
                  {members.map((source) => (
                    <li key={source.id} className="py-3">
                      <p className="font-medium text-ink">
                        {source.name}
                        {source.canonical_domain ? (
                          <span className="ml-2 font-mono text-xs font-normal text-ink-3">{source.canonical_domain}</span>
                        ) : null}
                      </p>
                      {source.public_condition ? <p className="mt-1 text-sm text-ink-2">{source.public_condition}</p> : null}
                      {source.decision_reason ? (
                        <ReviewNote reason={source.decision_reason} reviewedAt={source.reviewed_at} />
                      ) : null}
                    </li>
                  ))}
                </ul>
              </details>
            );
          })}
        </div>
        <p className="mt-4 text-xs text-ink-3">
          Kutipan ketentuan dan tanggal peninjauan setiap sumber ada di dokumentasi proyek (docs/RESEARCH_SOURCES.md dan
          docs/data-engineering/DOMAIN_REVIEW.md). Status bisa berubah jika ketentuan berubah atau izin diberikan.
        </p>
      </section>
    </div>
  );
}
