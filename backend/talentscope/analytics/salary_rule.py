"""The one rule that decides whether a job's salary is comparable.

A salary is *comparable* when all of these hold:

1. status is DISCLOSED and the currency is IDR;
2. both monthly bounds are known (a monthly or yearly figure; hourly/daily/weekly pay
   is never converted, see normalization.salary);
3. the range is ordered (monthly minimum <= monthly maximum);
4. the monthly midpoint is at least Rp500,000. Lower values are below any provincial
   minimum wage and in practice are parse or template artefacts (e.g. "2–897").

Only comparable salaries enter statistics (overview, histogram, comparison), the salary
filter bounds, the salary sort, and the salary range offered by /filters, so every view
describes the same records. Nothing is deleted: the job keeps its stored salary and its
quality flags. Very high values (> Rp100 juta) and wide ranges remain comparable but are
flagged and counted, because medians and quartiles are robust to them.

The rule is expressed once for SQL (``comparable_salary``) and once for Python
(``is_comparable``); tests check that both agree.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, and_, literal

from talentscope.normalization.salary import IDR_MONTHLY_LOW_OUTLIER
from talentscope.vocab import SalaryStatus

COMPARABLE_CURRENCY = "IDR"
MIN_MONTHLY_MIDPOINT = IDR_MONTHLY_LOW_OUTLIER


def monthly_midpoint(columns: Any) -> ColumnElement[Any]:
    """Midpoint of the monthly range. ``columns`` is ``Job`` or a subquery's ``.c``."""
    midpoint: ColumnElement[Any] = (
        columns.salary_monthly_min + columns.salary_monthly_max
    ) / literal(2.0)
    return midpoint


def monthly_idr_recorded(columns: Any) -> ColumnElement[bool]:
    """Disclosed IDR salary with both monthly bounds, before plausibility checks."""
    return and_(
        columns.salary_status == SalaryStatus.DISCLOSED.value,
        columns.salary_currency == COMPARABLE_CURRENCY,
        columns.salary_monthly_min.is_not(None),
        columns.salary_monthly_max.is_not(None),
    )


def comparable_salary(columns: Any) -> ColumnElement[bool]:
    return and_(
        monthly_idr_recorded(columns),
        columns.salary_monthly_min <= columns.salary_monthly_max,
        monthly_midpoint(columns) >= MIN_MONTHLY_MIDPOINT,
    )


def is_comparable(
    status: str, currency: str | None, monthly_min: int | None, monthly_max: int | None
) -> bool:
    return (
        status == SalaryStatus.DISCLOSED.value
        and currency == COMPARABLE_CURRENCY
        and monthly_min is not None
        and monthly_max is not None
        and monthly_min <= monthly_max
        and (monthly_min + monthly_max) / 2 >= MIN_MONTHLY_MIDPOINT
    )
