import { Suspense } from "react";

import { Card, CardHeader, CardSkeleton, ErrorState, PageHeader, StatTile } from "@/components/ui";
import { adminApi, type Quality } from "@/lib/admin-api";
import { apiErrorMessage } from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/format";
import { QUALITY_FLAG_TEXT } from "@/lib/quality-flags";

export const metadata = { title: "Kualitas Data" };

const FIELD_LABELS: Record<string, string> = {
  company_name: "Perusahaan",
  city: "Kota",
  province: "Provinsi",
  employment_type: "Jenis pekerjaan",
  experience: "Pengalaman",
  education: "Pendidikan",
  salary: "Gaji",
  description: "Deskripsi",
  source_url: "URL sumber",
  published_at: "Tanggal publikasi",
};

export default function QualityPage() {
  return (
    <>
      <PageHeader title="Kualitas data" description="Kelengkapan kolom dan tanda kualitas pada seluruh lowongan kanonis." />
      <Suspense fallback={<CardSkeleton rows={10} />}>
        <QualityReport />
      </Suspense>
    </>
  );
}

async function QualityReport() {
  let report: Quality;
  try {
    report = await adminApi.quality();
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/admin/kualitas" />;
  }
  const total = report.total_jobs || 1;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile label="Lowongan kanonis" value={formatNumber(report.total_jobs)} />
        <StatTile label="Rekaman sumber" value={formatNumber(report.total_source_records)} note="Lebih banyak dari lowongan bila ada kecocokan lintas sumber" />
        <StatTile
          label="Kemungkinan duplikat (satu sumber)"
          value={formatNumber(report.jobs_in_fingerprint_groups)}
          note={`${formatNumber(report.same_source_fingerprint_groups)} kelompok judul+perusahaan+kota yang sama; tidak digabung otomatis`}
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Kolom kosong atau tidak dicantumkan" />
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(report.missing).map(([field, count]) => (
                <tr key={field} className="border-t border-sunken first:border-t-0">
                  <th scope="row" className="py-2 text-left font-normal text-ink-2">{FIELD_LABELS[field] ?? field}</th>
                  <td className="tabular py-2 text-right text-ink">{formatNumber(count)}</td>
                  <td className="tabular w-20 py-2 text-right text-ink-3">{formatPercent(count / total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card>
          <CardHeader title="Tanda kualitas" />
          <ul className="space-y-3 text-sm">
            {Object.entries(report.flags).map(([flag, count]) => (
              <li key={flag} className="flex justify-between gap-4">
                <span>
                  <span className="font-mono text-xs text-ink-3">{flag}</span>
                  <span className="block text-ink-2">{QUALITY_FLAG_TEXT[flag] ?? ""}</span>
                </span>
                <span className="tabular shrink-0 font-semibold text-ink">{formatNumber(count)}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Keyakinan lokasi" />
          <ul className="space-y-1 text-sm">
            {Object.entries(report.location_confidence).map(([key, count]) => (
              <li key={key} className="flex justify-between"><span className="text-ink-2">{key}</span><span className="tabular">{formatNumber(count)}</span></li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Versi normalisasi" description="Semua baris sebaiknya berada pada versi yang sama." />
          <ul className="space-y-1 text-sm">
            {Object.entries(report.normalization_versions).map(([key, count]) => (
              <li key={key} className="flex justify-between"><span className="font-mono text-xs text-ink-2">{key}</span><span className="tabular">{formatNumber(count)}</span></li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
