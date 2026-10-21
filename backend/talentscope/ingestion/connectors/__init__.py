"""Connector construction from a source's registry entry."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from talentscope.config import get_settings
from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.connectors.lake_vacancies import LakeVacancies
from talentscope.ingestion.connectors.legacy_glints_csv import LegacyGlintsSnapshot
from talentscope.ingestion.connectors.lever import LeverPostings
from talentscope.ingestion.http import PoliteClient
from talentscope.models import Source


class ConnectorConfigError(ValueError):
    pass


def build_connector(source: Source, *, client: PoliteClient | None = None) -> Connector:
    """Instantiate the adapter named in ``source.connector`` with its stored config."""
    config = source.connector_config or {}
    try:
        if source.connector == LegacyGlintsSnapshot.name:
            return LegacyGlintsSnapshot(
                Path(config["path"]), datetime.fromisoformat(config["observed_at"])
            )
        if source.connector == LakeVacancies.name:
            path = get_settings().lake_dir / "silver" / "vacancies.parquet"
            if not path.exists():
                raise ConnectorConfigError(f"{path} not found; run `talentscope lake silver` first")
            return LakeVacancies(path, source.id)
        if source.connector == LeverPostings.name:
            if client is None:
                raise ConnectorConfigError("network connectors need an HTTP client")
            return LeverPostings(
                client,
                site=config["site"],
                company_name=config["company_name"],
                max_pages=int(config.get("max_pages", 20)),
                store_description=bool(config.get("store_description", False)),
            )
    except KeyError as exc:
        raise ConnectorConfigError(f"source {source.id!r} config is missing {exc}") from exc
    raise ConnectorConfigError(
        f"source {source.id!r} has no usable connector ({source.connector!r})"
    )
