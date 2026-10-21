"""Extract schema.org JobPosting objects from JSON-LD blocks in an HTML page."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

_LD_BLOCK = re.compile(
    rb"<script[^>]*type\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_CDATA = re.compile(r"^\s*(?://\s*)?<!\[CDATA\[|(?://\s*)?\]\]>\s*$")


def _iter_nodes(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from _iter_nodes(item)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _iter_nodes(node["@graph"])


def _is_job_posting(node: dict[str, Any]) -> bool:
    types = node.get("@type")
    names = types if isinstance(types, list) else [types]
    return any(isinstance(name, str) and name.rsplit("/", 1)[-1] == "JobPosting" for name in names)


def extract_job_postings(html: bytes) -> tuple[list[dict[str, Any]], int]:
    """Return (JobPosting objects, number of JSON-LD blocks that failed to parse).

    Malformed blocks are counted rather than repaired: guessing at broken JSON would risk
    attributing fields to the wrong object.
    """
    postings: list[dict[str, Any]] = []
    malformed = 0
    for raw_block in _LD_BLOCK.findall(html):
        text = _CDATA.sub("", raw_block.decode("utf-8", "replace")).strip()
        if not text:
            continue
        try:
            # strict=False accepts raw newlines/tabs inside strings, common in descriptions.
            data = json.loads(text, strict=False)
        except json.JSONDecodeError:
            malformed += 1
            continue
        postings.extend(node for node in _iter_nodes(data) if _is_job_posting(node))
    return postings, malformed
