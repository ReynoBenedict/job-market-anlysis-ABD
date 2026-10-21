"""Salary text parsing.

Design rules (SRS FR-DATA-006, FR-DATA-012, FR-SAL-001..010):

* A missing or hidden salary is a status, never the number zero.
* Currency and pay period are kept with the amounts. A period that the text does not
  state can only be filled from a documented source convention, and the result is
  marked ``period_assumed`` so analytics and the UI can say so.
* Monthly equivalents are derived only from monthly or yearly figures. Hourly, daily,
  and weekly pay would need an assumed working schedule, so they stay unconverted.
* Implausible values are flagged, not dropped; whether to exclude them is an
  analytics decision that must be disclosed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from talentscope.normalization.text import clean_text
from talentscope.vocab import SalaryPeriod, SalaryStatus

FLAG_SINGLE_VALUE = "SALARY_SINGLE_VALUE"
FLAG_WIDE_RANGE = "SALARY_WIDE_RANGE"
FLAG_HIGH_OUTLIER = "SALARY_HIGH_OUTLIER"
FLAG_LOW_OUTLIER = "SALARY_LOW_OUTLIER"
FLAG_CURRENCY_ASSUMED = "SALARY_CURRENCY_ASSUMED"
FLAG_MIN_GREATER_THAN_MAX = "SALARY_MIN_GREATER_THAN_MAX"

# Plausibility thresholds for IDR monthly pay. They only raise review flags.
# 500 thousand is well below any provincial minimum wage, while internship stipends
# can legitimately sit between that and the minimum wage. 100 million per month is
# far above typical disclosed ranges and usually indicates a typo (e.g. "12–140 jt").
IDR_MONTHLY_LOW_OUTLIER = 500_000
IDR_MONTHLY_HIGH_OUTLIER = 100_000_000
# A maximum more than four times the minimum is too wide to describe one position.
WIDE_RANGE_RATIO = 4

_NOT_DISCLOSED_PHRASES = (
    "tidak ditampilkan",
    "tidak menampilkan gaji",
    "tidak dicantumkan",
    "di atas ekspektasi",
    "rahasia",
    "confidential",
    "undisclosed",
)
_NEGOTIABLE_PHRASES = ("nego", "negotiable", "dapat dinegosiasikan", "kompetitif", "competitive")

_CURRENCY_MARKERS = (
    ("IDR", re.compile(r"\b(?:rp|idr)\b|rp\.?(?=\s*\d)")),
    ("USD", re.compile(r"\busd\b|us\$|\$")),
    ("SGD", re.compile(r"\bsgd\b|s\$")),
)

_PERIOD_MARKERS = (
    (
        SalaryPeriod.YEAR,
        re.compile(
            r"/\s*(?:tahun|thn|th|year|yr)\b|per\s*(?:tahun|year|annum)|tahunan|annual|yearly|p\.a\."
        ),
    ),
    (
        SalaryPeriod.MONTH,
        re.compile(r"/\s*(?:bulan|bln|month|mo)\b|per\s*(?:bulan|month)|perbulan|bulanan|monthly"),
    ),
    (
        SalaryPeriod.WEEK,
        re.compile(r"/\s*(?:minggu|week|wk)\b|per\s*(?:minggu|week)|mingguan|weekly"),
    ),
    (SalaryPeriod.DAY, re.compile(r"/\s*(?:hari|day)\b|per\s*(?:hari|day)|harian|daily")),
    (SalaryPeriod.HOUR, re.compile(r"/\s*(?:jam|hour|hr)\b|per\s*(?:jam|hour)|hourly")),
)

_MAGNITUDES = {
    "jt": 1_000_000,
    "juta": 1_000_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "rb": 1_000,
    "ribu": 1_000,
    "k": 1_000,
}

# A number (digits with optional "." / "," groups) optionally followed by a magnitude.
_AMOUNT = re.compile(r"(\d+(?:[.,]\d+)*)\s*(juta|jt|ribu|rb|million|mn|k)?\b")


@dataclass(frozen=True)
class SalaryParse:
    status: SalaryStatus
    minimum: int | None = None
    maximum: int | None = None
    currency: str | None = None
    period: SalaryPeriod = SalaryPeriod.UNKNOWN
    period_assumed: bool = False
    flags: tuple[str, ...] = ()

    @property
    def monthly_minimum(self) -> int | None:
        return _to_monthly(self.minimum, self.period)

    @property
    def monthly_maximum(self) -> int | None:
        return _to_monthly(self.maximum, self.period)


def _to_monthly(amount: int | None, period: SalaryPeriod) -> int | None:
    if amount is None:
        return None
    if period is SalaryPeriod.MONTH:
        return amount
    if period is SalaryPeriod.YEAR:
        return round(amount / 12)
    return None


def _parse_number(token: str) -> float:
    """Parse a number written with Indonesian or English separators.

    The last separator is the decimal mark when both kinds appear. A single kind used
    once is a thousands separator only when exactly three digits follow it
    ("1.500" -> 1500, "6,8" -> 6.8); used repeatedly it is always a thousands separator.
    """
    has_dot, has_comma = "." in token, "," in token
    if has_dot and has_comma:
        decimal = "." if token.rfind(".") > token.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        return float(token.replace(thousands, "").replace(decimal, "."))
    separator = "." if has_dot else "," if has_comma else None
    if separator is None:
        return float(token)
    parts = token.split(separator)
    if len(parts) > 2 or len(parts[1]) == 3:
        return float("".join(parts))
    return float(f"{parts[0]}.{parts[1]}")


def _extract_amounts(text: str) -> list[int]:
    matches = [
        (_parse_number(number), _MAGNITUDES.get(suffix or "", 1))
        for number, suffix in _AMOUNT.findall(text)
    ]
    # "Rp 5 - 7 juta": a bare leading number shares the magnitude of the next amount.
    if len(matches) >= 2 and matches[0][1] == 1 and matches[1][1] > 1 and matches[0][0] < 1000:
        matches[0] = (matches[0][0], matches[1][1])
    return [round(value * magnitude) for value, magnitude in matches]


def _detect_currency(lowered: str) -> str | None:
    for code, pattern in _CURRENCY_MARKERS:
        if pattern.search(lowered):
            return code
    return None


def _detect_period(lowered: str) -> SalaryPeriod | None:
    for period, pattern in _PERIOD_MARKERS:
        if pattern.search(lowered):
            return period
    return None


def parse_salary(
    value: object,
    *,
    default_currency: str | None = None,
    assumed_period: SalaryPeriod | None = None,
) -> SalaryParse:
    """Parse salary text such as "Rp 6,8 jt-7,4 jt" or "IDR 120.000.000 / tahun".

    ``default_currency`` and ``assumed_period`` express a documented source convention
    (e.g. a board that only ever shows monthly IDR). They are used only when the text
    itself is silent, and their use is recorded in the result.
    """
    text = clean_text(value)
    if text is None:
        return SalaryParse(SalaryStatus.NOT_DISCLOSED)
    lowered = text.casefold()
    if any(phrase in lowered for phrase in _NOT_DISCLOSED_PHRASES):
        return SalaryParse(SalaryStatus.NOT_DISCLOSED)

    amounts = _extract_amounts(lowered)
    if not amounts:
        if any(phrase in lowered for phrase in _NEGOTIABLE_PHRASES):
            return SalaryParse(SalaryStatus.NEGOTIABLE)
        return SalaryParse(SalaryStatus.UNPARSEABLE)

    flags: list[str] = []
    currency = _detect_currency(lowered)
    if currency is None and default_currency is not None:
        currency = default_currency
        flags.append(FLAG_CURRENCY_ASSUMED)

    period = _detect_period(lowered)
    period_assumed = False
    if period is None:
        if assumed_period is not None:
            period, period_assumed = assumed_period, True
        else:
            period = SalaryPeriod.UNKNOWN

    return evaluate_salary_amounts(
        amounts[0],
        amounts[1] if len(amounts) > 1 else None,
        currency=currency,
        period=period,
        period_assumed=period_assumed,
        flags=flags,
    )


def evaluate_salary_amounts(
    minimum: int | None,
    maximum: int | None,
    *,
    currency: str | None,
    period: SalaryPeriod,
    period_assumed: bool = False,
    flags: list[str] | None = None,
) -> SalaryParse:
    """Validate a parsed or API-provided salary range and attach plausibility flags.

    A single amount (only one bound known) is stored as an exact figure, min == max.
    """
    flags = list(flags or [])
    if minimum is None and maximum is None:
        return SalaryParse(SalaryStatus.NOT_DISCLOSED)
    if minimum is None or maximum is None:
        minimum = maximum = minimum if minimum is not None else maximum
        flags.append(FLAG_SINGLE_VALUE)
    assert minimum is not None and maximum is not None

    if minimum <= 0 or maximum <= 0:
        return SalaryParse(SalaryStatus.INVALID, minimum, maximum, currency, period, period_assumed)
    if minimum > maximum:
        flags.append(FLAG_MIN_GREATER_THAN_MAX)
        return SalaryParse(
            SalaryStatus.INVALID, minimum, maximum, currency, period, period_assumed, tuple(flags)
        )

    if maximum > WIDE_RANGE_RATIO * minimum:
        flags.append(FLAG_WIDE_RANGE)
    if currency == "IDR":
        monthly_min, monthly_max = _to_monthly(minimum, period), _to_monthly(maximum, period)
        if monthly_max is not None and monthly_max > IDR_MONTHLY_HIGH_OUTLIER:
            flags.append(FLAG_HIGH_OUTLIER)
        if monthly_min is not None and monthly_min < IDR_MONTHLY_LOW_OUTLIER:
            flags.append(FLAG_LOW_OUTLIER)
    return SalaryParse(
        SalaryStatus.DISCLOSED, minimum, maximum, currency, period, period_assumed, tuple(flags)
    )
