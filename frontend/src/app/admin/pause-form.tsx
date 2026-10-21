"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui";

import { type PauseState, setSourcePaused } from "./actions";

export function PauseForm({ sourceId, paused, canResume }: { sourceId: string; paused: boolean; canResume: boolean }) {
  const [state, action, pending] = useActionState<PauseState, FormData>(setSourcePaused, {});
  const nextPaused = !paused;

  if (!nextPaused && !canResume) {
    return <p className="text-xs text-ink-3">Tidak dapat dilanjutkan: status kelayakan belum disetujui.</p>;
  }
  return (
    <form action={action} className="flex flex-col gap-1.5">
      <input type="hidden" name="sourceId" value={sourceId} />
      <input type="hidden" name="paused" value={String(nextPaused)} />
      <div className="flex gap-2">
        <label className="sr-only" htmlFor={`reason-${sourceId}`}>Alasan</label>
        <input
          id={`reason-${sourceId}`}
          name="reason"
          required
          minLength={3}
          placeholder="Alasan (dicatat di audit)"
          className="h-9 min-w-0 flex-1 rounded-md border border-line px-2 text-sm focus:border-teal focus:outline-none"
        />
        <Button type="submit" variant="secondary" className="h-9 px-3" disabled={pending}>
          {nextPaused ? "Jeda" : "Lanjutkan"}
        </Button>
      </div>
      {state.error ? <p role="alert" className="text-xs text-danger">{state.error}</p> : null}
      {state.ok ? <p role="status" className="text-xs text-teal-text">{state.ok}</p> : null}
    </form>
  );
}
