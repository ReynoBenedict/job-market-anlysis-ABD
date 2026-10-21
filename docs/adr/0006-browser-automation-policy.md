# ADR-0006: Browser automation policy

**Status:** accepted (2026-10-17)

The legacy Selenium scraper (`legacy/academic_pipeline/scrapers/glints_scraper.py`)
collected Glints search pages while disabling automation flags and spoofing a browser
user agent. Glints' terms prohibit automated extraction without written consent.

**Decision:** no browser automation in TalentScope. The legacy script is kept for history
but exits immediately when run. A future connector may use a headless browser only if the
source's permission explicitly covers it, it identifies itself honestly, and no API or
static alternative exists. Stealth plugins, proxy rotation, CAPTCHA solving, and login
automation are never allowed (SRS §0.3).
