"""Controlled vocabularies shared by normalization, persistence, and the API.

Codes are stored in the database; the Indonesian labels are what the API returns to
the web client, so user-facing wording for a category lives in exactly one place.
"""

from __future__ import annotations

from enum import Enum


class LabelledEnum(str, Enum):
    """String enum whose members carry an Indonesian display label."""

    label: str

    # `label` has a default only so type checkers accept value lookup, e.g.
    # `EmploymentType("FULL_TIME")`; members are always declared as (code, label).
    def __new__(cls, code: str, label: str = "") -> LabelledEnum:
        member = str.__new__(cls, code)
        member._value_ = code
        member.label = label
        return member


class EmploymentType(LabelledEnum):
    FULL_TIME = ("FULL_TIME", "Penuh waktu")
    PART_TIME = ("PART_TIME", "Paruh waktu")
    CONTRACT = ("CONTRACT", "Kontrak")
    TEMPORARY = ("TEMPORARY", "Sementara")
    INTERNSHIP = ("INTERNSHIP", "Magang")
    FREELANCE = ("FREELANCE", "Freelance")
    APPRENTICESHIP = ("APPRENTICESHIP", "Pemagangan")
    PROJECT_BASED = ("PROJECT_BASED", "Berbasis proyek")
    VOLUNTEER = ("VOLUNTEER", "Sukarela")
    UNKNOWN = ("UNKNOWN", "Tidak dicantumkan")


class WorkArrangement(LabelledEnum):
    ONSITE = ("ONSITE", "Di kantor")
    HYBRID = ("HYBRID", "Hybrid")
    REMOTE = ("REMOTE", "Remote")
    FIELD = ("FIELD", "Lapangan")
    UNKNOWN = ("UNKNOWN", "Tidak dicantumkan")


class EducationLevel(LabelledEnum):
    """Minimum education requested; declared in ascending order of attainment."""

    SD = ("SD", "SD")
    SMP = ("SMP", "SMP")
    SMA_SMK = ("SMA_SMK", "SMA/SMK")
    DIPLOMA = ("DIPLOMA", "Diploma (D1–D4)")
    BACHELOR = ("BACHELOR", "Sarjana (S1)")
    PROFESSIONAL = ("PROFESSIONAL", "Pendidikan profesi")
    MASTER = ("MASTER", "Magister (S2)")
    DOCTORATE = ("DOCTORATE", "Doktor (S3)")
    UNKNOWN = ("UNKNOWN", "Tidak dicantumkan")


class ExperienceBand(LabelledEnum):
    UNDER_1 = ("UNDER_1", "< 1 tahun")
    Y1_3 = ("Y1_3", "1–3 tahun")
    Y3_5 = ("Y3_5", "3–5 tahun")
    Y5_10 = ("Y5_10", "5–10 tahun")
    OVER_10 = ("OVER_10", "> 10 tahun")
    UNKNOWN = ("UNKNOWN", "Tidak dicantumkan")


class SalaryStatus(LabelledEnum):
    DISCLOSED = ("DISCLOSED", "Dicantumkan")
    NOT_DISCLOSED = ("NOT_DISCLOSED", "Tidak dicantumkan")
    NEGOTIABLE = ("NEGOTIABLE", "Dapat dinegosiasikan")
    INVALID = ("INVALID", "Tidak valid")
    UNPARSEABLE = ("UNPARSEABLE", "Tidak dapat dibaca")


class SalaryPeriod(LabelledEnum):
    HOUR = ("HOUR", "per jam")
    DAY = ("DAY", "per hari")
    WEEK = ("WEEK", "per minggu")
    MONTH = ("MONTH", "per bulan")
    YEAR = ("YEAR", "per tahun")
    UNKNOWN = ("UNKNOWN", "periode tidak diketahui")


class Freshness(LabelledEnum):
    """Lifecycle labels (SRS FR-LIFE-001) that can be derived from available evidence."""

    # No source is re-checked live, so there is no "verified active" state: the best we
    # can say is that a listing was seen recently and its status is still unconfirmed.
    POTENTIALLY_ACTIVE = ("POTENTIALLY_ACTIVE", "Baru terlihat, belum diverifikasi")
    NOT_SEEN_RECENTLY = ("NOT_SEEN_RECENTLY", "Riwayat lowongan")
    EXPIRED_BY_SOURCE = ("EXPIRED_BY_SOURCE", "Kedaluwarsa menurut sumber")


class ObservationMethod(LabelledEnum):
    """How a source's listings were observed; tells users how much a listing can be trusted
    to reflect the live page."""

    ARCHIVE = ("ARCHIVE", "Arsip web")
    SNAPSHOT = ("SNAPSHOT", "Snapshot historis")
    LIVE = ("LIVE", "Langsung dari sumber")

    @classmethod
    def of_technical_method(cls, technical_method: str) -> ObservationMethod:
        if technical_method == "archive_index":
            return cls.ARCHIVE
        if technical_method == "manual_import":
            return cls.SNAPSHOT
        return cls.LIVE


