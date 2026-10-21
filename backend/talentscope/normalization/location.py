"""Location normalization for Indonesian job locations.

Sources write locations as free text ("Kab. Tangerang,Banten", "Jakarta Selatan",
"Remote"). We keep the original string and add a province from the official list of
38 provinces when it is stated or can be inferred from a well-known city. Nothing is
geocoded below city/regency level (SRS FR-DATA-011).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from talentscope.normalization.text import clean_text, normalize_for_matching

PROVINCES = (
    "Aceh",
    "Sumatera Utara",
    "Sumatera Barat",
    "Riau",
    "Kepulauan Riau",
    "Jambi",
    "Sumatera Selatan",
    "Kepulauan Bangka Belitung",
    "Bengkulu",
    "Lampung",
    "DKI Jakarta",
    "Jawa Barat",
    "Banten",
    "Jawa Tengah",
    "DI Yogyakarta",
    "Jawa Timur",
    "Bali",
    "Nusa Tenggara Barat",
    "Nusa Tenggara Timur",
    "Kalimantan Barat",
    "Kalimantan Tengah",
    "Kalimantan Selatan",
    "Kalimantan Timur",
    "Kalimantan Utara",
    "Sulawesi Utara",
    "Gorontalo",
    "Sulawesi Tengah",
    "Sulawesi Barat",
    "Sulawesi Selatan",
    "Sulawesi Tenggara",
    "Maluku",
    "Maluku Utara",
    "Papua",
    "Papua Barat",
    "Papua Barat Daya",
    "Papua Tengah",
    "Papua Pegunungan",
    "Papua Selatan",
)

_PROVINCE_ALIASES = {
    **{normalize_for_matching(name): name for name in PROVINCES},
    "jakarta": "DKI Jakarta",
    "dki": "DKI Jakarta",
    "daerah khusus ibukota jakarta": "DKI Jakarta",
    "daerah khusus jakarta": "DKI Jakarta",
    "yogyakarta": "DI Yogyakarta",
    "diy": "DI Yogyakarta",
    "daerah istimewa yogyakarta": "DI Yogyakarta",
    "d i yogyakarta": "DI Yogyakarta",
    "bangka belitung": "Kepulauan Bangka Belitung",
    "babel": "Kepulauan Bangka Belitung",
    "kepri": "Kepulauan Riau",
    "ntb": "Nusa Tenggara Barat",
    "ntt": "Nusa Tenggara Timur",
    "jabar": "Jawa Barat",
    "jateng": "Jawa Tengah",
    "jatim": "Jawa Timur",
    "sumut": "Sumatera Utara",
    "sumbar": "Sumatera Barat",
    "sumsel": "Sumatera Selatan",
    "nad": "Aceh",
    "nanggroe aceh darussalam": "Aceh",
    # English and older spellings seen in schema.org addresses.
    "sumatra utara": "Sumatera Utara",
    "sumatra barat": "Sumatera Barat",
    "sumatra selatan": "Sumatera Selatan",
    "north sumatra": "Sumatera Utara",
    "west sumatra": "Sumatera Barat",
    "south sumatra": "Sumatera Selatan",
    "west java": "Jawa Barat",
    "central java": "Jawa Tengah",
    "east java": "Jawa Timur",
    "east kalimantan": "Kalimantan Timur",
    "south kalimantan": "Kalimantan Selatan",
    "west kalimantan": "Kalimantan Barat",
    "south sulawesi": "Sulawesi Selatan",
    "north sulawesi": "Sulawesi Utara",
    "riau islands": "Kepulauan Riau",
}

# Cities common in Indonesian listings whose province is unambiguous. Used only when the
# source gives a city without a province; the result is marked as inferred.
_CITY_PROVINCES = {
    "jakarta selatan": "DKI Jakarta",
    "jakarta barat": "DKI Jakarta",
    "jakarta pusat": "DKI Jakarta",
    "jakarta utara": "DKI Jakarta",
    "jakarta timur": "DKI Jakarta",
    "kepulauan seribu": "DKI Jakarta",
    # Jakarta districts (kecamatan) that are not also common place names elsewhere.
    **{
        district: "DKI Jakarta"
        for district in (
            "cakung",
            "cempaka putih",
            "cengkareng",
            "cilandak",
            "cilincing",
            "ciracas",
            "duren sawit",
            "gambir",
            "grogol petamburan",
            "jagakarsa",
            "jatinegara",
            "johar baru",
            "kalideres",
            "kebayoran baru",
            "kebayoran lama",
            "kebon jeruk",
            "kelapa gading",
            "kemayoran",
            "kembangan",
            "kramat jati",
            "mampang prapatan",
            "matraman",
            "pademangan",
            "palmerah",
            "pasar minggu",
            "pasar rebo",
            "penjaringan",
            "pesanggrahan",
            "pulo gadung",
            "sawah besar",
            "tambora",
            "tanjung priok",
            "tebet",
        )
    },
    "cikarang": "Jawa Barat",
    "cikarang barat": "Jawa Barat",
    "cikarang utara": "Jawa Barat",
    "cikarang selatan": "Jawa Barat",
    "cikupa": "Banten",
    "balikpapan selatan": "Kalimantan Timur",
    "bandung": "Jawa Barat",
    "bekasi": "Jawa Barat",
    "depok": "Jawa Barat",
    "bogor": "Jawa Barat",
    "cimahi": "Jawa Barat",
    "karawang": "Jawa Barat",
    "cirebon": "Jawa Barat",
    "tangerang": "Banten",
    "tangerang selatan": "Banten",
    "serang": "Banten",
    "cilegon": "Banten",
    "semarang": "Jawa Tengah",
    "surakarta": "Jawa Tengah",
    "solo": "Jawa Tengah",
    "sleman": "DI Yogyakarta",
    "bantul": "DI Yogyakarta",
    "surabaya": "Jawa Timur",
    "malang": "Jawa Timur",
    "sidoarjo": "Jawa Timur",
    "gresik": "Jawa Timur",
    "denpasar": "Bali",
    "badung": "Bali",
    "medan": "Sumatera Utara",
    "batam": "Kepulauan Riau",
    "palembang": "Sumatera Selatan",
    "makassar": "Sulawesi Selatan",
    "balikpapan": "Kalimantan Timur",
    "samarinda": "Kalimantan Timur",
    "pekanbaru": "Riau",
    "padang": "Sumatera Barat",
    "bandar lampung": "Lampung",
    "manado": "Sulawesi Utara",
    "pontianak": "Kalimantan Barat",
    "banjarmasin": "Kalimantan Selatan",
}

_REMOTE_MARKERS = ("remote", "work from home", "wfh", "dari rumah", "jarak jauh")
_REGENCY_PREFIX = re.compile(r"^(?:kab\.?|kabupaten)\s+", re.IGNORECASE)
_CITY_PREFIX = re.compile(r"^(?:kota(?:\s+administrasi)?)\s+", re.IGNORECASE)


class LocationConfidence(str, Enum):
    SOURCE_STRUCTURED = "SOURCE_STRUCTURED"  # province stated explicitly by the source
    INFERRED = "INFERRED"  # province derived from a known city name
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LocationParse:
    city: str | None
    province: str | None
    confidence: LocationConfidence
    is_remote: bool = False
    is_regency: bool | None = None  # True for "Kab.", False for "Kota", None if unstated


def canonical_province(value: str | None) -> str | None:
    if not value:
        return None
    key = normalize_for_matching(re.sub(r"^provinsi\s+", "", value, flags=re.IGNORECASE))
    return _PROVINCE_ALIASES.get(key)


def canonical_city(city: str | None) -> str | None:
    """One spelling per regency: "Kab. Bandung", "KAB Bandung" and "Kabupaten Bandung" all
    become "Kabupaten Bandung", so the same place is not counted (or fingerprinted) as two.
    "Kota" and unprefixed names are left as written: "Bogor" may be the city or the regency."""
    city = clean_text(city)
    if city is None:
        return None
    return _REGENCY_PREFIX.sub("Kabupaten ", city)


def _city_base_name(city: str) -> str:
    return _CITY_PREFIX.sub("", _REGENCY_PREFIX.sub("", city))


def _regency_marker(city: str) -> bool | None:
    if _REGENCY_PREFIX.match(city):
        return True
    if _CITY_PREFIX.match(city):
        return False
    return None


def parse_location(value: object) -> LocationParse:
    text = clean_text(value)
    if text is None:
        return LocationParse(None, None, LocationConfidence.UNKNOWN)

    lowered = text.casefold()
    is_remote = any(marker in lowered for marker in _REMOTE_MARKERS)

    if "," in text:
        city_part, _, province_part = text.rpartition(",")
        province = canonical_province(province_part.strip())
        city = canonical_city(city_part)
        if province is not None:
            # Drop a city part that merely repeats the province ("DKI Jakarta, DKI Jakarta"),
            # but keep cities that share a name with an alias ("Yogyakarta, DI Yogyakarta").
            if city is not None and normalize_for_matching(city) == normalize_for_matching(
                province
            ):
                city = None
            return LocationParse(
                city,
                province,
                LocationConfidence.SOURCE_STRUCTURED,
                is_remote,
                _regency_marker(city) if city else None,
            )

    province = canonical_province(text)
    if province is not None:
        return LocationParse(None, province, LocationConfidence.SOURCE_STRUCTURED, is_remote)

    if is_remote:
        return LocationParse(None, None, LocationConfidence.UNKNOWN, is_remote=True)

    inferred = _CITY_PROVINCES.get(normalize_for_matching(_city_base_name(text)))
    return LocationParse(
        canonical_city(text),
        inferred,
        LocationConfidence.INFERRED if inferred else LocationConfidence.UNKNOWN,
        is_remote=False,
        is_regency=_regency_marker(text),
    )
