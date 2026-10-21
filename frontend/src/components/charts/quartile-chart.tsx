import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { formatNumber, formatRupiahShort } from "@/lib/format";

import { niceTicks } from "./ticks";

export interface QuartileRow {
  key: string;
  label: string;
  n: number;
  jobsInGroup: number;
  p25: number | null;
  median: number | null;
  p75: number | null;
  smallSample: boolean;
  href?: string;
}

/**
 * One row per group: the interquartile range as a bar and the median as a tick on a
 * shared scale. Groups below the minimum sample show no statistics at all.
 */
export function QuartileChart({ rows, minRecords }: { rows: QuartileRow[]; minRecords: number }) {
  // The shared scale starts at Rp0 and ends on a round tick, so bar positions can be read off the axis.
  const ticks = niceTicks(Math.max(...rows.map((row) => row.p75 ?? 0), 1));
  const scaleMax = ticks[ticks.length - 1];
  const position = (value: number) => `${(value / scaleMax) * 100}%`;
  const scale = (
    <div aria-hidden className="relative h-4 text-[11px] font-normal normal-case tracking-normal text-ink-3">
      {ticks.map((tick, index) => (
        <span
          key={tick}
          className={`tabular absolute top-0 whitespace-nowrap ${index === 0 ? "" : index === ticks.length - 1 ? "-translate-x-full" : "-translate-x-1/2"}`}
          style={{ left: position(tick) }}
        >
          {tick === 0 ? "Rp0" : formatRupiahShort(tick)}
        </span>
      ))}
    </div>
  );

  return (
    <div>
      <div className="hidden grid-cols-[minmax(0,14rem)_1fr_7rem] items-end gap-4 border-b border-line pb-2 text-xs font-medium uppercase tracking-wide text-ink-2 md:grid">
        <span>Kelompok</span>
        <span>
          <span className="block">Separuh di tengah (p25–p75) · garis = median</span>
          <span className="mt-1 block">{scale}</span>
        </span>
        <span className="text-right">Sampel gaji</span>
      </div>
      <div className="border-b border-line pb-2 md:hidden">
        <p className="text-xs font-medium text-ink-2">Batang: separuh lowongan di tengah (p25–p75). Garis: median.</p>
        <div className="mt-1">{scale}</div>
      </div>
      <ul className="divide-y divide-sunken">
        {rows.map((row) => (
          <li key={row.key} className="grid gap-2 py-3 md:grid-cols-[minmax(0,14rem)_1fr_7rem] md:items-center md:gap-4">
            <div className="min-w-0 text-sm font-medium text-ink">
              {row.href ? (
                <Link href={row.href} className="hover:text-teal-text hover:underline">
                  {row.label}
                </Link>
              ) : (
                row.label
              )}
            </div>
            {row.median !== null && row.p25 !== null && row.p75 !== null ? (
              <div>
                <div className="relative h-6" aria-hidden>
                  <div className="absolute inset-y-[11px] left-0 right-0 rounded-full bg-sunken" />
                  <div
                    className="absolute inset-y-[7px] rounded-[4px] bg-teal/35"
                    style={{ left: position(row.p25), width: `calc(${position(row.p75)} - ${position(row.p25)})` }}
                  />
                  <div className="absolute inset-y-[3px] w-[3px] -translate-x-1/2 rounded-full bg-teal-text" style={{ left: position(row.median) }} />
                </div>
                <p className="tabular mt-0.5 text-xs text-ink-2">
                  Median <span className="font-semibold text-ink">{formatRupiahShort(row.median)}</span> · p25{" "}
                  {formatRupiahShort(row.p25)} · p75 {formatRupiahShort(row.p75)}
                </p>
              </div>
            ) : (
              <p className="flex items-center gap-1.5 text-xs text-warn">
                <AlertTriangle aria-hidden className="size-3.5" />
                Statistik tidak ditampilkan: kurang dari {minRecords} lowongan dengan gaji.
              </p>
            )}
            <div className="flex items-center gap-2 text-sm md:justify-end">
              <span className="tabular text-ink-2" title={`${row.n} dari ${row.jobsInGroup} lowongan mencantumkan gaji`}>
                n = {formatNumber(row.n)}
              </span>
              {row.smallSample && row.median !== null ? (
                <span className="rounded-full border border-warn-line bg-warn-wash px-2 text-[11px] font-medium text-warn">
                  sampel kecil
                </span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
