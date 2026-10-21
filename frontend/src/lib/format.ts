const LOCALE = "id-ID";
const TIME_ZONE = "Asia/Jakarta";

const integer = new Intl.NumberFormat(LOCALE);
const percent = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 1 });
const rupiah = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});
const decimal = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });
const dateLong = new Intl.DateTimeFormat(LOCALE, { dateStyle: "long", timeZone: TIME_ZONE });
const dateTime = new Intl.DateTimeFormat(LOCALE, {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: TIME_ZONE,
});

export function formatNumber(value: number): string {
  return integer.format(value);
}

export function formatPercent(share: number): string {
  return percent.format(share);
}

/** Full rupiah amount, e.g. "Rp 5.500.000". */
export function formatRupiah(amount: number): string {
  return rupiah.format(amount).replace(/ /g, " ");
}

/** Compact rupiah in the "jt" (juta) style used on Indonesian job boards, e.g. "Rp 5,5 jt". */
export function formatRupiahShort(amount: number): string {
  if (amount >= 1_000_000) return `Rp ${decimal.format(amount / 1_000_000)} jt`;
  if (amount >= 1_000) return `Rp ${decimal.format(amount / 1_000)} rb`;
  return `Rp ${integer.format(amount)}`;
}

export function formatRupiahRange(min: number | null, max: number | null): string | null {
  if (min === null || max === null) return null;
  return min === max ? formatRupiah(min) : `${formatRupiah(min)} – ${formatRupiah(max)}`;
}

export function formatDate(iso: string): string {
  return dateLong.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

const dateShort = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeZone: TIME_ZONE });

/** e.g. "12 Mar 2026", for dense places such as job cards. */
export function formatDateShort(iso: string): string {
  return dateShort.format(new Date(iso));
}
