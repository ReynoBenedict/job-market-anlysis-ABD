import pytest

from talentscope.normalization.salary import (
    FLAG_CURRENCY_ASSUMED,
    FLAG_HIGH_OUTLIER,
    FLAG_LOW_OUTLIER,
    FLAG_MIN_GREATER_THAN_MAX,
    FLAG_SINGLE_VALUE,
    FLAG_WIDE_RANGE,
    evaluate_salary_amounts,
    parse_salary,
)
from talentscope.vocab import SalaryPeriod, SalaryStatus

MONTHLY_IDR = {"default_currency": "IDR", "assumed_period": SalaryPeriod.MONTH}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rp 7\xa0jt-9\xa0jt", (7_000_000, 9_000_000)),  # non-breaking spaces from the source HTML
        ("Rp 6,8 jt-7,4 jt", (6_800_000, 7_400_000)),  # Indonesian decimal comma
        ("Rp 2.5 jt", (2_500_000, 2_500_000)),  # decimal point also accepted
        ("IDR 5.000.000 - 7.000.000", (5_000_000, 7_000_000)),  # thousands separators
        ("Rp 1.500.000", (1_500_000, 1_500_000)),
        ("Rp 5 - 7 juta", (5_000_000, 7_000_000)),  # magnitude written once
        ("Rp 500 rb - 750 rb", (500_000, 750_000)),
    ],
)
def test_parses_indonesian_amount_formats(text: str, expected: tuple[int, int]) -> None:
    result = parse_salary(text, **MONTHLY_IDR)
    assert result.status is SalaryStatus.DISCLOSED
    assert (result.minimum, result.maximum) == expected
    assert result.currency == "IDR"


@pytest.mark.parametrize(
    "text",
    [
        "Gaji Tidak Ditampilkan",
        "Tidak Ditampilkan",
        "Gaji di atas ekspektasi",
        "",
        None,
        "  ",
        "Not Specified",
    ],
)
def test_hidden_or_missing_salary_is_a_status_not_zero(text: object) -> None:
    result = parse_salary(text, **MONTHLY_IDR)
    assert result.status is SalaryStatus.NOT_DISCLOSED
    assert result.minimum is None and result.maximum is None
    assert result.monthly_minimum is None


def test_negotiable_without_numbers() -> None:
    assert parse_salary("Gaji nego").status is SalaryStatus.NEGOTIABLE


def test_text_without_amounts_is_unparseable() -> None:
    assert parse_salary("Sesuai standar perusahaan").status is SalaryStatus.UNPARSEABLE


def test_stated_annual_period_is_converted_to_monthly() -> None:
    result = parse_salary("Rp 120 juta - 180 juta / tahun", **MONTHLY_IDR)
    assert result.period is SalaryPeriod.YEAR
    assert result.period_assumed is False  # the text states the period; no assumption
    assert (result.monthly_minimum, result.monthly_maximum) == (10_000_000, 15_000_000)


def test_assumed_period_is_marked_as_assumption() -> None:
    result = parse_salary("Rp 7 jt-9 jt", **MONTHLY_IDR)
    assert result.period is SalaryPeriod.MONTH
    assert result.period_assumed is True


def test_unknown_period_without_convention_has_no_monthly_value() -> None:
    result = parse_salary("Rp 7 jt-9 jt")
    assert result.period is SalaryPeriod.UNKNOWN
    assert result.monthly_minimum is None


def test_hourly_pay_is_not_converted_without_a_schedule() -> None:
    result = parse_salary("Rp 50 rb / jam")
    assert result.period is SalaryPeriod.HOUR
    assert result.monthly_minimum is None and result.monthly_maximum is None


def test_usd_uses_english_thousands_separator() -> None:
    result = parse_salary("USD 1,000 - 2,000 per month")
    assert (result.currency, result.minimum, result.maximum) == ("USD", 1000, 2000)
    assert result.period is SalaryPeriod.MONTH
    # Outlier thresholds are defined for IDR only.
    assert FLAG_LOW_OUTLIER not in result.flags


def test_currency_assumption_is_flagged() -> None:
    result = parse_salary("5 jt - 6 jt", default_currency="IDR")
    assert result.currency == "IDR"
    assert FLAG_CURRENCY_ASSUMED in result.flags


def test_single_value_is_exact_range() -> None:
    result = parse_salary("Rp 2,5 jt", **MONTHLY_IDR)
    assert result.minimum == result.maximum == 2_500_000
    assert FLAG_SINGLE_VALUE in result.flags


def test_min_greater_than_max_is_invalid() -> None:
    result = parse_salary("Rp 9 jt - 7 jt", **MONTHLY_IDR)
    assert result.status is SalaryStatus.INVALID
    assert FLAG_MIN_GREATER_THAN_MAX in result.flags


def test_zero_amount_is_invalid() -> None:
    assert parse_salary("Rp 0", **MONTHLY_IDR).status is SalaryStatus.INVALID


def test_extreme_values_are_flagged_not_dropped() -> None:
    # The real snapshot contains "Rp 12 jt-140 jt"; it stays disclosed but flagged.
    result = parse_salary("Rp 12 jt-140 jt", **MONTHLY_IDR)
    assert result.status is SalaryStatus.DISCLOSED
    assert {FLAG_WIDE_RANGE, FLAG_HIGH_OUTLIER} <= set(result.flags)
    assert FLAG_LOW_OUTLIER in parse_salary("Rp 300 rb", **MONTHLY_IDR).flags


def test_structured_amounts_use_same_validation() -> None:
    result = evaluate_salary_amounts(None, 25_000_000, currency="IDR", period=SalaryPeriod.MONTH)
    assert (result.minimum, result.maximum) == (25_000_000, 25_000_000)
    assert FLAG_SINGLE_VALUE in result.flags
    assert evaluate_salary_amounts(
        None, None, currency="IDR", period=SalaryPeriod.MONTH
    ).status is (SalaryStatus.NOT_DISCLOSED)
