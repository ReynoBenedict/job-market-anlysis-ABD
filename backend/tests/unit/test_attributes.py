import pytest

from talentscope.normalization.attributes import (
    normalize_education,
    normalize_employment_type,
    parse_experience,
    parse_posting_age,
    split_card_tags,
)
from talentscope.normalization.role_family import classify_role_family
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    ExperienceBand,
    RoleFamily,
    WorkArrangement,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Penuh Waktu", EmploymentType.FULL_TIME),
        ("Full-time", EmploymentType.FULL_TIME),
        ("Paruh Waktu", EmploymentType.PART_TIME),
        ("Kontrak", EmploymentType.CONTRACT),
        ("Magang", EmploymentType.INTERNSHIP),
        ("Internship", EmploymentType.INTERNSHIP),
        ("Freelance", EmploymentType.FREELANCE),
        (None, EmploymentType.UNKNOWN),
        ("Lainnya", EmploymentType.UNKNOWN),
    ],
)
def test_employment_type(label: str | None, expected: EmploymentType) -> None:
    assert normalize_employment_type(label) is expected


@pytest.mark.parametrize(
    ("text", "minimum", "maximum", "band"),
    [
        ("1–3 tahun", 1, 3, ExperienceBand.Y1_3),
        ("3-5 tahun", 3, 5, ExperienceBand.Y3_5),
        ("5–10 tahun", 5, 10, ExperienceBand.Y5_10),
        ("Lebih dari 10 tahun", 10, None, ExperienceBand.OVER_10),
        ("Kurang dari 1 tahun", 0, 1, ExperienceBand.UNDER_1),
        ("Fresh Graduate", 0, 0, ExperienceBand.UNDER_1),
        ("2+ years", 2, None, ExperienceBand.Y1_3),
        ("Not Specified", None, None, ExperienceBand.UNKNOWN),
    ],
)
def test_experience(
    text: str, minimum: int | None, maximum: int | None, band: ExperienceBand
) -> None:
    parsed = parse_experience(text)
    assert (parsed.min_years, parsed.max_years, parsed.band) == (minimum, maximum, band)


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("Minimal Sarjana (S1)", EducationLevel.BACHELOR),
        ("Minimal Diploma (D1 - D4)", EducationLevel.DIPLOMA),
        ("Minimal SMA/SMK", EducationLevel.SMA_SMK),
        ("Minimal SD", EducationLevel.SD),
        ("Minimal Magister (S2)", EducationLevel.MASTER),
        ("Minimal Pendidikan Profesi", EducationLevel.PROFESSIONAL),
        ("Tidak ada", EducationLevel.UNKNOWN),
    ],
)
def test_education(text: str, level: EducationLevel) -> None:
    assert normalize_education(text) is level


def test_card_tags_separate_work_arrangement_and_truncation() -> None:
    tags = split_card_tags(["Hybrid", "+3", "SQL", "Python", "SQL"])
    assert tags.skills == ("SQL", "Python")
    assert tags.hidden_count == 3
    assert tags.work_arrangement is WorkArrangement.HYBRID


def test_remote_tag_is_not_a_skill() -> None:
    tags = split_card_tags(["+5", "Remote/Dari rumah"])
    assert tags.skills == ()
    assert tags.work_arrangement is WorkArrangement.REMOTE
    assert tags.work_arrangement_evidence == "Remote/Dari rumah"


def test_listing_badges_are_ignored() -> None:
    assert split_card_tags(["Perusahaan Premium", "Excel"]).skills == ("Excel",)


@pytest.mark.parametrize(
    ("text", "days", "urgent", "approximate"),
    [
        ("Kemarin", 1, False, False),
        ("UrgentKemarin", 1, True, False),
        ("Urgent3 hari yang lalu", 3, True, False),
        ("13 jam yang lalu", 0, False, False),
        ("2 bulan yang lalu", 60, False, True),
        ("Not Specified", None, False, False),
        ("tanggal tidak jelas", None, False, False),
    ],
)
def test_posting_age(text: str, days: int | None, urgent: bool, approximate: bool) -> None:
    age = parse_posting_age(text)
    assert (age.days, age.is_urgent, age.approximate) == (days, urgent, approximate)


@pytest.mark.parametrize(
    ("title", "family"),
    [
        ("Data Engineer", RoleFamily.DATA_ANALYTICS),
        ("QA Engineer", RoleFamily.QUALITY_ASSURANCE),
        ("DevOps Engineer", RoleFamily.INFRASTRUCTURE_DEVOPS),
        ("C++ Software Engineer", RoleFamily.SOFTWARE_ENGINEERING),
        ("Backend Developer (.NET)", RoleFamily.SOFTWARE_ENGINEERING),
        ("UI/UX Designer Intern", RoleFamily.DESIGN_CREATIVE),
        ("IT Project Manager", RoleFamily.PRODUCT_PROJECT),
        ("Administrator HR", RoleFamily.HUMAN_RESOURCES),
        ("Finance, Accounting & Tax", RoleFamily.FINANCE_ACCOUNTING),
        ("Management Trainee", RoleFamily.GRADUATE_PROGRAM),
        ("Digital Marketing", RoleFamily.MARKETING),
        ("Civil Engineer", RoleFamily.ENGINEERING),
        # Blue-collar and service roles that dominate the archived regional job sites.
        ("Barista – Fulltime", RoleFamily.FOOD_HOSPITALITY),
        ("Cook Helper", RoleFamily.FOOD_HOSPITALITY),
        ("Store Crew (SMA/Sederajat)", RoleFamily.RETAIL_STORE),
        ("Kasir", RoleFamily.RETAIL_STORE),
        ("Kurir Motor Ekspedisi Bekasi", RoleFamily.TRANSPORT_DELIVERY),
        ("Operator Produksi", RoleFamily.PRODUCTION),
        ("Production Engineer", RoleFamily.ENGINEERING),
        ("Satpam", RoleFamily.SECURITY_FACILITIES),
        ("Security Engineer", RoleFamily.INFRASTRUCTURE_DEVOPS),
        ("Admin Gudang", RoleFamily.SUPPLY_CHAIN),
        ("Master of Ceremony", RoleFamily.OTHER),
        ("", RoleFamily.OTHER),
    ],
)
def test_role_family_rules(title: str, family: RoleFamily) -> None:
    assert classify_role_family(title) is family
