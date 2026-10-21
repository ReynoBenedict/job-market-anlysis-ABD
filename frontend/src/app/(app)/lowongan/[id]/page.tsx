import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowLeft, CircleSlash, ExternalLink, FileX, History, LinkIcon } from "lucide-react";

import { locationText, postedText } from "@/components/jobs/job-card";
import { SalaryBlock } from "@/components/jobs/salary";
import { SaveJobButton } from "@/components/jobs/save-job-button";
import { StatusBadge } from "@/components/jobs/status-badge";
import { Badge, Card, CardHeader, CardSkeleton, ErrorState, LinkButton } from "@/components/ui";
import { api, ApiError, apiErrorMessage, type JobDetail } from "@/lib/api";
import { resultsHref } from "@/lib/drilldown";
import { formatDate, formatNumber } from "@/lib/format";
import { QUALITY_FLAG_TEXT } from "@/lib/quality-flags";
import { METHOD_EXPLANATION, safeExternalUrl, sourceHost, STATUS_EXPLANATION, type StatusCode } from "@/lib/status";

type Params = Promise<{ id: string }>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { id } = await params;
  try {
    const job = await api.job(id);
    return { title: `${job.title}${job.company_name ? ` — ${job.company_name}` : ""}` };
  } catch {
    return { title: "Detail Lowongan" };
  }
}

