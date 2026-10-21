/**
 * Shared axis helpers. Kept outside the "use client" histogram module so server components
 * (e.g. the quartile chart) can call them.
 */

/** Axis ticks at a 1-2-5 step giving about four intervals; counts never need fractions. */
export function niceTicks(max: number, intervals = 4): number[] {
  const rough = max / intervals;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = Math.max(1, [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 1);
  const top = Math.ceil(max / step) * step;
  return Array.from({ length: top / step + 1 }, (_, index) => index * step);
}
