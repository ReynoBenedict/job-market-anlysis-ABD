"use client";

import Link from "next/link";
import { useState } from "react";
import { MapPin, Trash2 } from "lucide-react";

import { Button, EmptyState, LinkButton } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { clearSavedJobs, removeSavedJob, useSavedJobs, useSavedJobsAvailable } from "@/lib/saved-jobs";

export function SavedJobsList() {
  const jobs = useSavedJobs();
  const available = useSavedJobsAvailable();
  const [confirming, setConfirming] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!available) {
    return (
      <EmptyState
        title="Browser ini tidak mengizinkan penyimpanan"
        description="Lowongan tersimpan memakai penyimpanan situs di browser. Penyimpanan itu sedang diblokir (misalnya mode privat atau data situs dinonaktifkan), jadi daftar tidak dapat dibaca atau diubah. Izinkan data situs untuk TalentScope lalu muat ulang halaman."
        action={<LinkButton href="/lowongan">Cari Lowongan</LinkButton>}
      />
    );
  }

  if (!jobs.length) {
    return (
      <EmptyState
        title="Belum ada lowongan tersimpan"
        description="Tekan ikon penanda pada lowongan untuk menyimpannya di sini. Daftar ini hanya tersimpan di browser ini."
        action={<LinkButton href="/lowongan">Cari Lowongan</LinkButton>}
      />
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-2" aria-live="polite">
          {jobs.length} lowongan tersimpan
        </p>
        {confirming ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-ink-2">Hapus semua?</span>
            <Button variant="secondary" className="h-9" onClick={() => { setFailed(!clearSavedJobs()); setConfirming(false); }}>
              Ya, hapus
            </Button>
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              Batal
            </Button>
          </div>
        ) : (
          <Button variant="ghost" onClick={() => setConfirming(true)}>
            <Trash2 aria-hidden className="size-4" /> Hapus semua
          </Button>
        )}
      </div>
      {failed ? (
        <p role="status" className="mb-3 text-sm text-danger">
          Browser menolak menyimpan perubahan.
        </p>
      ) : null}
      <p className="mb-3 text-xs text-ink-3">
        Rincian di bawah adalah salinan saat disimpan; buka lowongan untuk melihat data terbaru.
      </p>
      <ul className="space-y-3">
        {jobs.map((job) => (
          <li key={job.id} className="card flex items-start justify-between gap-4 p-4">
            <div className="min-w-0">
              <Link href={`/lowongan/${job.id}`} className="font-semibold text-ink hover:text-teal-text hover:underline">
                {job.title}
              </Link>
              <p className="text-sm text-ink-2">{job.company ?? "Perusahaan tidak dicantumkan"}</p>
              <p className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-ink-3">
                {job.location ? (
                  <span className="flex items-center gap-1">
                    <MapPin aria-hidden className="size-3.5" /> {job.location}
                  </span>
                ) : null}
                <span>Disimpan {formatDateTime(job.savedAt)}</span>
                {job.status ? <span>Status saat disimpan: {job.status}</span> : null}
              </p>
            </div>
            <Button
              variant="ghost"
              aria-label={`Hapus ${job.title} dari tersimpan`}
              onClick={() => setFailed(!removeSavedJob(job.id))}
            >
              <Trash2 aria-hidden className="size-4" />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
