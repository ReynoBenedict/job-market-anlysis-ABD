import Link from "next/link";
import { History, Info } from "lucide-react";

import type { DatasetScope } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";

/**
 * One-sentence disclosure of what a page's numbers describe, with the sources and caveats
 * behind a disclosure so they never push the actual content down.
 */
export function DataScopeNotice({ scope }: { scope: DatasetScope }) {
  const period =
    scope.observed_from && scope.observed_to
      ? scope.observed_from.slice(0, 7) === scope.observed_to.slice(0, 7)
        ? formatDate(scope.observed_to)
        : `${formatDate(scope.observed_from)} – ${formatDate(scope.observed_to)}`
      : null;
  const Icon = scope.is_historical ? History : Info;
  return (
    <details
      className={`group rounded-lg border px-4 py-3 text-sm ${
        scope.is_historical ? "border-warn-line bg-warn-wash" : "border-teal-line bg-teal-wash"
      }`}
    >
      <summary className="flex cursor-pointer list-none items-start gap-2.5 [&::-webkit-details-marker]:hidden">
        <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${scope.is_historical ? "text-warn" : "text-teal-text"}`} />
        <span className="text-ink-2">
          <strong className="font-semibold text-ink">
            {scope.is_historical ? "Data lama, bukan daftar lowongan yang sedang dibuka." : "Data dari pengamatan terbaru."}
          </strong>{" "}
          {/* observed_* are archive-capture/snapshot dates (last_seen_at), not posting dates. */}
          {period ? `Terakhir terlihat ${period}. ` : null}
          <span className="font-medium text-teal-text underline group-open:hidden">Apa artinya?</span>
        </span>
      </summary>
      <div className="mt-2 space-y-1.5 pl-6 text-ink-2">
        <p>
          Kumpulan data: {scope.sources.map((source) => `${source.name} (${source.method.label.toLowerCase()})`).join("; ") || "tidak ada"}
          {scope.publisher_sites ? `, dengan halaman dari ${formatNumber(scope.publisher_sites)} situs asal` : null}.
        </p>
        {scope.published_from && scope.published_to ? (
          <p>
            Tanggal tayang menurut situs asal: {formatDate(scope.published_from)} – {formatDate(scope.published_to)}.
          </p>
        ) : null}
        {scope.coverage_notes.map((note) => (
          <p key={note}>{note}</p>
        ))}
        <p>
          Angka di sini menggambarkan lowongan yang tercatat, bukan seluruh pasar kerja Indonesia.{" "}
          <Link href="/metodologi" className="font-medium text-teal-text underline">
            Cara kami menghitung
          </Link>
        </p>
      </div>
    </details>
  );
}
