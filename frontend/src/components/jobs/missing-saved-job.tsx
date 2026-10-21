"use client";

import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { BookmarkX } from "lucide-react";

import { Button } from "@/components/ui";
import { removeSavedJob, useSavedJobs } from "@/lib/saved-jobs";

const JOB_PATH = /^\/lowongan\/([^/]+)\/?$/;

function subscribe(listener: () => void): () => void {
  window.addEventListener("popstate", listener);
  return () => window.removeEventListener("popstate", listener);
}

/**
 * The address bar, not the router: the proxy answers an unknown job with the prerendered
 * not-found page, so the router's pathname is that page while the browser still shows
 * /lowongan/<id>.
 */
function useMissingJobId(): string | null {
  const pathname = useSyncExternalStore(subscribe, () => window.location.pathname, () => "");
  const id = JOB_PATH.exec(pathname)?.[1];
  return id && id !== "tidak-ditemukan" ? decodeURIComponent(id) : null;
}

/**
 * Shown on the "job not found" page. When the missing job is in this browser's saved list,
 * say so and offer to remove it, so a saved link that went stale is not a dead end.
 */
export function MissingSavedJobNotice() {
  const id = useMissingJobId();
  const saved = useSavedJobs().find((job) => job.id === id);
  const [removedTitle, setRemovedTitle] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  if (removedTitle) {
    return (
      <p role="status" className="mt-6 rounded-md border border-line bg-sunken p-4 text-sm text-ink-2">
        “{removedTitle}” sudah dihapus dari daftar tersimpan.{" "}
        <Link href="/tersimpan" className="font-medium text-teal-text underline">
          Lihat lowongan tersimpan
        </Link>
      </p>
    );
  }
  if (!saved) return null;

  return (
    <div className="mt-6 w-full rounded-md border border-warn-line bg-warn-wash p-4 text-left text-sm text-ink-2">
      <p className="flex items-start gap-2 font-semibold text-ink">
        <BookmarkX aria-hidden className="mt-0.5 size-4 shrink-0 text-warn" />
        Lowongan ini ada di daftar tersimpanmu
      </p>
      <p className="mt-1">
        “{saved.title}”{saved.company ? ` dari ${saved.company}` : ""} sudah tidak ada di TalentScope, jadi rinciannya tidak
        dapat ditampilkan lagi. Kamu bisa menghapusnya dari daftar tersimpan.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          className="h-9"
          onClick={() => {
            if (removeSavedJob(saved.id)) setRemovedTitle(saved.title);
            else setFailed(true);
          }}
        >
          Hapus dari tersimpan
        </Button>
        <Link href="/tersimpan" className="font-medium text-teal-text underline">
          Kembali ke lowongan tersimpan
        </Link>
      </div>
      {failed ? (
        <p role="status" className="mt-2 text-xs text-danger">
          Browser menolak menyimpan perubahan.
        </p>
      ) : null}
    </div>
  );
}
