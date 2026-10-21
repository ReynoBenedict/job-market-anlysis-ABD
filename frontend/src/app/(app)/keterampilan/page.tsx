import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { EyeOff, Tags } from "lucide-react";

import { BarList } from "@/components/charts/bar-list";
import { Card, CardFootnote, CardHeader, CardSkeleton, cx, ErrorState, PageHeader, SampleSize, StatTile } from "@/components/ui";
import { api, apiErrorMessage } from "@/lib/api";
import { readFilters, type SearchParamsRecord } from "@/lib/filters";
import { formatNumber, formatPercent } from "@/lib/format";

export const metadata: Metadata = { title: "Keterampilan" };

export default function SkillsPage({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  return (
    <>
      <PageHeader
        title="Keterampilan"
        description="Keterampilan apa yang sering diminta? Data saat ini belum cukup untuk menjawabnya dengan pasti. Halaman ini menunjukkan apa yang sudah terlihat dan apa yang masih kurang."
      />
      <Suspense fallback={<CardSkeleton rows={10} />}>
        <Skills searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Skills({ searchParams }: { searchParams: Promise<SearchParamsRecord> }) {
  const query = readFilters(await searchParams);
  const selectedRole = query.role_family?.[0];
  let stats;
  try {
    stats = await api.sourceTags({ role_family: selectedRole, limit: 15 });
  } catch (error) {
    return <ErrorState message={apiErrorMessage(error)} retryHref="/keterampilan" />;
  }
  const totalTags = stats.visible_tags + stats.hidden_tags;
  const population = `${formatNumber(stats.total_jobs)} lowongan${selectedRole ? " pada bidang ini" : ""}`;

  return (
    <div className="space-y-6">
      <div role="note" className="flex gap-3 rounded-lg border border-warn-line bg-warn-wash p-4 text-sm text-ink-2">
        <EyeOff aria-hidden className="mt-0.5 size-5 shrink-0 text-warn" />
        <div>
          <p className="font-semibold text-ink">Belum bisa dijadikan peringkat keterampilan yang paling dicari</p>
          <p className="mt-1">
            Untuk menghitung keterampilan dengan benar, kami perlu deskripsi lowongan lengkap. Saat ini hanya snapshot
            Glints yang punya data keterampilan, berupa beberapa tag di kartu lowongan, dan sebagian besar tag
            disembunyikan oleh situsnya. Jadi angka di bawah adalah <em>tag yang kebetulan terlihat</em> pada{" "}
            {formatNumber(stats.total_jobs)} lowongan, bukan gambaran pasar kerja.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          label="Tag terlihat"
          value={formatPercent(totalTags ? stats.visible_tags / totalTags : 0)}
          icon={<Tags aria-hidden className="size-4" />}
          note={`${formatNumber(stats.visible_tags)} dari ${formatNumber(totalTags)} tag; sisanya tersembunyi di balik “+N” pada kartu`}
        />
        <StatTile
          label="Lowongan dengan tag tersembunyi"
          value={formatNumber(stats.jobs_with_hidden_tags)}
          note={`dari ${population}; kartunya menampilkan “+N” tag lain`}
        />
        <StatTile
          label="Lowongan tanpa tag terlihat"
          value={formatNumber(stats.total_jobs - stats.jobs_with_visible_tags)}
          note={`dari ${population}; tidak ada satu pun tag yang tampil`}
        />
      </div>
      <p className="-mt-2 text-sm text-ink-3">
        Kedua kelompok lowongan di atas bertumpang tindih, jadi angkanya tidak bisa dijumlahkan: kebanyakan kartu
        menampilkan satu sampai tiga tag lalu “+N” lainnya, sehingga punya tag terlihat sekaligus tag tersembunyi. Semua
        angka di halaman ini hanya dihitung dari lowongan sumber yang menampilkan tag (snapshot Glints); lowongan dari arsip
        web tidak termasuk. Tag “Hybrid” dan “Remote” dipindahkan ke pengaturan kerja, bukan dihitung sebagai keterampilan.
      </p>

      <Card>
        <CardHeader
          title="Tag yang paling sering terlihat di kartu lowongan Glints"
          description="Urutan ini hanya untuk tag yang kebetulan tampil, bukan peringkat keterampilan yang paling dicari. Pilih bidang untuk melihat tag pada lowongan bidang itu; klik tag untuk mencari lowongannya."
          action={<SampleSize n={stats.total_jobs} />}
        />
        <nav aria-label="Pilih bidang" className="mb-5 flex flex-wrap gap-2">
          {[{ key: undefined, label: "Semua bidang" }, ...stats.role_families.map((row) => ({ key: row.value, label: row.label }))].map((item) => (
            <Link
              key={item.key ?? "all"}
              href={item.key ? `/keterampilan?role_family=${item.key}` : "/keterampilan"}
              aria-current={item.key === selectedRole ? "page" : undefined}
              scroll={false}
              className={cx(
                "inline-flex h-10 items-center rounded-md border px-3 text-sm",
                item.key === selectedRole ? "border-teal bg-teal text-white" : "border-line bg-card text-ink-2 hover:border-line-strong",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        {stats.top_tags.length ? (
          <BarList
            caption="Frekuensi tag yang terlihat pada kartu lowongan"
            items={stats.top_tags.map((tag) => ({
              key: tag.value,
              label: tag.label,
              count: tag.count,
              share: tag.count / stats.total_jobs,
              // Exact tag (and the selected field), so the search shows the listings counted here.
              href: `/lowongan?tag=${encodeURIComponent(tag.value)}${selectedRole ? `&role_family=${selectedRole}` : ""}`,
            }))}
          />
        ) : (
          <p className="text-sm text-ink-2">Tidak ada tag yang terlihat untuk bidang ini.</p>
        )}
        <CardFootnote>
          Persentase = banyaknya lowongan yang menampilkan tag itu dibagi {population} (termasuk yang tidak
          menampilkan tag apa pun). Karena tag terpotong, tag yang tidak muncul di sini belum tentu jarang diminta.
        </CardFootnote>
      </Card>

      <Card>
        <CardHeader title="Apa yang masih kurang" />
        <ol className="list-decimal space-y-2 pl-5 text-sm text-ink-2">
          <li>
            <strong className="text-ink">Deskripsi lowongan lengkap dari sumber yang mengizinkan.</strong> Halaman arsip web
            memang memuat deskripsi, tetapi hak atas teksnya milik situs asal, dan banyak situs memakai paragraf templat
            yang sama di semua lowongannya (mis. “mampu berkomunikasi dengan baik”), sehingga keterampilan tertentu
            terlihat jauh lebih sering daripada kenyataannya.
          </li>
          <li>
            <strong className="text-ink">Pemeriksaan ketepatan oleh manusia.</strong> Kami sudah punya kamus keterampilan
            dalam bahasa Indonesia dan Inggris, tetapi ketepatannya belum diperiksa ulang oleh peninjau manusia.
          </li>
        </ol>
        <p className="mt-3 text-sm text-ink-3">
          Sampai keduanya terpenuhi, TalentScope tidak menampilkan peringkat keterampilan.{" "}
          <Link href="/metodologi#keterampilan" className="font-medium text-teal-text underline">
            Selengkapnya
          </Link>
        </p>
      </Card>
    </div>
  );
}
