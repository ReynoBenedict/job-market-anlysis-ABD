import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded-md">
      <span aria-hidden className="flex size-8 items-center justify-center rounded-md bg-navy font-display text-sm font-bold text-white">
        TS
      </span>
      <span className="font-display text-lg font-semibold tracking-tight text-ink">
        TalentScope<span className="sr-only"> — Beranda</span>
      </span>
    </Link>
  );
}
