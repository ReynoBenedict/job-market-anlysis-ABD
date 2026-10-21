"use client";

import { useEffect, useId, useRef, useState } from "react";

import { formatNumber, formatRupiahShort } from "@/lib/format";

import { niceTicks } from "./ticks";

// Re-exported for existing imports (lib.test.ts).
export { niceTicks };

export interface HistogramBin {
  lower: number;
  upper: number | null;
  count: number;
}

/** Width used before the container is measured (server render). */
const DEFAULT_WIDTH = 640;
const MIN_WIDTH = 240;
const HEIGHT = 220;
const PAD = { top: 12, right: 12, bottom: 40, left: 40 };
const GAP = 2;
/** Minimum horizontal room per axis label, in CSS pixels, so labels never collide. */
const MIN_LABEL_SPACING = 36;

/** Interval in words: lower bound included, upper bound excluded. */
export function binLabel(bin: HistogramBin): string {
  if (bin.upper === null) return `${formatRupiahShort(bin.lower)} atau lebih`;
  if (bin.lower === 0) return `di bawah ${formatRupiahShort(bin.upper)}`;
  return `${formatRupiahShort(bin.lower)} – di bawah ${formatRupiahShort(bin.upper)}`;
}

/** Axis value in millions with an Indonesian decimal comma (2_500_000 -> "2,5"). */
function millions(value: number): string {
  return String(Math.round(value / 100_000) / 10).replace(".", ",");
}

/**
 * Bin-edge labels for the x axis. Each bar spans the interval between two edge labels; an
 * open-ended last bin has no upper edge and is labelled "≥ x" under its bar instead.
 */
export function edgeLabels(bins: HistogramBin[], every: number): { index: number; label: string; centered: boolean }[] {
  if (!bins.length) return [];
  const openLast = bins[bins.length - 1].upper === null;
  const closed = openLast ? bins.length - 1 : bins.length;
  const edges = bins.slice(0, closed).map((bin, index) => ({ index, value: bin.lower }));
  if (closed > 0) edges.push({ index: closed, value: bins[closed - 1].upper ?? 0 });
  const labels = edges
    .filter((edge) => edge.index % every === 0 && !(openLast && edge.index === closed))
    .map((edge) => ({ index: edge.index, label: millions(edge.value), centered: false }));
  if (openLast) labels.push({ index: bins.length - 1, label: `≥${millions(bins[bins.length - 1].lower)}`, centered: true });
  return labels;
}

/**
 * Column histogram with a per-bar tooltip and a toggleable data table. The SVG is drawn at
 * the container's pixel width, so axis text stays 11px on phones instead of shrinking with
 * a scaled viewBox.
 */
export function Histogram({ bins, caption }: { bins: HistogramBin[]; caption: string }) {
  const [active, setActive] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const containerRef = useRef<HTMLDivElement>(null);
  const tableId = useId();

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(Math.round(entry.contentRect.width), MIN_WIDTH)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const ticks = niceTicks(Math.max(...bins.map((bin) => bin.count), 1));
  const top = ticks[ticks.length - 1];
  const plotWidth = width - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotWidth / Math.max(bins.length, 1);
  const barWidth = Math.max(slot - GAP, 1);
  const y = (value: number) => PAD.top + plotHeight - (value / top) * plotHeight;
  const edgeX = (index: number) => PAD.left + index * slot;
  const labels = edgeLabels(bins, Math.max(1, Math.ceil(MIN_LABEL_SPACING / slot)));
  const activeBin = active === null ? null : bins[active];

  return (
    <figure>
      <div ref={containerRef} className="relative">
        <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} className="block max-w-full" role="group" aria-label={caption}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(tick)} y2={y(tick)} stroke="#e2e8f0" strokeWidth={1} />
              <text x={PAD.left - 6} y={y(tick) + 4} textAnchor="end" className="fill-ink-3 text-xs tabular">
                {formatNumber(tick)}
              </text>
            </g>
          ))}
          {bins.map((bin, index) => {
            const x = edgeX(index) + GAP / 2;
            const height = Math.max(y(0) - y(bin.count), bin.count > 0 ? 1 : 0);
            const radius = Math.min(4, height / 2, barWidth / 2);
            return (
              <g key={bin.lower}>
                {/* 4px rounded data end, square at the baseline. */}
                <path
                  d={`M${x},${y(0)} v${-(height - radius)} q0,${-radius} ${radius},${-radius} h${barWidth - 2 * radius} q${radius},0 ${radius},${radius} v${height - radius} z`}
                  className={active === index ? "fill-teal-hover" : "fill-teal"}
                />
                <rect
                  x={edgeX(index)}
                  y={PAD.top}
                  width={slot}
                  height={plotHeight}
                  fill="transparent"
                  tabIndex={0}
                  role="img"
                  aria-label={`Gaji ${binLabel(bin)} per bulan: ${formatNumber(bin.count)} lowongan`}
                  onMouseEnter={() => setActive(index)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(index)}
                  onBlur={() => setActive(null)}
                />
              </g>
            );
          })}
          <line x1={PAD.left} x2={width - PAD.right} y1={y(0)} y2={y(0)} stroke="#cbd5e1" strokeWidth={1} />
          <g aria-hidden>
            {labels.map(({ index, label, centered }) => {
              const x = centered ? edgeX(index) + slot / 2 : edgeX(index);
              return (
                <g key={`${index}-${label}`}>
                  {centered ? null : <line x1={x} x2={x} y1={y(0)} y2={y(0) + 4} stroke="#94a3b8" strokeWidth={1} />}
                  <text x={x} y={y(0) + 17} textAnchor="middle" className="fill-ink-3 text-xs tabular">
                    {label}
                  </text>
                </g>
              );
            })}
          </g>
          <text x={PAD.left + plotWidth / 2} y={HEIGHT - 4} textAnchor="middle" className="fill-ink-3 text-xs">
            Titik tengah gaji bulanan (juta rupiah)
          </text>
        </svg>
        {activeBin ? (
          <div
            className="pointer-events-none absolute top-2 rounded-md border border-line bg-card px-3 py-2 text-xs shadow-[var(--shadow-float)]"
            style={{ left: `${Math.min((edgeX(active ?? 0) / width) * 100, 55)}%` }}
          >
            <p className="font-semibold text-ink">{binLabel(activeBin)}</p>
            <p className="tabular text-ink-2">{formatNumber(activeBin.count)} lowongan</p>
          </div>
        ) : null}
      </div>
      <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-ink-3">
        <span>
          {caption}. Tiap batang mencakup rentang di antara dua angka di bawahnya: angka kiri termasuk, angka kanan tidak.
        </span>
        <button
          type="button"
          className="font-medium text-teal-text underline"
          aria-expanded={showTable}
          aria-controls={tableId}
          onClick={() => setShowTable((shown) => !shown)}
        >
          {showTable ? "Sembunyikan tabel" : "Tampilkan sebagai tabel"}
        </button>
      </figcaption>
      {showTable ? (
        <table id={tableId} className="mt-3 w-full text-sm">
          <thead>
            <tr className="bg-canvas text-left text-xs uppercase tracking-wide text-ink-2">
              <th className="px-3 py-2 font-medium">Rentang titik tengah gaji per bulan</th>
              <th className="px-3 py-2 text-right font-medium">Lowongan</th>
            </tr>
          </thead>
          <tbody>
            {bins.map((bin) => (
              <tr key={bin.lower} className="border-t border-sunken">
                <td className="px-3 py-1.5">{binLabel(bin)}</td>
                <td className="tabular px-3 py-1.5 text-right">{formatNumber(bin.count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </figure>
  );
}
