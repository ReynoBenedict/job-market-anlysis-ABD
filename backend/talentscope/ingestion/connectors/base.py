from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from typing import ClassVar, Literal

from talentscope.ingestion.records import SalaryConvention, SourceJob


class Connector(ABC):
    """A source adapter: knows how to retrieve and parse one kind of source.

    Connectors only produce ``SourceJob`` values. Policy checks, normalization,
    deduplication, persistence, and run bookkeeping belong to the shared pipeline, so a
    connector cannot bypass them and one connector's failure cannot affect another.
    """

    #: Key stored in ``sources.connector``.
    name: ClassVar[str]
    #: Bump when parsing changes so stored records show which parser produced them.
    parser_version: ClassVar[str]
    #: "import" reads a local file; "collect" makes network requests.
    mode: ClassVar[Literal["import", "collect"]]
    salary_convention: ClassVar[SalaryConvention | None] = None
    #: True when each run delivers the source's complete current content (a rebuilt
    #: snapshot). The pipeline then applies the run in a single transaction, all or
    #: nothing, and removes the source's records the snapshot no longer contains.
    replaces_snapshot: ClassVar[bool] = False

    @abstractmethod
    def describe_input(self) -> str:
        """Human-readable description of what is read (file + checksum, or endpoint)."""

    @abstractmethod
    def observed_at(self) -> datetime:
        """When the returned data was observed at the source."""

    @abstractmethod
    def fetch(self) -> Iterator[SourceJob]:
        """Yield jobs. Raise a ``ConnectorError`` subclass when the run must stop."""

    def current_keys(self) -> set[str]:
        """Source keys of the complete snapshot (only for ``replaces_snapshot``)."""
        raise NotImplementedError(f"{self.name} does not deliver complete snapshots")
