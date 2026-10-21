import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cx } from "@/components/ui";
import { type FilterQuery, serializeFilters } from "@/lib/filters";

/** Page numbers to show: first, last, and a window around the current page. */
export function pageWindow(current: number, total: number, radius = 1): (number | "gap")[] {
  const pages = new Set([1, total]);
  for (let page = current - radius; page <= current + radius; page++) {
    if (page >= 1 && page <= total) pages.add(page);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  return sorted.flatMap((page, index) => (index > 0 && page - sorted[index - 1] > 1 ? ["gap" as const, page] : [page]));
}

export function Pagination({
  basePath,
  query,
  page,
  totalPages,
}: {
  basePath: string;
  query: FilterQuery;
  page: number;
  totalPages: number;
}) {
  if (totalPages <= 1) return null;
  const href = (target: number) => {
    const search = serializeFilters({ ...query, page: target > 1 ? String(target) : undefined });
    return search ? `${basePath}?${search}` : basePath;
  };
  const linkClass = "inline-flex h-10 min-w-10 items-center justify-center rounded-md border px-3 text-sm";

  return (
    <nav aria-label="Halaman hasil" className="flex flex-wrap items-center justify-center gap-1.5">
      {page > 1 ? (
        <Link href={href(page - 1)} className={cx(linkClass, "border-line bg-card hover:border-line-strong")} rel="prev">
          <ChevronLeft aria-hidden className="size-4" /> Sebelumnya
        </Link>
      ) : null}
      {pageWindow(page, totalPages).map((item, index) =>
        item === "gap" ? (
          <span key={`gap-${index}`} className="px-1 text-ink-3" aria-hidden>
            …
          </span>
        ) : (
          <Link
            key={item}
            href={href(item)}
            aria-current={item === page ? "page" : undefined}
            aria-label={`Halaman ${item}`}
            className={cx(
              linkClass,
              item === page ? "border-teal bg-teal font-semibold text-white" : "border-line bg-card hover:border-line-strong",
            )}
          >
            {item}
          </Link>
        ),
      )}
      {page < totalPages ? (
        <Link href={href(page + 1)} className={cx(linkClass, "border-line bg-card hover:border-line-strong")} rel="next">
          Berikutnya <ChevronRight aria-hidden className="size-4" />
        </Link>
      ) : null}
    </nav>
  );
}
