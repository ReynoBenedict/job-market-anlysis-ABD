import pytest

from talentscope.normalization.location import (
    LocationConfidence,
    canonical_province,
    parse_location,
)
from talentscope.normalization.text import clean_text, normalize_for_matching


@pytest.mark.parametrize(
    "value", [None, "", "   ", "Not Specified", "not specified", "-", float("nan")]
)
def test_clean_text_treats_placeholders_as_missing(value: object) -> None:
    assert clean_text(value) is None


def test_clean_text_collapses_whitespace_and_nbsp() -> None:
    assert clean_text("  Rp 7\xa0jt \n -  9 jt ") == "Rp 7 jt - 9 jt"


def test_clean_text_keeps_indonesian_punctuation() -> None:
    assert clean_text("1–3 tahun") == "1–3 tahun"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("C++ Software Engineer", "c++ software engineer"),
        ("Backend Developer (.NET)", "backend developer net"),
        ("Finance, Accounting & Tax", "finance accounting tax"),
        ("UI/UX Designer", "ui ux designer"),
        ("[INTERN] Backend Developer", "intern backend developer"),
        ("((()))", ""),
        ("Café Supervisor", "cafe supervisor"),
    ],
)
def test_normalize_for_matching_never_creates_empty_tokens(title: str, expected: str) -> None:
    normalized = normalize_for_matching(title)
    assert normalized == expected
    # The legacy K-Means preprocessing produced "" tokens from punctuation; this must not.
    assert "" not in normalized.split(" ") or normalized == ""


def test_structured_location() -> None:
    result = parse_location("Kab. Tangerang,Banten")
    assert (result.city, result.province, result.is_regency) == (
        "Kabupaten Tangerang",
        "Banten",
        True,
    )
    assert result.confidence is LocationConfidence.SOURCE_STRUCTURED


@pytest.mark.parametrize(
    "text",
    ["Kab. Bandung, Jawa Barat", "Kabupaten Bandung, Jawa Barat", "KAB Bandung, Jawa Barat"],
)
def test_regency_spellings_become_one_city(text: str) -> None:
    # Glints writes "Kab. X", archive sites "Kabupaten X": one place, one city value (and
    # one cross-source fingerprint), not two.
    assert parse_location(text).city == "Kabupaten Bandung"


def test_city_and_unprefixed_names_are_left_as_written() -> None:
    # "Bogor" may be Kota or Kabupaten Bogor; it must not be guessed.
    assert parse_location("Kota Bogor, Jawa Barat").city == "Kota Bogor"
    assert parse_location("Bogor, Jawa Barat").city == "Bogor"


def test_city_that_shares_a_name_with_a_province_alias_is_kept() -> None:
    result = parse_location("Yogyakarta,DI Yogyakarta")
    assert (result.city, result.province) == ("Yogyakarta", "DI Yogyakarta")


def test_city_repeating_the_province_is_dropped() -> None:
    assert parse_location("DKI Jakarta, DKI Jakarta").city is None


@pytest.mark.parametrize(
    ("alias", "province"),
    [
        ("Jakarta", "DKI Jakarta"),
        ("D.I. Yogyakarta", "DI Yogyakarta"),
        ("Provinsi Jawa Barat", "Jawa Barat"),
        ("jatim", "Jawa Timur"),
        ("Atlantis", None),
    ],
)
def test_province_aliases(alias: str, province: str | None) -> None:
    assert canonical_province(alias) == province


def test_city_without_province_is_inferred_and_marked() -> None:
    result = parse_location("Kota Bekasi")
    assert (result.city, result.province, result.is_regency) == ("Kota Bekasi", "Jawa Barat", False)
    assert result.confidence is LocationConfidence.INFERRED


def test_unknown_place_is_kept_but_unresolved() -> None:
    result = parse_location("Singapore")
    assert (result.city, result.province, result.confidence) == (
        "Singapore",
        None,
        LocationConfidence.UNKNOWN,
    )


def test_remote_location() -> None:
    result = parse_location("Remote")
    assert result.is_remote and result.city is None and result.province is None
