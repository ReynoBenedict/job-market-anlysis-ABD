"""Rule-based role-family taxonomy (SRS FR-DATA-015).

Job titles are mapped to a small set of occupational families so that counts and
salaries can be compared across differently worded titles. Rules are ordered: more
specific families come first so that "Data Engineer" is not swallowed by the generic
software rule and "QA Engineer" is not counted as software development.

The taxonomy is versioned; changing a rule changes classifications, so bump the
version and re-run the normalization to keep stored values consistent.
"""

from __future__ import annotations

import re

from talentscope.normalization.text import normalize_for_matching
from talentscope.vocab import RoleFamily

ROLE_TAXONOMY_VERSION = "2026.10.5"

_RULES: tuple[tuple[RoleFamily, str], ...] = (
    (
        RoleFamily.GRADUATE_PROGRAM,
        r"management (?:trainee|training|associate)|graduate (?:development )?program"
        r"|development program|\bodp\b|\bmt\b",
    ),
    # "Admin" as the head noun: the job is administrative even when sales/orders are named.
    (RoleFamily.ADMIN_OPERATIONS, r"^admin(?:istrasi)? (?:sales|penjualan|order)"),
    (
        RoleFamily.QUALITY_ASSURANCE,
        r"\bqa\b|quality assurance|quality control|\bqc\b|qaqc|\bquality\b|\bmutu\b|inspection"
        r"|inspector|\btester\b|\btesting\b|\bsdet\b",
    ),
    (
        RoleFamily.DATA_ANALYTICS,
        r"\bdata (?:scientist|science|analyst|analytics|engineer|engineering|warehouse|architect"
        r"|intelligence|insight)"
        r"|machine learning|\bml\b|\bai\b|artificial intelligence|business intelligence|\bbi\b"
        r"|business analyst|\banalytics\b|\bstatistic",
    ),
    (
        RoleFamily.INFRASTRUCTURE_DEVOPS,
        r"devops|devsecops|site reliability|\bsre\b|cloud (?:engineer|architect)|infrastructure"
        r"|network (?:engineer|administrator)|system(?:s)? (?:administrator|engineer)|sysadmin"
        r"|security (?:engineer|analyst)|cyber ?security|database administrator|\bdba\b"
        r"|platform engineer",
    ),
    (
        RoleFamily.SECURITY_FACILITIES,
        r"satpam|\bsecurity\b|keamanan|cleaning service|cleaner|office ?boy|\bob\b|kebersihan"
        r"|petugas kebersihan|janitor|gardener|tukang kebun|lifeguard",
    ),
    (
        RoleFamily.IT_SUPPORT,
        r"\bit (?:support|staff|officer|admin|administrator|technician|helpdesk|specialist)"
        r"|help ?desk|technical support|\bit\b$|\bstaf+ it\b|it functional",
    ),
    (
        RoleFamily.SOFTWARE_ENGINEERING,
        # "mobile" alone also names field roles ("Relation Officer Mobile"): needs a tech word.
        r"software|developer|programmer|front ?end|back ?end|full ?stack|\bweb\b"
        r"|mobile (?:developer|engineer|app|programmer)|android"
        r"|\bios\b|flutter|react|golang|\bgo\b|\bjava\b|\bphp\b|laravel|\bnet\b|node|c\+\+"
        r"|solution architect|engineering manager|tech lead|\bcoding\b|system(?:s)? analyst",
    ),
    (
        RoleFamily.PRODUCT_PROJECT,
        r"product (?:manager|owner|lead|analyst|specialist|intern|ops|tech)"
        r"|project (?:manager|officer|coordinator|lead)"
        r"|scrum master|program manager|\bpmo\b|delivery manager",
    ),
    (
        RoleFamily.DESIGN_CREATIVE,
        # "Design engineer(ing)" is engineering, handled by the ENGINEERING rule.
        r"^(?!.*engineer).*(?:design|\bui\b|\bux\b|graphic|illustrat|video|photograph|animat|\bmotion"
        r"|creative|copywrit|multimedia|desain|content creator|soundman|audio|konten)",
    ),
    (
        RoleFamily.CUSTOMER_SERVICE,
        r"customer (?:service|support|success|care|experience)|\bcs\b|call cent|contact cent",
    ),
    (
        RoleFamily.HUMAN_RESOURCES,
        r"\bhr\b|\bhrd\b|\bhrga\b|\bhrbp\b|human (?:resource|capital)|recruit|talent acquisition"
        r"|\bpeople\b|personalia|payroll|learning (?:and )?development|learning specialist"
        r"|organi[sz]ational development|pengembangan organisasi|\bhc\b",
    ),
    (
        RoleFamily.FINANCE_ACCOUNTING,
        r"financ|accounting|accountant|akuntan|\btax\b|pajak|audit|treasury|keuangan|bookkeep|budget"
        r"|billing|invoice|collection|penagih|payable|receivable|cost control|fiskal|fiscal|fraud"
        r"|payment|kolektor|collector|\bar controller",
    ),
    (
        RoleFamily.SALES_BUSINESS,
        r"sales|account (?:executive|excutive|manager)|business development|\bbd\b|telemarketing"
        r"|penjualan"
        r"|key account|partnership|merchant acquisition|\bspg\b|\bspb\b|promotor|canvasser"
        r"|bancassurance|product consultant|territory manager|business partner",
    ),
    (
        RoleFamily.MARKETING,
        r"marketing|\bseo\b|\bsem\b|social media|\bbrand|public relation|\bpr\b|communication"
        r"|\bkol\b|campaign|growth|content (?:writer|strategist|specialist)|sosial media"
        r"|media sosial|advertis|marcomm|live ?stream|host live|affiliate|sponsorship|\bevent\b",
    ),
    (
        RoleFamily.SUPPLY_CHAIN,
        r"supply chain|procurement|purchasing|logistic|warehouse|inventory|\bppic\b|\bbuyer\b"
        r"|gudang|pengadaan|shipping|\bexim\b|export|import|distribution|distribusi|tender|\bhub\b"
        r"|picker|porter|pelabuhan",
    ),
    (RoleFamily.LEGAL, r"legal|lawyer|compliance|hukum|paralegal|notaris"),
    (
        RoleFamily.FOOD_HOSPITALITY,
        r"barista|\bcook\b|\bchef\b|kitchen|dapur|\bkoki\b|juru masak|tukang masak|waiter|waitress"
        r"|pelayan|\bserver\b|bartender|steward|dishwasher|pastry|baker|bakery|housekeep"
        r"|room attendant|hotel|restoran|restaurant|\bcafe\b|kafe|food (?:and|&) beverage|\bf ?b\b"
        r"|reservation|pramusaji|\bcake\b|\bkue\b|pariwisata",
    ),
    (
        RoleFamily.RETAIL_STORE,
        # Employer names (Indomaret, Alfamart) are not occupations, so they are not listed.
        r"kasir|cashier|pramuniaga|store|toko|shop ?keeper|\boutlet\b|merchandiser|minimarket"
        r"|retail",
    ),
    (
        RoleFamily.TRANSPORT_DELIVERY,
        r"driver|sopir|supir|kurir|courier|\brider\b|delivery|ekspedisi|pramugar|pilot|masinis"
        r"|kondektur|helper (?:driver|truck)|kereta api|kernet|kenek",
    ),
    (
        RoleFamily.PRODUCTION,
        # "Production engineer" is an engineering role, handled by the ENGINEERING rule.
        r"^(?!.*engineer).*(?:produksi|production|operator|manufactur|pabrik|factory|packing|packer"
        r"|assembly|helper)",
    ),
    (
        RoleFamily.EDUCATION,
        r"teacher|\bguru\b|tutor|pengajar|instructor|lecturer|dosen|trainer|education"
        r"|kepala sekolah|day ?care|pengasuh anak",
    ),
    (
        RoleFamily.HEALTHCARE,
        r"nurse|perawat|doctor|dokter|apoteker|pharmac|bidan|medis|medical|clinical|therap"
        r"|\bcssd\b|steril|\bipcn\b|infection|farmasi|farmasis",
    ),
    (
        RoleFamily.ENGINEERING,
        r"engineer|civil|mechanical|electrical|maintenance|teknik|sipil|mesin"
        r"|drafter|autocad|architect|technician|teknisi|machine|mekanik|mechanic|welder|surveyor"
        r"|bengkel|pelaksana (?:proyek|project|lapangan)|konstruksi|otomasi|automation",
    ),
    (
        RoleFamily.ADMIN_OPERATIONS,
        # Generic words ("staff", "assistant", "koordinator") are not occupations, and "office"
        # must not match "officer"; such titles fall through to OTHER.
        r"admin|operation|operasional|\boffice\b|secretary|sekretaris|receptionist|general affair"
        r"|\bga\b|document control|data entry|entry data|personal assistant|asisten pribadi"
        r"|resepsionis|tata usaha",
    ),
)

_COMPILED = tuple((family, re.compile(pattern)) for family, pattern in _RULES)


def classify_role_family(title: str | None) -> RoleFamily:
    key = normalize_for_matching(title)
    if not key:
        return RoleFamily.OTHER
    for family, pattern in _COMPILED:
        if pattern.search(key):
            return family
    return RoleFamily.OTHER
