import { Suspense } from "react";

import { Pagination } from "@/components/explorer/pagination";
import { CardSkeleton, EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { adminApi, type AuditPage } from "@/lib/admin-api";
import { apiErrorMessage } from "@/lib/api";
import type { SearchParamsRecord } from "@/lib/filters";
import { formatDateTime } from "@/lib/format";

export const metadata = { title: "Audit Perubahan" };

export default function AuditPageView({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader title="Audit perubahan" description="Catatan permanen atas perubahan status sumber dan tindakan admin." />
      <Suspense fallback={<CardSkeleton rows={8} />}>
        <AuditList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function AuditList({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const page = Math.max(1, Number((await searchParams).page) || 1);
  let events: AuditPage;
  try {
    events = await adminApi.audit({ page, page_size: 50 });
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/admin/audit" />;
  }
  if (!events.items.length) return <EmptyState title="Belum ada catatan audit" />;
  return (
    <div className="space-y-4">
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="bg-canvas text-left text-xs uppercase tracking-wide text-ink-2">
              <th scope="col" className="px-4 py-3 font-medium">Waktu</th>
              <th scope="col" className="px-4 py-3 font-medium">Pelaku</th>
              <th scope="col" className="px-4 py-3 font-medium">Tindakan</th>
              <th scope="col" className="px-4 py-3 font-medium">Alasan & rincian</th>
            </tr>
          </thead>
          <tbody>
            {events.items.map((event) => (
              <tr key={event.id} className="border-t border-sunken align-top">
                <td className="whitespace-nowrap px-4 py-3 text-ink-2">{formatDateTime(event.created_at)}</td>
                <td className="px-4 py-3">{event.actor}</td>
                <td className="px-4 py-3">
                  <span className="font-mono text-xs">{event.action}</span>
                  <span className="block text-xs text-ink-3">{event.entity_type}: {event.entity_id}</span>
                </td>
                <td className="px-4 py-3 text-ink-2">
                  {event.reason}
                  {Object.keys(event.details).length ? (
                    <code className="mt-1 block break-all text-[11px] text-ink-3">{JSON.stringify(event.details)}</code>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination basePath="/admin/audit" query={{}} page={page} totalPages={events.total_pages} />
    </div>
  );
}
