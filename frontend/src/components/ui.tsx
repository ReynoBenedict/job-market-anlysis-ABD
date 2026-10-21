import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

import { formatNumber } from "@/lib/format";

function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export { cx };

export function Card({ className, ...props }: ComponentProps<"section">) {
  // min-w-0: as a grid item, a card must be allowed to shrink below its content width
  // (wide tables scroll inside it instead of widening the page).
  return <section className={cx("card min-w-0 p-5 md:p-6", className)} {...props} />;
}

export function CardHeader({
  title,
  description,
  action,
  as: Heading = "h2",
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  as?: "h2" | "h3";
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <Heading className="text-lg font-semibold leading-snug text-ink">{title}</Heading>
        {description ? <p className="mt-1 text-sm text-ink-3">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

/** Mandatory methodology footer for analytical cards (Stitch DESIGN.md, "Data Cards"). */
export function CardFootnote({ children }: { children: ReactNode }) {
  return <p className="mt-5 border-t border-line pt-3 text-xs leading-relaxed text-ink-3">{children}</p>;
}

type Tone = "neutral" | "teal" | "blue" | "warn" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-sunken text-ink-2 border-line",
  teal: "bg-teal-wash text-teal-text border-teal-line",
  blue: "bg-blue-wash text-blue border-blue-line",
  warn: "bg-warn-wash text-warn border-warn-line",
  danger: "bg-danger-wash text-danger border-danger-line",
};

export function Badge({
  tone = "neutral",
  pill = false,
  children,
  className,
  title,
}: {
  tone?: Tone;
  pill?: boolean;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={cx(
        "inline-flex items-center gap-1 border px-2 py-0.5 text-xs font-medium leading-5",
        pill ? "rounded-full" : "rounded-sm",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** "n = 1.133" sample-size label, always shown next to statistics. */
export function SampleSize({ n, label = "lowongan" }: { n: number; label?: string }) {
  return (
    <Badge className="tabular font-mono">
      n = {formatNumber(n)} {label}
    </Badge>
  );
}

const buttonBase =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60";
const buttonVariants = {
  primary: "h-10 bg-teal text-white hover:bg-teal-hover",
  secondary: "h-10 border border-line bg-card text-ink hover:border-line-strong hover:bg-canvas",
  ghost: "h-9 text-ink-3 hover:bg-sunken hover:text-ink",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: keyof typeof buttonVariants }) {
  return <button className={cx(buttonBase, buttonVariants[variant], className)} {...props} />;
}

export function LinkButton({
  variant = "primary",
  className,
  ...props
}: ComponentProps<typeof Link> & { variant?: keyof typeof buttonVariants }) {
  return <Link className={cx(buttonBase, buttonVariants[variant], className)} {...props} />;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  aside,
}: {
  eyebrow?: ReactNode;
  title: string;
  description?: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl">
        {eyebrow ? <div className="mb-2">{eyebrow}</div> : null}
        <h1 className="text-2xl font-semibold text-ink md:text-[28px] md:leading-9">{title}</h1>
        {description ? <p className="mt-2 text-[15px] text-ink-2">{description}</p> : null}
      </div>
      {aside}
    </header>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-line-strong bg-card px-6 py-12 text-center">
      <Inbox aria-hidden className="mb-3 size-8 text-ink-4" />
      <p className="font-semibold text-ink">{title}</p>
      {description ? <p className="mt-1 max-w-md text-sm text-ink-3">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Data tidak dapat dimuat",
  message,
  retryHref,
}: {
  title?: string;
  message: string;
  retryHref?: string;
}) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-danger-line bg-danger-wash p-4 text-sm">
      <AlertTriangle aria-hidden className="mt-0.5 size-5 shrink-0 text-danger" />
      <div>
        <p className="font-semibold text-danger">{title}</p>
        <p className="mt-1 text-ink-2">{message}</p>
        {retryHref ? (
          <Link href={retryHref} className="mt-2 inline-flex items-center gap-1 font-medium text-teal-text underline">
            <RefreshCw aria-hidden className="size-3.5" /> Coba lagi
          </Link>
        ) : null}
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-md bg-sunken", className)} />;
}

export function CardSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cx("card space-y-3 p-6", className)} aria-busy="true" aria-label="Memuat data">
      <Skeleton className="h-5 w-1/3" />
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-4 w-full" />
      ))}
    </div>
  );
}

export function StatTile({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-3">{label}</p>
        {icon ? <span className="rounded-md bg-teal-wash p-2 text-teal-text">{icon}</span> : null}
      </div>
      <p className="mt-2 font-display text-3xl font-bold leading-tight text-ink">{value}</p>
      {note ? <p className="mt-auto pt-3 text-xs leading-relaxed text-ink-3">{note}</p> : null}
    </div>
  );
}
