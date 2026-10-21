from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

# Attributes every LogRecord has; anything else was passed via `extra=` and is context.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        context = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        return f"{base} {context}" if context else base


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter()
        if fmt == "json"
        else TextFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # One INFO line per HTTP request drowns out pipeline logs during archive collection.
    logging.getLogger("httpx").setLevel(logging.WARNING)
