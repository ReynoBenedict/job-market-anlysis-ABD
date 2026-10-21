/**
 * What a listing's status means to a job seeker. The API decides the status from evidence
 * (expiry date given by the source, when the listing was last seen); this module only
 * explains it. No status means "verified open": TalentScope does not re-check listings live.
 */

export type StatusCode = "POTENTIALLY_ACTIVE" | "NOT_SEEN_RECENTLY" | "EXPIRED_BY_SOURCE";

export const STATUS_EXPLANATION: Record<StatusCode, string> = {
  POTENTIALLY_ACTIVE:
    "Lowongan ini terlihat baru-baru ini, tetapi TalentScope belum memeriksa apakah masih dibuka. Pastikan di situs aslinya.",
  NOT_SEEN_RECENTLY:
    "Lowongan ini tercatat pada pengamatan lama dan statusnya sekarang tidak diketahui. Anggap sebagai referensi, bukan lowongan yang pasti masih dibuka.",
  EXPIRED_BY_SOURCE:
    "Situs asal mencantumkan batas akhir yang sudah lewat. Lowongan ini kemungkinan besar sudah ditutup.",
};

export const METHOD_EXPLANATION: Record<string, string> = {
  ARCHIVE: "Halaman ini dibaca dari arsip web, bukan dari situsnya secara langsung.",
  SNAPSHOT: "Berasal dari satu kali pengumpulan data yang tidak diperbarui.",
  LIVE: "Dibaca langsung dari sumber.",
};

/** Hostname of a listing URL, for "dari situs …" labels; null for missing or non-http URLs. */
export function sourceHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return null;
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** Only http(s) URLs are rendered as links. */
export function safeExternalUrl(url: string | null | undefined): string | null {
  return sourceHost(url) ? (url as string) : null;
}
