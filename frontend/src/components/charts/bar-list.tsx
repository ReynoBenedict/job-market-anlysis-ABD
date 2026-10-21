import Link from "next/link";

import { formatNumber, formatPercent } from "@/lib/format";

export interface BarListItem {
  key: string;
  label: string;
  count: number;
  share: number;
  href?: string;
}

/**
 * Ranked horizontal bars rendered as an ordered list. Values are printed as text,
 * so the chart is its own table view and nothing depends on color alone.
 */
export function BarList({ items, caption }: { items: BarListItem[]; caption: string }) {
  const max = Math.max(...items.map((item) => item.count), 1);
  return (
    <ol aria-label={caption} className="space-y-3">
      {items.map((item) => {
        const content = (
          <>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="min-w-0 break-words font-medium text-ink">{item.label}</span>
              <span className="tabular shrink-0 text-ink-2">
                {formatNumber(item.count)}
                <span className="ml-2 inline-block w-14 text-right text-xs text-ink-3">{formatPercent(item.share)}</span>
              </span>
            </div>
            <div className="mt-1.5 h-2 rounded-full bg-sunken" aria-hidden>
              <div
                className="h-2 rounded-full bg-teal transition-colors group-hover:bg-teal-hover"
                style={{ width: `${Math.max((item.count / max) * 100, 1.5)}%` }}
              />
            </div>
          </>
        );
        return (
          <li key={item.key} title={`${item.label}: ${formatNumber(item.count)} (${formatPercent(item.share)})`}>
            {item.href ? (
              <Link href={item.href} className="group block rounded-sm outline-offset-4">
                {content}
              </Link>
            ) : (
              <div className="group">{content}</div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
