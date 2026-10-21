import { Suspense } from "react";

import { Badge, CardSkeleton, ErrorState, PageHeader } from "@/components/ui";
import { adminApi, type AdminSource } from "@/lib/admin-api";
import { apiErrorMessage } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";

import { PauseForm } from "./pause-form";

export const metadata = { title: "Sumber Data" };

const RUNNABLE = new Set(["APPROVED", "APPROVED_WITH_CONDITIONS"]);

export default function AdminSourcesPage() {
  return (
    <>
      <PageHeader
        title="Registri sumber data"
        description="Status kelayakan hanya dapat diubah lewat CLI dengan alasan dan bukti (`talentscope sources set-status`). Halaman ini hanya dapat menjeda atau melanjutkan sumber yang sudah disetujui."
      />
      <Suspense fallback={<CardSkeleton rows={10} />}>
        <SourcesTable />
      </Suspense>
    </>
  );
}

async function SourcesTable() {
  let sources: AdminSource[];
  try {
    sources = await adminApi.sources();
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/admin" />;
  }
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[900px] text-sm">
        <caption className="sr-only">Sumber data dan status operasional</caption>
        <thead>
          <tr className="bg-canvas text-left text-xs uppercase tracking-wide text-ink-2">
            <th scope="col" className="px-4 py-3 font-medium">Sumber</th>
            <th scope="col" className="px-4 py-3 font-medium">Kelayakan</th>
            <th scope="col" className="px-4 py-3 font-medium">Konektor</th>
            <th scope="col" className="px-4 py-3 font-medium">Eksekusi terakhir</th>
            <th scope="col" className="w-72 px-4 py-3 font-medium">Operasi</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr key={source.id} className="border-t border-sunken align-top">
              <td className="px-4 py-3">
                <p className="font-medium text-ink">{source.name}</p>
                <p className="font-mono text-xs text-ink-3">{source.id}</p>
              </td>
              <td className="px-4 py-3">
                <Badge tone={RUNNABLE.has(source.permission_status.code) ? "teal" : source.permission_status.code === "BLOCKED" ? "danger" : "warn"} pill>
                  {source.permission_status.label}
                </Badge>
                <p className="mt-1 text-xs text-ink-3">Ditinjau {source.reviewed_at ? formatDate(source.reviewed_at) : "–"}</p>
              </td>
              <td className="px-4 py-3 text-ink-2">
                {source.connector ?? <span className="text-ink-3">Belum ada</span>}
                {source.is_paused ? <Badge className="ml-2">Dijeda</Badge> : null}
              </td>
              <td className="px-4 py-3 text-xs text-ink-2">
                {source.last_run_at ? (
                  <>
                    {source.last_run_status} · {formatDateTime(source.last_run_at)}
                    <br />
                    Berhasil terakhir: {source.last_success_at ? formatDateTime(source.last_success_at) : "–"}
                  </>
                ) : (
                  "Belum pernah"
                )}
              </td>
              <td className="px-4 py-3">
                {source.connector ? (
                  <PauseForm sourceId={source.id} paused={source.is_paused} canResume={RUNNABLE.has(source.permission_status.code)} />
                ) : (
                  <span className="text-xs text-ink-3">Tidak ada konektor untuk dijalankan.</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
