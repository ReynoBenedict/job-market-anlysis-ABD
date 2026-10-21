"use client";

import { useState } from "react";
import { Bookmark, BookmarkCheck } from "lucide-react";

import { cx } from "@/components/ui";
import { type SavedJob, toggleSavedJob, useSavedJobs } from "@/lib/saved-jobs";

export function SaveJobButton({ job, withLabel = false }: { job: Omit<SavedJob, "savedAt">; withLabel?: boolean }) {
  const saved = useSavedJobs().some((item) => item.id === job.id);
  const [failed, setFailed] = useState(false);
  const label = saved ? "Hapus dari tersimpan" : "Simpan lowongan";

  return (
    <div className="flex flex-col items-end">
      <button
        type="button"
        aria-pressed={saved}
        aria-label={withLabel ? undefined : `${label}: ${job.title}`}
        title={label}
        onClick={() => setFailed(!toggleSavedJob(job))}
        className={cx(
          "inline-flex items-center gap-2 rounded-md border text-sm font-medium transition-colors",
          withLabel ? "h-10 px-4" : "size-9 justify-center",
          saved
            ? "border-teal-line bg-teal-wash text-teal-text"
            : "border-line bg-card text-ink-2 hover:border-line-strong hover:text-ink",
        )}
      >
        {saved ? <BookmarkCheck aria-hidden className="size-4" /> : <Bookmark aria-hidden className="size-4" />}
        {withLabel ? (saved ? "Tersimpan" : "Simpan") : null}
      </button>
      {failed ? (
        <span role="status" className="mt-1 text-xs text-danger">
          Browser menolak menyimpan data.
        </span>
      ) : null}
    </div>
  );
}
