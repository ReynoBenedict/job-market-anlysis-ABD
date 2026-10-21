import { Suspense } from "react";

import { Pagination } from "@/components/explorer/pagination";
import { Badge, CardSkeleton, EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { adminApi, type RunPage } from "@/lib/admin-api";
import { apiErrorMessage } from "@/lib/api";
import type { SearchParamsRecord } from "@/lib/filters";
import { formatDateTime, formatNumber } from "@/lib/format";

export const metadata = { title: "Riwayat Eksekusi" };

const STATUS_TONE: Record<string, "teal" | "warn" | "danger" | "neutral"> = {
  SUCCEEDED: "teal",
  PARTIAL: "warn",
  FAILED: "danger",
  REFUSED: "neutral",
  RUNNING: "neutral",
};

export default function RunsPage({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader title="Riwayat eksekusi ingestion" description="Setiap impor atau pengambilan data, termasuk yang ditolak oleh kebijakan sumber." />
      <Suspense fallback={<CardSkeleton rows={8} />}>
        <Runs searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Runs({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const page = Math.max(1, Number((await searchParams).page) || 1);
  let runs: RunPage;
  try {
    runs = await adminApi.runs({ page, page_size: 20 });
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/admin/riwayat" />;
  }
  if (!runs.items.length) return <EmptyState title="Belum ada eksekusi" description="Jalankan `talentscope bootstrap` untuk impor pertama." />;

  return (
    <div className="space-y-4">
      {runs.items.map((run) => (
        <article key={run.id} className="card p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium text-ink">
              {run.source_id} <span className="font-normal text-ink-3">· {run.mode} · {run.trigger}</span>
            </p>
            <Badge tone={STATUS_TONE[run.status.code]} pill>{run.status.label}</Badge>
          </div>
          <p className="mt-1 text-xs text-ink-3">
            Mulai {formatDateTime(run.started_at)}
            {run.duration_seconds !== null ? ` · ${run.duration_seconds?.toFixed(1)} detik` : null} · data diamati{" "}
            {formatDateTime(run.observed_at)} · parser {run.parser_version}
          </p>
          <dl className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {[
              ["Dibaca", run.records_seen],
              ["Baru", run.records_created],
              ["Diperbarui", run.records_updated],
              ["Tetap", run.records_unchanged],
              ["Ditolak", run.records_rejected],
              ["Cocok lintas sumber", run.cross_source_matches],
            ].map(([label, value]) => (
              <div key={label as string} className="rounded-md bg-sunken px-2 py-1.5">
                <dt className="text-[11px] text-ink-3">{label}</dt>
                <dd className="tabular font-semibold text-ink">{formatNumber(value as number)}</dd>
              </div>
            ))}
          </dl>
          {run.error_category ? (
            <p className="mt-3 rounded-md border border-warn-line bg-warn-wash px-3 py-2 text-xs text-ink-2">
              <strong>{run.error_category.label}:</strong> {run.message}
            </p>
          ) : null}
          {run.input_reference ? <p className="mt-2 break-all font-mono text-[11px] text-ink-3">{run.input_reference}</p> : null}
        </article>
      ))}
      <Pagination basePath="/admin/riwayat" query={{}} page={page} totalPages={runs.total_pages} />
    </div>
  );
}
