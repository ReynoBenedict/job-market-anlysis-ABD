/** Plain-language explanations of the backend's data-quality flags. */
export const QUALITY_FLAG_TEXT: Record<string, string> = {
  SALARY_PERIOD_ASSUMED: "Periode gaji tidak tertulis; diasumsikan bulanan sesuai konvensi tampilan sumber.",
  SALARY_CURRENCY_ASSUMED: "Mata uang gaji tidak tertulis; diasumsikan rupiah.",
  SALARY_SINGLE_VALUE: "Sumber hanya mencantumkan satu angka gaji, bukan rentang.",
  SALARY_WIDE_RANGE: "Rentang gaji sangat lebar (maksimum lebih dari 4× minimum).",
  SALARY_HIGH_OUTLIER: "Gaji maksimum di atas Rp100 juta per bulan; kemungkinan salah ketik di sumber.",
  SALARY_LOW_OUTLIER: "Gaji minimum di bawah Rp500 ribu per bulan.",
  SALARY_MIN_GREATER_THAN_MAX: "Batas bawah gaji melebihi batas atas; gaji dianggap tidak valid.",
  TAGS_TRUNCATED: "Sumber hanya menampilkan sebagian tag; daftar tag tidak lengkap.",
  LOCATION_UNRESOLVED: "Lokasi tidak dapat dipetakan ke provinsi.",
  ROLE_UNCLASSIFIED: "Judul belum cocok dengan aturan klasifikasi bidang pekerjaan.",
  POSTING_AGE_APPROXIMATE: "Umur lowongan di sumber dibulatkan (minggu/bulan).",
  INVALID_SOURCE_URL: "Tautan sumber tidak valid sehingga tidak ditampilkan.",
};
