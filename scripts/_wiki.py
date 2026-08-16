#!/usr/bin/env python3
"""Small, dependency-free helpers shared by the wiki scripts."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from pathlib import Path
from typing import Any


FRONTMATTER_BOUNDARY = "---"
ASCII_STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "vs", "with"}


def contained_path(root: Path, candidate: Path) -> Path:
    """Resolve candidate and reject paths outside root."""
    resolved_root = root.expanduser().resolve(strict=True)
    resolved = candidate.expanduser().resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes vault: {candidate}") from exc
    return resolved


def parse_inline_list(value: str) -> list[str] | None:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    reader = csv.reader(io.StringIO(inner), skipinitialspace=True)
    return [item.strip().strip("'\"") for item in next(reader)]


def parse_scalar(value: str) -> Any:
    value = value.strip()
    inline = parse_inline_list(value)
    if inline is not None:
        return inline
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value.strip("'\"")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, list[str]]:
    """Parse the vault's flat YAML subset and return metadata, body, warnings."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_BOUNDARY:
        return {}, text, ["missing frontmatter boundary"]

    try:
        end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_BOUNDARY
        )
    except StopIteration:
        return {}, text, ["unclosed frontmatter"]

    metadata: dict[str, Any] = {}
    warnings: list[str] = []
    current_list: str | None = None
    for line_number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item_match = re.match(r"^\s+-\s+(.+?)\s*$", raw)
        if item_match and current_list:
            value = item_match.group(1).strip().strip("'\"")
            metadata.setdefault(current_list, []).append(value)
            continue
        field_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", raw)
        if not field_match:
            warnings.append(f"unparsed frontmatter line {line_number}: {raw}")
            current_list = None
            continue
        key, raw_value = field_match.groups()
        raw_value = raw_value or ""
        if not raw_value.strip():
            metadata[key] = []
            current_list = key
        else:
            metadata[key] = parse_scalar(raw_value)
            current_list = None

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return metadata, body, warnings


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[/_.-]+", " ", value)
    value = re.sub(r"[^\w\u3400-\u9fff]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def tokens(value: str) -> set[str]:
    normalized = normalize(value)
    found = {
        token
        for token in normalized.split()
        if not (token.isascii() and token in ASCII_STOPWORDS)
    }
    for cjk_span in re.findall(r"[\u3400-\u9fff]+", normalized):
        found.update(cjk_span[index : index + 2] for index in range(len(cjk_span) - 1))
    return {token for token in found if token}


def first_h1(body: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return ""


def as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in {None, ""}:
        return []
    return [str(value)]
