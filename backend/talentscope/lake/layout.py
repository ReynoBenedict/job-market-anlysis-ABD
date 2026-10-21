from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Lake:
    """Directory layout of the lake. Everything lives under one root (``LAKE_DIR``).

    bronze/  append-only raw observations, partitioned by source and crawl/batch
    silver/  rebuilt from bronze: parsed observations, source records, vacancies
    gold/    rebuilt from silver: analytics tables and the data-quality report
    state/   checkpoints (per-domain yield, crawl progress)
    synthetic/  benchmark-only data, never read by silver or gold
    """

    root: Path

    @property
    def bronze(self) -> Path:
        return self.root / "bronze"

    @property
    def silver(self) -> Path:
        return self.root / "silver"

    @property
    def gold(self) -> Path:
        return self.root / "gold"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def synthetic(self) -> Path:
        return self.root / "synthetic"

    def cc_candidates(self, crawl: str) -> Path:
        return self.bronze / "commoncrawl" / "candidates" / f"crawl={crawl}" / "candidates.parquet"

    def cc_captures_dir(self, crawl: str) -> Path:
        return self.bronze / "commoncrawl" / "captures" / f"crawl={crawl}"

    def ensure(self) -> None:
        for path in (self.bronze, self.silver, self.gold, self.state):
            path.mkdir(parents=True, exist_ok=True)
