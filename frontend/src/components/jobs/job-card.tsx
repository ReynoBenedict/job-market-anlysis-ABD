import Link from "next/link";
import { Briefcase, Clock, GraduationCap, MapPin } from "lucide-react";

import type { JobSummary } from "@/lib/api";
import { formatDateShort } from "@/lib/format";
import { sourceHost } from "@/lib/status";

import { isImplausibleSalary, salaryRangeText } from "./salary";
import { SaveJobButton } from "./save-job-button";
import { StatusBadge } from "./status-badge";

export function locationText(job: Pick<JobSummary, "location">): string | null {
  const { city, province, text } = job.location;
  if (city && province) return `${city}, ${province}`;
  return city ?? province ?? text;
}

/**
 * When the listing was posted. Archived pages state a date; the snapshot only states an
 * age ("3 hari lalu") relative to when it was collected, so that date is approximate.
 */
export function postedText(job: Pick<JobSummary, "published_at" | "posted_age_days" | "last_seen_at">): string | null {
  if (job.published_at) return `Tayang ${formatDateShort(job.published_at)}`;
  if (job.posted_age_days === null) return null;
  const posted = new Date(job.last_seen_at);
  posted.setDate(posted.getDate() - job.posted_age_days);
  return `Tayang ± ${formatDateShort(posted.toISOString())}`;
}

/** One short salary line; the detail page explains why a salary is missing. */
export function salaryLine(salary: JobSummary["salary"]): { text: string; disclosed: boolean } {
  const range = salaryRangeText(salary);
  if (range) {
    const period = salary.period.code === "MONTH" ? "/bulan" : ` ${salary.period.label}`;
    return { text: `${range}${period}${salary.period_assumed ? "*" : ""}`, disclosed: true };
  }
  if (isImplausibleSalary(salary)) return { text: "Angka gaji di sumber tidak wajar", disclosed: false };
  return { text: salary.status.code === "NOT_DISCLOSED" ? "Gaji tidak dicantumkan" : "Gaji tidak tersedia", disclosed: false };
}

/** `returnQuery` is the results page's query string, so the detail page can link back to it. */
export function JobCard({ job, returnQuery }: { job: JobSummary; returnQuery?: string }) {
  const location = locationText(job);
  const posted = postedText(job);
  const salary = salaryLine(job.salary);
  const site = sourceHost(job.source_url);
  const facts = [
    location ? { icon: MapPin, text: location } : null,
    job.employment_type.code !== "UNKNOWN" ? { icon: Briefcase, text: job.employment_type.label } : null,
    job.experience.band.code !== "UNKNOWN" ? { icon: Clock, text: `Pengalaman ${job.experience.band.label}` } : null,
    job.education.code !== "UNKNOWN" ? { icon: GraduationCap, text: `Min. ${job.education.label}` } : null,
  ].filter((fact) => fact !== null);

  return (
    <article className="card relative p-4 transition-shadow focus-within:border-teal/45 hover:border-teal/45 hover:shadow-[var(--shadow-raised)] md:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold leading-snug text-ink [overflow-wrap:anywhere] md:text-lg">
            <Link
              href={returnQuery ? `/lowongan/${job.id}?kembali=${encodeURIComponent(returnQuery)}` : `/lowongan/${job.id}`}
              className="hover:text-teal-text hover:underline"
            >
              {job.title}
            </Link>
          </h3>
          <p className="mt-0.5 text-sm text-ink-2 [overflow-wrap:anywhere] md:text-[15px]">
            {job.company_name ?? "Perusahaan tidak dicantumkan"}
          </p>
        </div>
        <SaveJobButton job={{ id: job.id, title: job.title, company: job.company_name, location, status: job.freshness.label }} />
      </div>

      {facts.length ? (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-ink-2">
          {facts.map(({ icon: Icon, text }) => (
            <li key={text} className="flex min-w-0 items-center gap-1.5">
              <Icon aria-hidden className="size-4 shrink-0 text-ink-3" />
              <span className="[overflow-wrap:anywhere]">{text}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <p className={salary.disclosed ? "tabular mt-3 font-semibold text-teal-text" : "mt-3 text-sm text-ink-3"}>
        {salary.text}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-sunken pt-3 text-xs text-ink-3">
        <StatusBadge freshness={job.freshness} />
        {posted ? <span>{posted}</span> : null}
        <span className="min-w-0 [overflow-wrap:anywhere]">
          {job.source.method.label}
          {site ? ` · ${site}` : ` · ${job.source.name}`}
        </span>
      </div>
    </article>
  );
}
