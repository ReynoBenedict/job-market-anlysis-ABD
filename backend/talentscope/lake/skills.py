"""Dictionary-based skill mentions in job descriptions (ADR-0011 baseline).

A mention means the phrase appears in the description; it is not proof of a formal
requirement. Patterns use word boundaries and avoid ambiguous short names ("Go", "R",
"C", "Word" alone), which would match ordinary Indonesian and English text.
Bump SKILL_DICTIONARY_VERSION whenever an entry changes; silver is then rebuilt.
"""

from __future__ import annotations

import re

SKILL_DICTIONARY_VERSION = "skills-2026.10.3"

# canonical name -> regex alternatives (lower-case, matched against lower-cased text)
_SKILLS: dict[str, str] = {
    # Programming and web
    "Python": r"python",
    "Java": r"java(?!\s*script)",
    "JavaScript": r"javascript|java script",
    "TypeScript": r"typescript",
    "PHP": r"php",
    "Laravel": r"laravel",
    "CodeIgniter": r"codeigniter",
    "Golang": r"golang",
    "C#": r"c#|c sharp",
    "C++": r"c\+\+",
    ".NET": r"\.net\b|dotnet|asp\.net",
    "Kotlin": r"kotlin",
    "Swift": r"swift",
    "Flutter": r"flutter",
    "Dart": r"dart",
    "React": r"react(?:\.?js)?(?!\s*native)",
    "React Native": r"react native",
    "Vue.js": r"vue(?:\.?js)?",
    "Angular": r"angular",
    "Node.js": r"node\.?js",
    "HTML": r"html5?",
    "CSS": r"css3?",
    "WordPress": r"wordpress",
    "REST API": r"rest(?:ful)? api",
    "Git": r"git(?!hub)|github|gitlab",
    # Data
    "SQL": r"sql",
    "MySQL": r"mysql",
    "PostgreSQL": r"postgre(?:sql|s)",
    "MongoDB": r"mongo(?:db)?",
    "Oracle Database": r"oracle(?: database| db)?",
    "Microsoft SQL Server": r"sql server|mssql",
    "Data Analysis": r"data analy(?:sis|tics)|analisis data|analisa data",
    "Power BI": r"power ?bi",
    "Tableau": r"tableau",
    "Machine Learning": r"machine learning",
    "Statistics": r"statisti(?:k|cs)",
    # Cloud and infrastructure
    "AWS": r"aws|amazon web services",
    "Google Cloud": r"google cloud|gcp",
    "Microsoft Azure": r"azure",
    "Docker": r"docker",
    "Kubernetes": r"kubernetes|k8s",
    "Linux": r"linux",
    "Networking": r"jaringan komputer|computer network(?:ing)?|mikrotik|cisco",
    # Office and business tools
    "Microsoft Excel": r"(?:ms\.?|microsoft) excel|excel",
    "Microsoft Word": r"(?:ms\.?|microsoft) word",
    "Microsoft PowerPoint": r"powerpoint|power point",
    "Microsoft Office": r"(?:ms\.?|microsoft) office",
    "Google Workspace": r"google (?:workspace|sheets?|docs)",
    "SAP": r"sap",
    "Accurate": r"accurate",
    "Zahir": r"zahir",
    "Jurnal.id": r"jurnal\.id",
    "Accounting": r"akuntansi|accounting",
    "Taxation": r"perpajakan|brevet|taxation",
    "AutoCAD": r"autocad|auto cad",
    "SketchUp": r"sketch ?up",
    # Design and media
    "Adobe Photoshop": r"photoshop",
    "Adobe Illustrator": r"illustrator",
    "Adobe Premiere": r"premiere",
    "CorelDRAW": r"corel ?draw",
    "Figma": r"figma",
    "Canva": r"canva",
    "Video Editing": r"video editing|edit(?:ing)? video",
    "Copywriting": r"copywriting",
    # Marketing and sales
    "SEO": r"seo",
    "Social Media Marketing": r"social media|media sosial",
    "Digital Marketing": r"digital marketing|pemasaran digital",
    "Google Ads": r"google ads|adwords",
    "Facebook Ads": r"facebook ads|meta ads",
    "Customer Service": r"customer service|pelayanan pelanggan",
    "Negotiation": r"negosiasi|negotiation",
    # Languages and general
    "English": r"bahasa inggris|english",
    "Mandarin": r"mandarin",
    "Japanese": r"bahasa jepang|japanese",
    # "jaringan komunikasi" is a communications network, not a skill (reviewed sample).
    "Communication": r"(?<!jaringan )komunikasi|communication skills?",
    "Leadership": r"kepemimpinan|leadership",
    "Teamwork": r"kerja ?sama tim|teamwork|team work",
    "Driving License (SIM)": r"\bsim [abc]\d?\b|surat izin mengemudi",
}

# The left boundary is checked in Python rather than with a leading lookbehind: a regex
# that starts with a lookbehind is tried at every position, which made skill matching
# most of silver's parse time. Same matches, about 4x faster on real descriptions.
_PATTERNS = [(name, re.compile(rf"(?:{pattern})(?![\w+#])")) for name, pattern in _SKILLS.items()]
_WORDLIKE = re.compile(r"[\w.+#]")

# Skills that are also degree majors. A match right after a degree marker ("S1 Bahasa
# Inggris", "jurusan Akuntansi") names a field of study, not a skill, and is ignored.
_MAJOR_LIKE = frozenset({"English", "Communication", "Accounting", "Taxation", "Statistics"})
_DEGREE_CONTEXT = re.compile(
    r"\b(?:s1|s2|s3|d1|d2|d3|d4|sarjana|diploma|jurusan|prodi|program studi|bidang studi|"
    r"mata pelajaran|lulusan|pendidikan)\b[^.;]{0,40}$"
)


def _is_skill_mention(name: str, pattern: re.Pattern[str], text: str) -> bool:
    position = 0
    while (match := pattern.search(text, position)) is not None:
        start = match.start()
        if start == 0 or not _WORDLIKE.match(text[start - 1]):
            preceding = text[max(0, start - 60) : start]
            if name not in _MAJOR_LIKE or not _DEGREE_CONTEXT.search(preceding):
                return True
        position = start + 1
    return False


def extract_skills(text: str | None) -> list[str]:
    """Canonical skill names mentioned in ``text``, in dictionary order, without repeats."""
    if not text:
        return []
    lowered = text.lower()
    return [name for name, pattern in _PATTERNS if _is_skill_mention(name, pattern, lowered)]


def dictionary_size() -> int:
    return len(_SKILLS)