export default function JobDetailPage({ params, searchParams }: { params: Params; searchParams: SearchParams }) {
  return (
    <Suspense fallback={<CardSkeleton rows={8} />}>
      <JobDetailContent params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function JobDetailContent({ params, searchParams }: { params: Params; searchParams: SearchParams }) {
  const { id } = await params;
  const back = resultsHref((await searchParams).kembali);
  let job: JobDetail;
  try {
    job = await api.job(id);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    return <ErrorState message={apiErrorMessage(error)} retryHref={`/lowongan/${encodeURIComponent(id)}`} />;
  }
  const location = job.archive?.city_templated ? null : locationText(job);
  const originalUrl = safeExternalUrl(job.source_url);
  const site = sourceHost(job.source_url);

  return (
    <article className="mx-auto max-w-5xl">
      <Link href={back} className="mb-4 inline-flex h-10 items-center gap-1.5 text-sm font-medium text-teal-text hover:underline">
        <ArrowLeft aria-hidden className="size-4" /> Kembali ke hasil pencarian
      </Link>

      <header className="card mb-6 p-5 md:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap gap-2">
              <StatusBadge freshness={job.freshness} />
              <Badge tone="blue">{job.role_family.label}</Badge>
            </div>
            <h1 className="text-2xl font-semibold leading-tight text-ink [overflow-wrap:anywhere] md:text-3xl">{job.title}</h1>
            {job.archive?.source_title && job.archive.source_title !== job.title ? (
              <p className="mt-1 text-xs text-ink-3 [overflow-wrap:anywhere]">Judul di situs asal: “{job.archive.source_title}”</p>
            ) : null}
            <p className="mt-1 text-lg text-ink-2 [overflow-wrap:anywhere]">{job.company_name ?? "Perusahaan tidak dicantumkan"}</p>
            <p className="mt-1 text-sm text-ink-3">
              {location ?? (job.archive?.city_templated ? "Banyak lokasi" : "Lokasi tidak dicantumkan")}
              {job.employment_type.code !== "UNKNOWN" ? ` · ${job.employment_type.label}` : null}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-start gap-2">
            <SaveJobButton
              job={{ id: job.id, title: job.title, company: job.company_name, location, status: job.freshness.label }}
              withLabel
            />
            {originalUrl ? (
              <LinkButton href={originalUrl} target="_blank" rel="noopener noreferrer nofollow" variant="secondary">
                Buka halaman asli <ExternalLink aria-hidden className="size-4" />
              </LinkButton>
            ) : null}
          </div>
        </div>
        <StatusNotice job={job} />
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader title="Rincian lowongan" />
            <SalaryBlock salary={job.salary} />
            <dl className="mt-5 grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
              <Detail
                term="Lokasi"
                value={job.archive?.city_templated ? "Banyak lokasi" : location}
                source={job.location.text}
                note={job.archive?.city_templated ? "Situs asal membuat halaman serupa untuk berbagai daerah." : undefined}
              />
              <Detail
                term="Jenis pekerjaan"
                value={job.employment_type.code === "UNKNOWN" ? null : job.employment_type.label}
                source={job.employment_type_text}
              />
              <Detail
                term="Pengaturan kerja"
                value={job.work_arrangement.code === "UNKNOWN" ? null : job.work_arrangement.label}
                source={job.work_arrangement_evidence}
              />
              <Detail
                term="Pengalaman"
                value={job.experience.band.code === "UNKNOWN" ? null : job.experience.band.label}
                source={job.experience.text}
              />
              <Detail
                term="Pendidikan minimum"
                value={job.education.code === "UNKNOWN" ? null : job.education.label}
                source={job.education_text}
              />
              <Detail term="Bidang" value={job.role_family.label} note="Dikelompokkan TalentScope dari judul lowongan." />
            </dl>
            {job.source_tags.length ? (
              <div className="mt-5 border-t border-sunken pt-4">
                <p className="text-sm font-medium text-ink">Tag di sumber</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {job.source_tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
                {job.hidden_tag_count ? (
                  <p className="mt-2 text-xs text-ink-3">
                    Sumber menyembunyikan {job.hidden_tag_count} tag lain, jadi daftar ini bukan seluruh persyaratan.
                  </p>
                ) : null}
              </div>
            ) : null}
          </Card>

          <Card>
            <CardHeader title="Deskripsi pekerjaan" />
            {job.description ? (
              <p className="whitespace-pre-line text-[15px] text-ink-2">{job.description}</p>
            ) : (
              <div className="flex items-start gap-3 text-sm text-ink-2">
                <FileX aria-hidden className="mt-0.5 size-5 shrink-0 text-ink-3" />
                <p>
                  {job.source.method.code === "ARCHIVE"
                    ? "TalentScope tidak menampilkan deskripsi dari halaman arsip; hak atas teksnya milik situs asal."
                    : "Sumber data ini hanya berisi informasi dari kartu lowongan, tanpa deskripsi."}{" "}
                  {originalUrl ? "Baca deskripsi lengkap di halaman asli jika masih tersedia." : null}
                </p>
              </div>
            )}
          </Card>
        </div>

        <aside className="min-w-0 space-y-6">
          <Card>
            <CardHeader title="Asal data" as="h2" />
            <dl className="space-y-3 text-sm">
              <Row term="Sumber" value={job.source.name} note={METHOD_EXPLANATION[job.source.method.code]} />
              {site ? (
                <Row
                  term="Situs asal"
                  value={site}
                  note={
                    job.archive?.aggregator_site
                      ? "Situs ini menyalin lowongan dari sumber lain, jadi ini bukan iklan asli pemberi kerja. Cari iklan resminya sebelum melamar."
                      : undefined
                  }
                />
              ) : null}
              <Row
                term="Tanggal tayang"
                value={job.published_at ? formatDate(job.published_at) : (postedText(job)?.replace(/^Tayang /, "") ?? "Tidak dicantumkan")}
              />
              <Row
                term="Batas lamaran"
                value={job.expires_at ? formatDate(job.expires_at) : "Tidak diketahui"}
                note={
                  job.expires_at
                    ? undefined
                    : job.archive?.deadline_unreliable
                      ? `Situs asal mengisi batas lamaran secara otomatis (sama untuk hampir semua lowongannya${
                          job.archive.source_valid_through ? `, di sini ${formatDate(job.archive.source_valid_through)}` : ""
                        }), jadi tanggal itu tidak kami anggap sebagai batas lamaran.`
                      : "Sumber tidak mencantumkan batas lamaran yang dapat dipakai."
                }
              />
              <Row
                term={job.source.method.code === "ARCHIVE" ? "Diarsipkan" : "Dikumpulkan"}
                value={
                  job.first_seen_at.slice(0, 10) === job.last_seen_at.slice(0, 10)
                    ? formatDate(job.last_seen_at)
                    : `${formatDate(job.first_seen_at)} – ${formatDate(job.last_seen_at)}`
                }
              />
              <Row term="Diperiksa langsung" value="Belum pernah" note="TalentScope belum memeriksa ulang lowongan ke situs asalnya." />
              {job.archive ? (
                <Row
                  term="Ditemukan di"
                  value={`${formatNumber(job.archive.pages)} halaman, ${formatNumber(job.archive.sites.length)} situs`}
                  note={
                    job.archive.city_templated
                      ? "Situs asal membuat halaman serupa untuk banyak lokasi; semuanya dihitung sebagai satu lowongan tanpa satu lokasi pasti."
                      : job.archive.pages > 1
                        ? "Halaman-halaman yang sama digabung menjadi satu lowongan."
                        : undefined
                  }
                />
              ) : null}
            </dl>
            {!originalUrl ? (
              <p className="mt-4 flex items-start gap-2 rounded-md bg-sunken p-3 text-xs text-ink-2">
                <LinkIcon aria-hidden className="mt-0.5 size-3.5 shrink-0 text-ink-3" />
                Tautan asli tidak tersimpan untuk sumber ini.
              </p>
            ) : null}
            {job.source.attribution ? <p className="mt-4 text-xs text-ink-3">{job.source.attribution}</p> : null}
          </Card>

          {job.quality_flags.length ? (
            <Card>
              <CardHeader title="Catatan kualitas data" as="h2" />
              <ul className="space-y-2 text-sm text-ink-2">
                {job.quality_flags.map((flag) => (
                  <li key={flag} className="flex gap-2">
                    <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-warn" />
                    {QUALITY_FLAG_TEXT[flag] ?? flag}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          <details className="card p-5 text-xs text-ink-3">
            <summary className="cursor-pointer text-sm font-medium text-ink-2">Detail teknis</summary>
            <ul className="mt-2 space-y-1">
              {job.source_records.map((record) => (
                <li key={`${record.source.id}-${record.first_seen_at}`}>
                  {record.source.name}: identitas{" "}
                  {record.source_key_kind === "content_fingerprint" ? "sidik konten (sumber tidak memberi ID)" : record.source_key_kind},
                  aturan pencocokan {record.match_rule}
                </li>
              ))}
              <li>Versi normalisasi: {job.normalization_version}</li>
            </ul>
          </details>
        </aside>
      </div>
    </article>
  );
}

function StatusNotice({ job }: { job: JobDetail }) {
  const code = job.freshness.code as StatusCode;
  const expired = code === "EXPIRED_BY_SOURCE";
  const Icon = expired ? CircleSlash : History;
  return (
    <div
      className={`mt-4 flex items-start gap-3 rounded-md border p-3 text-sm ${
        expired ? "border-warn-line bg-warn-wash" : "border-line bg-sunken"
      }`}
    >
      <Icon aria-hidden className={`mt-0.5 size-5 shrink-0 ${expired ? "text-warn" : "text-ink-3"}`} />
      <div className="text-ink-2">
        <p className="font-semibold text-ink">
          {expired && job.expires_at
            ? `Batas lamaran sudah lewat (${formatDate(job.expires_at)})`
            : "Belum tentu masih dibuka"}
        </p>
        <p className="mt-0.5">{STATUS_EXPLANATION[code]} TalentScope tidak menerima lamaran.</p>
      </div>
    </div>
  );
}

function Row({ term, value, note }: { term: string; value: string; note?: string }) {
  return (
    <div>
      <dt className="text-ink-3">{term}</dt>
      <dd className="font-medium text-ink [overflow-wrap:anywhere]">{value}</dd>
      {note ? <dd className="mt-0.5 text-xs text-ink-3">{note}</dd> : null}
    </div>
  );
}

function Detail({ term, value, source, note }: { term: string; value: string | null; source?: string | null; note?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-ink-3">{term}</dt>
      <dd className="font-medium text-ink">{value ?? <span className="font-normal text-ink-3">Tidak dicantumkan</span>}</dd>
      {source && source !== value ? <dd className="text-xs text-ink-3 [overflow-wrap:anywhere]">Tertulis di sumber: “{source}”</dd> : null}
      {note ? <dd className="text-xs text-ink-3">{note}</dd> : null}
    </div>
  );
}
