"""Which websites inside Common Crawl may contribute records.

Common Crawl's terms let us use the archive, but crawled content remains subject to the
site owner's own terms. We therefore apply the same per-site decisions as for direct
collection: any site whose terms prohibit automated extraction or aggregation, or whose
terms we could not verify, is excluded even when its pages are in the archive.
Everything else is used for research analytics only, under the conditions in
docs/DATA_POLICY.md. Site owners can opt out by being added here.
"""

from __future__ import annotations

import re

# Registered domains of sources researched in docs/RESEARCH_SOURCES.md whose status is
# BLOCKED, REQUIRES_WRITTEN_PERMISSION, or NEEDS_REVIEW, plus large commercial job portals
# found in the archive whose terms have not been reviewed. Matching is on the registered
# domain, so subdomains are excluded too.
EXCLUDED_DOMAINS = frozenset(
    {
        # BLOCKED
        "glints.com",
        "glints.id",
        "jobstreet.co.id",
        "jobstreet.com",
        "linkedin.com",
        "indeed.com",
        "kitalulus.com",
        "karir.com",
        # REQUIRES_WRITTEN_PERMISSION
        # Karirhub (karirhub.kemnaker.go.id) and the Pasker ID datasets need written
        # permission; Pasker ID's job pages (paskerid.kemnaker.go.id) are BLOCKED. The
        # registered domain covers both, so it is excluded under the stricter status.
        "kemnaker.go.id",
        "kalibrr.id",
        "kalibrr.com",
        "pintarnya.com",
        "pintarnya.id",
        # NEEDS_REVIEW
        "dealls.com",
        "loker.id",
        "topkarir.com",
        "hiredtoday.com",
        "techinasia.com",
        "bkn.go.id",
        # Commercial portals present in Common Crawl; terms not reviewed (2026-10-17)
        "foundit.id",
        "jobsdb.com",
        "profesea.id",
        "jobs.id",
    }
)

# Hosts whose name suggests a vacancy site or blog (as opposed to an employer's own
# website). Used only to report source mix and bias; it does not affect eligibility.
_JOB_SITE_HINT = re.compile(r"loker|lowongan|karir|career|kerja|jobs?|vacanc|rekrut|recruit|bursa")


def is_excluded(registered_domain: str | None) -> bool:
    return registered_domain is None or registered_domain.lower() in EXCLUDED_DOMAINS


def site_type(registered_domain: str | None) -> str:
    """'job_site' for vacancy portals/blogs by name, 'other' for employers and the rest."""
    if not registered_domain:
        return "other"
    name = registered_domain.split(".")[0]
    return "job_site" if _JOB_SITE_HINT.search(name) else "other"
