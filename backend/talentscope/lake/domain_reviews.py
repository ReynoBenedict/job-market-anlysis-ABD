"""Per-site review of the domains that contribute archived job pages.

The Common Crawl licence covers the archive, not the sites' content, so every site whose
pages we use is reviewed individually (terms, disclaimer, robots.txt, provenance). Only
reviewed sites with a usable status reach silver; an archived page from any other site
is kept in bronze but excluded until someone reviews that site. Evidence and quotes:
docs/data-engineering/DOMAIN_REVIEW.md (review of 2026-10-18).

This is a default-deny allow-list. Large portals that prohibit collection are listed
separately in domains.EXCLUDED_DOMAINS so they are not even fetched.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReviewStatus(str, Enum):
    # Terms read; they neither permit nor prohibit reuse. Used for non-commercial research
    # with attribution, a link to the original page, minimal fields, and opt-out on request.
    NO_STATEMENT = "no_statement"
    # Terms allow reuse under a condition we meet (e.g. a link back to the page).
    PERMITS_WITH_CONDITIONS = "permits_with_conditions"
    # Terms prohibit copying or republishing: excluded.
    PROHIBITS = "prohibits"
    # Terms could not be read (DNS/TLS failure, hijacked domain): excluded until verified.
    UNREADABLE = "unreadable"
    # Excluded on quality or provenance grounds (scam patterns, admitted copying of
    # content from a source that prohibits it).
    EXCLUDED_QUALITY = "excluded_quality"


USABLE = frozenset({ReviewStatus.NO_STATEMENT, ReviewStatus.PERMITS_WITH_CONDITIONS})


@dataclass(frozen=True)
class DomainReview:
    status: ReviewStatus
    # The site says it collects vacancies from other sources: its records are second-hand.
    aggregator: bool = False
    note: str = ""


REVIEWED_AT = "2026-10-18"

_NO, _PERMIT, _PROHIBIT, _UNREAD, _QUALITY = (
    ReviewStatus.NO_STATEMENT,
    ReviewStatus.PERMITS_WITH_CONDITIONS,
    ReviewStatus.PROHIBITS,
    ReviewStatus.UNREADABLE,
    ReviewStatus.EXCLUDED_QUALITY,
)

DOMAIN_REVIEWS: dict[str, DomainReview] = {
    # One shared template and operator; employers and third parties post vacancies.
    "lokeraceh.id": DomainReview(
        _NO, note="terms silent on reuse; same operator as lokerbekasi.id"
    ),
    "lokerbekasi.id": DomainReview(_NO, note="terms silent on reuse"),
    "lowongankerjacirebon.id": DomainReview(_NO, note="terms silent on reuse"),
    "lokerbogor.co.id": DomainReview(_NO, note="terms silent on reuse"),
    "gaji.co.id": DomainReview(
        _NO, aggregator=True, note="no terms page; listings appear rewritten from other texts"
    ),
    "aksesinfo.my.id": DomainReview(_NO, note="privacy policy only, no terms"),
    "lokerbekasi.my.id": DomainReview(
        _NO, aggregator=True, note="'dikumpulkan dari beberapa sumber publik'"
    ),
    "mediaanalisindonesia.co.id": DomainReview(_NO, note="privacy policy only, no terms"),
    "bisakerja.id": DomainReview(_NO, note="disclaimer only; content claimed as own writing"),
    "lokerbandung.or.id": DomainReview(_NO, note="no terms ('Belum diatur')"),
    "sportsmatters.id": DomainReview(_NO, aggregator=True, note="'berasal dari berbagai sumber'"),
    "inaba.ac.id": DomainReview(_NO, note="university career centre; no terms found"),
    "jogjaterkini.id": DomainReview(_NO, note="news portal; partly checked"),
    "lokersamarinda.biz.id": DomainReview(_NO, aggregator=True, note="'berbagai sumber' template"),
    "kusnendar.web.id": DomainReview(
        _PERMIT, aggregator=True, note="copying allowed only with a backlink; we link back"
    ),
    "bursaloker.id": DomainReview(_NO, note="no terms found"),
    "lokerjakarta.id": DomainReview(
        _NO, note="employer self-posting; terms silent on visitor reuse"
    ),
    "openkerja.id": DomainReview(_NO, aggregator=True, note="'portal agregator'"),
    "sokacoke.id": DomainReview(
        _NO, aggregator=True, note="'berbagai sumber' template; partly checked"
    ),
    "lokerjogja.id": DomainReview(_NO, note="employers post directly; partly checked"),
    "promag.id": DomainReview(_NO, aggregator=True, note="'dari berbagai sumber'"),
    "pixelninja.id": DomainReview(_NO, note="no terms ('Belum diatur')"),
    "pekerjamigran.id": DomainReview(
        _NO, note="overseas placements (rejected as outside Indonesia); source SISKOP2MI"
    ),
    # Excluded.
    "groove.co.id": DomainReview(
        _PROHIBIT, note="'tidak diperbolehkan untuk menyalin ... tanpa izin tertulis'"
    ),
    "bukaloker.web.id": DomainReview(
        _QUALITY,
        aggregator=True,
        note="admits using copyrighted material without permission; Indeed-derived",
    ),
    "generalist.biz.id": DomainReview(
        _QUALITY, note="scam-pattern listings, injected gambling spam"
    ),
    "aloka.id": DomainReview(_UNREAD, note="redirects to an unrelated domain (likely hijacked)"),
    "tempatbelajar.my.id": DomainReview(_UNREAD, note="DNS failure on 2026-10-18"),
    "infobumn.web.id": DomainReview(_UNREAD, note="connection refused on 2026-10-18"),
    "lorong.my.id": DomainReview(_UNREAD, note="TLS error on 2026-10-18"),
    "pressrelease.co.id": DomainReview(_UNREAD, note="DNS failure on 2026-10-18"),
    "jac-recruitment.co.id": DomainReview(
        _UNREAD, note="terms page truncated; robots.txt disallows deep job paths"
    ),
}


def review_of(domain: str | None) -> DomainReview | None:
    return DOMAIN_REVIEWS.get((domain or "").lower())


def usable_domains() -> list[str]:
    return sorted(domain for domain, review in DOMAIN_REVIEWS.items() if review.status in USABLE)


def aggregator_domains() -> list[str]:
    return sorted(domain for domain, review in DOMAIN_REVIEWS.items() if review.aggregator)
