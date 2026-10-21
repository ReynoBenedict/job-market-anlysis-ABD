"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui";

/** Fallback for unexpected rendering errors; expected API failures are handled inline. */
export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="card mx-auto mt-10 max-w-lg p-8 text-center">
      <AlertTriangle aria-hidden className="mx-auto size-8 text-danger" />
      <h1 className="mt-3 text-xl font-semibold text-ink">Terjadi kesalahan tak terduga</h1>
      <p className="mt-2 text-sm text-ink-2">
        Halaman ini gagal dimuat. Coba lagi; jika masalah berlanjut, laporkan kode berikut.
      </p>
      {error.digest ? <p className="mt-2 font-mono text-xs text-ink-3">Kode: {error.digest}</p> : null}
      <Button className="mt-5" onClick={reset}>
        Coba lagi
      </Button>
    </div>
  );
}