class PermissionStatus(LabelledEnum):
    DISCOVERED = ("DISCOVERED", "Ditemukan")
    NEEDS_REVIEW = ("NEEDS_REVIEW", "Perlu ditinjau")
    APPROVED = ("APPROVED", "Diizinkan (izin/lisensi tercatat)")
    APPROVED_WITH_CONDITIONS = ("APPROVED_WITH_CONDITIONS", "Boleh dipakai dengan syarat")
    REQUIRES_WRITTEN_PERMISSION = ("REQUIRES_WRITTEN_PERMISSION", "Perlu izin tertulis")
    BLOCKED = ("BLOCKED", "Diblokir")
    PAUSED = ("PAUSED", "Dijeda")
    RETIRED = ("RETIRED", "Dihentikan")


# Only these states allow a connector to run (SRS FR-SRC-002, FR-ING-004).
RUNNABLE_PERMISSION_STATUSES = frozenset(
    {PermissionStatus.APPROVED, PermissionStatus.APPROVED_WITH_CONDITIONS}
)


class RunStatus(LabelledEnum):
    RUNNING = ("RUNNING", "Berjalan")
    SUCCEEDED = ("SUCCEEDED", "Berhasil")
    PARTIAL = ("PARTIAL", "Berhasil sebagian")
    FAILED = ("FAILED", "Gagal")
    REFUSED = ("REFUSED", "Ditolak kebijakan")


class RunErrorCategory(LabelledEnum):
    POLICY_BLOCKED = ("POLICY_BLOCKED", "Diblokir kebijakan sumber")
    ACCESS_DENIED = ("ACCESS_DENIED", "Akses ditolak sumber")
    RATE_LIMITED = ("RATE_LIMITED", "Dibatasi laju permintaan")
    NETWORK = ("NETWORK", "Gangguan jaringan")
    SCHEMA_CHANGED = ("SCHEMA_CHANGED", "Struktur sumber berubah")
    PARSE_ERROR = ("PARSE_ERROR", "Gagal mengurai data")
    INVALID_RECORDS = ("INVALID_RECORDS", "Rekaman tidak valid")
    INTERNAL = ("INTERNAL", "Kesalahan internal")


class RoleFamily(LabelledEnum):
    SOFTWARE_ENGINEERING = ("SOFTWARE_ENGINEERING", "Rekayasa Perangkat Lunak")
    DATA_ANALYTICS = ("DATA_ANALYTICS", "Data & Analitik")
    INFRASTRUCTURE_DEVOPS = ("INFRASTRUCTURE_DEVOPS", "Infrastruktur & DevOps")
    QUALITY_ASSURANCE = ("QUALITY_ASSURANCE", "Quality Assurance & Pengujian")
    IT_SUPPORT = ("IT_SUPPORT", "Dukungan & Administrasi TI")
    PRODUCT_PROJECT = ("PRODUCT_PROJECT", "Produk & Manajemen Proyek")
    DESIGN_CREATIVE = ("DESIGN_CREATIVE", "Desain & Kreatif")
    MARKETING = ("MARKETING", "Pemasaran")
    SALES_BUSINESS = ("SALES_BUSINESS", "Penjualan & Pengembangan Bisnis")
    FINANCE_ACCOUNTING = ("FINANCE_ACCOUNTING", "Keuangan & Akuntansi")
    HUMAN_RESOURCES = ("HUMAN_RESOURCES", "SDM & Rekrutmen")
    ADMIN_OPERATIONS = ("ADMIN_OPERATIONS", "Administrasi & Operasional")
    CUSTOMER_SERVICE = ("CUSTOMER_SERVICE", "Layanan Pelanggan")
    SUPPLY_CHAIN = ("SUPPLY_CHAIN", "Rantai Pasok & Pengadaan")
    ENGINEERING = ("ENGINEERING", "Teknik (Non-Perangkat Lunak)")
    GRADUATE_PROGRAM = ("GRADUATE_PROGRAM", "Program Lulusan & Management Trainee")
    EDUCATION = ("EDUCATION", "Pendidikan & Pelatihan")
    HEALTHCARE = ("HEALTHCARE", "Kesehatan")
    LEGAL = ("LEGAL", "Hukum & Kepatuhan")
    FOOD_HOSPITALITY = ("FOOD_HOSPITALITY", "Makanan, Minuman & Perhotelan")
    RETAIL_STORE = ("RETAIL_STORE", "Ritel & Toko")
    TRANSPORT_DELIVERY = ("TRANSPORT_DELIVERY", "Transportasi & Pengiriman")
    PRODUCTION = ("PRODUCTION", "Produksi & Pabrik")
    SECURITY_FACILITIES = ("SECURITY_FACILITIES", "Keamanan & Kebersihan")
    OTHER = ("OTHER", "Lainnya / Belum terklasifikasi")
