import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { Card, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Cara Kami Menghitung" };

const SECTIONS = [
  ["sumber", "Dari mana datanya?"],
  ["status", "Apakah lowongan masih dibuka?"],
  ["duplikat", "Bagaimana lowongan dihitung?"],
  ["gaji", "Bagaimana gaji dihitung?"],
  ["bidang", "Bagaimana bidang ditentukan?"],
  ["keterampilan", "Mengapa belum ada peringkat keterampilan?"],
  ["teknis", "Untuk pembaca teknis"],
  ["koreksi", "Koreksi & penghapusan"],
] as const;

function Section({ id, title, summary, children }: { id: string; title: string; summary: ReactNode; children?: ReactNode }) {
  return (
    <Card id={id}>
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      <div className="mt-2 text-[15px] leading-relaxed text-ink-2 [&_strong]:text-ink">{summary}</div>
      {children ? (
        <details className="mt-3 text-sm leading-relaxed text-ink-2">
          <summary className="cursor-pointer font-medium text-teal-text">Rincian</summary>
          <div className="mt-2 space-y-2 [&_li]:ml-5 [&_li]:list-disc [&_strong]:text-ink">{children}</div>
        </details>
      ) : null}
    </Card>
  );
}

export default function MethodologyPage() {
  return (
    <>
      <PageHeader
        title="Cara Kami Menghitung"
        description="Penjelasan singkat tentang asal data, arti status lowongan, dan cara angka-angka di TalentScope dihitung. Buka “Rincian” bila ingin tahu lebih jauh."
      />
      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <nav aria-label="Daftar isi" className="min-w-0 lg:sticky lg:top-24 lg:self-start">
          <ol className="flex gap-2 overflow-x-auto pb-2 text-sm lg:block lg:space-y-1 lg:overflow-visible lg:pb-0">
            {SECTIONS.map(([id, label]) => (
              <li key={id} className="shrink-0">
                {/* Small screens: a horizontally scrolling row of bordered chips, so a cut-off chip reads as "more". */}
                <a
                  href={`#${id}`}
                  className="block whitespace-nowrap rounded-md border border-line bg-card px-3 py-2 text-ink-2 hover:bg-sunken hover:text-ink lg:whitespace-normal lg:border-transparent lg:bg-transparent"
                >
                  {label}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0 space-y-6">
          <Section
            id="sumber"
            title="Dari mana datanya?"
            summary={
              <p>
                Dari dua kumpulan data: <strong>arsip web Common Crawl</strong> (halaman lowongan berdomain .id,
                kebanyakan dari situs info lowongan daerah, sebagian menayangkan ulang lowongan dari situs lain) dan{" "}
                <strong>satu snapshot Glints</strong> yang dikumpulkan sekali pada Juni 2026 untuk proyek akademik. Dari
                arsip web kami hanya memakai situs yang sudah kami tinjau satu per satu dan ketentuannya tidak melarang;
                tidak ada situs yang memberi izin khusus. Situs yang melarang, belum ditinjau, atau ketentuannya tidak bisa
                dibuka tidak kami pakai. Daftar lengkapnya ada di halaman{" "}
                <Link href="/sumber-data" className="font-medium text-teal-text underline">
                  Sumber Data
                </Link>
                .
              </p>
            }
          >
            <ul>
              <li>
                Dari arsip web kami hanya memakai data terstruktur lowongan (judul, perusahaan, lokasi, gaji, tanggal),
                bukan halaman HTML-nya. Deskripsi hanya disimpan di penyimpanan lokal dan tidak ditampilkan, karena hak
                atas teksnya milik situs asal.
              </li>
              <li>
                Snapshot Glints berasal dari pencarian 44 kata kunci (kebanyakan teknologi, data, dan bisnis), sehingga
                bidang-bidang itu lebih banyak muncul daripada di pasar kerja sebenarnya.
              </li>
              <li>
                Portal besar (mis. JobStreet, LinkedIn, dan situs Glints saat ini) tidak kami ambil datanya karena
                ketentuannya melarang. Snapshot Glints yang ada dikumpulkan sebelumnya oleh proyek akademik, dan hak
                menampilkan ulangnya belum dipastikan.
              </li>
              <li>Karena itu angka-angka di TalentScope adalah gambaran dari lowongan yang tercatat, bukan sensus pasar kerja.</li>
            </ul>
          </Section>

          <Section
            id="status"
            title="Apakah lowongan masih dibuka?"
            summary={
              <p>
                <strong>Belum tentu.</strong> TalentScope belum memeriksa ulang lowongan ke situs asalnya, jadi tidak ada
                lowongan yang kami nyatakan “masih dibuka”. Setiap lowongan diberi salah satu status berikut, dan kamu selalu
                perlu memastikannya di situs asal sebelum melamar.
              </p>
            }
          >
            <dl className="space-y-2">
              <div>
                <dt className="font-semibold text-ink">Kedaluwarsa menurut sumber</dt>
                <dd>
                  Situs asal mencantumkan batas lamaran yang sudah lewat. Batas lamaran berlaku sampai akhir hari itu (WIB).
                  Situs yang mengisi batas lamaran secara otomatis (tanggal atau selang hari yang sama pada sebagian besar
                  lowongannya) tidak dipakai sebagai batas lamaran.
                </dd>
              </div>
              <div>
                <dt className="font-semibold text-ink">Riwayat lowongan</dt>
                <dd>Tercatat pada pengamatan lama; statusnya sekarang tidak diketahui.</dd>
              </div>
              <div>
                <dt className="font-semibold text-ink">Baru terlihat, belum diverifikasi</dt>
                <dd>Diarsipkan atau dikumpulkan dalam 30 hari terakhir, tetapi belum diperiksa masih dibuka atau tidak.</dd>
              </div>
            </dl>
            <p>
              Setiap lowongan menampilkan tanggal tayang (dari situs asal), batas lamaran bila ada, dan kapan halaman itu
              diarsipkan atau dikumpulkan. Tanggal tayang di snapshot Glints hanya berupa “3 hari lalu”, jadi tanggalnya
              perkiraan dan ditandai “±”.
            </p>
          </Section>

          <Section
            id="duplikat"
            title="Bagaimana lowongan dihitung?"
            summary={
              <p>
                <strong>Satu lowongan dihitung sekali</strong>, walaupun muncul di beberapa situs atau beberapa kali
                diarsipkan. Halaman yang bukan lowongan sungguhan, atau tidak menyebut perusahaannya, tidak dihitung.
              </p>
            }
          >
            <ul>
              <li>
                Lowongan dianggap sama bila perusahaan, posisi, dan lokasinya sama dan tanggal tayangnya berdekatan (jarak
                antar-iklan paling jauh 45 hari). Lowongan yang sama yang diiklankan lagi setelah jeda lebih dari 45 hari
                dihitung sebagai lowongan baru. Halaman yang sama yang diarsipkan berkali-kali hanya menambah catatan
                pengamatan, bukan lowongan.
              </li>
              <li>
                Beberapa situs membuat ratusan halaman serupa untuk setiap kecamatan atau kota (mis. “Lowongan Indomaret di
                …”) dengan gaji yang sama di semua halaman. Seluruh halaman itu dihitung sebagai satu lowongan tanpa lokasi
                pasti, berapa pun rentang tanggalnya, karena tanggal halaman semacam itu hanya menunjukkan kapan situs
                membuatnya. Bila gajinya berbeda per kota, setiap kota dihitung sebagai lowongan tersendiri.
              </li>
              <li>
                Halaman dengan nama perusahaan yang hanya pengisi (mis. “Perusahaan” atau nama situsnya sendiri) tidak
                dihitung, karena tidak jelas siapa yang membuka lowongan. Lowongan dengan perusahaan yang dirahasiakan atau
                dari perorangan (mis. asisten rumah tangga) tetap dihitung dan ditandai.
              </li>
              <li>Lowongan yang lokasinya di luar Indonesia tidak dihitung.</li>
            </ul>
          </Section>

          <Section
            id="gaji"
            title="Bagaimana gaji dihitung?"
            summary={
              <p>
                Hanya gaji yang <strong>benar-benar dicantumkan</strong> yang dihitung; lowongan tanpa gaji tidak dianggap
                nol. Bila lowongan mencantumkan rentang, kami memakai titik tengahnya. Kelompok dengan kurang dari 5 gaji
                tidak diberi angka.
              </p>
            }
          >
            <ul>
              <li>
                Beberapa situs menampilkan angka gaji yang sama persis di hampir semua lowongannya. Angka seperti itu adalah
                templat situs, bukan gaji lowongan, jadi tidak kami pakai.
              </li>
              <li>Gaji tahunan dibagi 12. Gaji per jam, per hari, atau per minggu tidak diubah menjadi bulanan.</li>
              <li>
                Snapshot Glints tidak menuliskan periode gaji; kami anggap per bulan karena begitulah Glints menampilkan gaji,
                dan anggapan ini ditandai.
              </li>
              <li>
                Gaji di bawah Rp500 ribu per bulan tidak dipakai untuk statistik. Gaji yang sangat tinggi (di atas Rp100 juta)
                atau rentang yang sangat lebar ditandai sebagai catatan kualitas.
              </li>
              <li>Kelompok dengan kurang dari 20 gaji ditandai “sampel kecil”.</li>
              <li>Gaji di iklan lowongan belum tentu sama dengan gaji yang akhirnya ditawarkan atau diterima.</li>
            </ul>
          </Section>

          <Section
            id="bidang"
            title="Bagaimana bidang ditentukan?"
            summary={
              <p>
                Dari kata-kata di judul lowongan, dengan aturan yang bisa diperiksa (mis. “Barista” → Makanan, Minuman &
                Perhotelan; “Admin Gudang” → Rantai Pasok). Judul yang tidak cocok dengan aturan mana pun masuk “Lainnya”.
              </p>
            }
          >
            <p>
              Ini alat bantu pengelompokan, bukan klasifikasi jabatan resmi seperti KBJI. Sebagian judul bisa masuk bidang
              yang kurang tepat, terutama judul yang umum atau bercampur nama tempat.
            </p>
          </Section>

          <Section
            id="keterampilan"
            title="Mengapa belum ada peringkat keterampilan?"
            summary={
              <p>
                Untuk itu dibutuhkan deskripsi lowongan lengkap dari sumber yang mengizinkan, dan pemeriksaan ketepatan oleh
                manusia. Keduanya belum terpenuhi, jadi halaman{" "}
                <Link href="/keterampilan" className="font-medium text-teal-text underline">
                  Keterampilan
                </Link>{" "}
                hanya menampilkan tag yang terlihat di snapshot Glints.
              </p>
            }
          />

          <Section
            id="teknis"
            title="Untuk pembaca teknis"
            summary={
              <p>
                Pengolahan data, pengujian, dan keputusan teknis didokumentasikan di repositori proyek (folder{" "}
                <code className="font-mono text-sm">docs/</code>), termasuk evaluasi eksperimen pengelompokan K-Means dari
                proyek akademik awal.
              </p>
            }
          >
            <p id="k-means">
              <strong>Mengapa K-Means tidak dipakai:</strong> proyek awal mengelompokkan judul dengan TF-IDF dan K-Means (k =
              3) di Spark MLlib, dengan Silhouette Score 0,0351. Satu klaster ternyata terbentuk dari judul yang tanda bacanya
              menjadi spasi ganda (artefak pra-pemrosesan), dan hasilnya berubah besar dengan <em>seed</em> acak yang berbeda.
              Klaster yang tidak stabil tidak layak ditampilkan, sehingga TalentScope memakai aturan bidang yang dapat diuji
              (docs/ML_EVALUATION.md).
            </p>
            <p>
              <strong>Pengolahan arsip web:</strong> halaman diambil dari indeks Common Crawl dengan laju terbatas, disimpan
              sebagai Parquet (bronze → silver → gold), divalidasi, lalu digabung menjadi lowongan unik dengan DuckDB
              (docs/LAKE.md, docs/DATA_INVENTORY.md).
            </p>
          </Section>

          <Card id="koreksi">
            <h2 className="text-xl font-semibold text-ink">Koreksi & penghapusan</h2>
            <div className="mt-2 space-y-2 text-[15px] leading-relaxed text-ink-2">
              <p>
                Pemilik situs, pemberi kerja, atau siapa pun yang menemukan data keliru dapat meminta koreksi atau
                penghapusan lewat halaman <em>issues</em> repositori proyek. Sertakan tautan lowongan di TalentScope dan
                alasannya. Bila pemilik situs meminta datanya tidak dipakai, situs itu kami keluarkan dari pengumpulan dan
                lowongannya kami hapus.
              </p>
              <p>
                TalentScope tidak menerima lamaran kerja dan tidak menyimpan data pribadi pencari kerja. Lowongan yang kamu
                simpan hanya ada di browser ini.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
