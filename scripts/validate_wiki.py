#!/usr/bin/env python3
"""Validate changed Obsidian pages against the LLM-wiki archive contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from _wiki import as_string_list, contained_path, first_h1, parse_frontmatter


REQUIRED_FIELDS = ("type", "domain", "status", "tags", "aliases", "created", "updated", "sources")
LIST_FIELDS = ("domain", "tags", "aliases", "sources")
DOMAIN_INDEX = {
    "programming": "index-programming.md",
    "cs": "index-cs.md",
    "game-design": "index-game-design.md",
}
SAFE_STEM = re.compile(r"(?:[a-z0-9][a-z0-9-]*|_moc-[a-z0-9-]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--page", required=True, action="append", type=Path)
    parser.add_argument("--expected-updated", help="Require this YYYY-MM-DD updated value")
    parser.add_argument("--no-require-log", action="store_true")
    return parser.parse_args()


def validate_date(value: Any, field: str, errors: list[str]) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        errors.append(f"{field} must be an ISO date (YYYY-MM-DD)")
        return None


def wikilink_count(text: str, stem: str) -> int:
    return len(re.findall(r"\[\[" + re.escape(stem) + r"(?:\||#|\]\])", text))


def validate_page(
    vault: Path,
    path: Path,
    args: argparse.Namespace,
    index_cache: dict[str, str],
    recent_log: str,
) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    metadata, body, parse_warnings = parse_frontmatter(text)
    warnings.extend(parse_warnings)

    for field in REQUIRED_FIELDS:
        if field not in metadata:
            errors.append(f"missing frontmatter field: {field}")
    for field in LIST_FIELDS:
        if field in metadata and not isinstance(metadata[field], list):
            errors.append(f"{field} must be an inline or block list")

    if not SAFE_STEM.fullmatch(path.stem):
        errors.append("filename must be kebab-case (or _moc-kebab-case)")
    if not first_h1(body):
        errors.append("page must contain an H1 title")

    created = validate_date(metadata.get("created"), "created", errors) if "created" in metadata else None
    updated = validate_date(metadata.get("updated"), "updated", errors) if "updated" in metadata else None
    if created and updated and updated < created:
        errors.append("updated date precedes created date")
    if args.expected_updated and str(metadata.get("updated")) != args.expected_updated:
        errors.append(f"updated must equal {args.expected_updated}")

    domains = as_string_list(metadata.get("domain"))
    if not domains:
        errors.append("domain must contain at least one value")
    sources = as_string_list(metadata.get("sources"))
    status = str(metadata.get("status", ""))
    page_type = str(metadata.get("type", ""))
    if not sources and status != "stub" and page_type != "source":
        errors.append("non-stub, non-source pages must cite at least one source")

    all_index_hits = 0
    for index_name, index_text in index_cache.items():
        hits = wikilink_count(index_text, path.stem)
        all_index_hits += hits
        if hits > 1:
            warnings.append(f"{index_name} contains {hits} links to this page")
    if all_index_hits == 0:
        errors.append("page is not registered in index.md or a domain index")

    if domains:
        primary_domain = domains[0]
        index_name = DOMAIN_INDEX.get(primary_domain)
        if not index_name:
            warnings.append(f"no validator mapping for primary domain: {primary_domain}")
        elif index_name not in index_cache:
            errors.append(f"missing primary-domain index: {index_name}")
        elif wikilink_count(index_cache[index_name], path.stem) == 0:
            errors.append(f"page is not registered in primary-domain index {index_name}")

    if not args.no_require_log and wikilink_count(recent_log, path.stem) == 0:
        errors.append("recent log.md entries do not mention this page")

    return {
        "page": path.relative_to(vault).as_posix(),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    try:
        vault = args.vault.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not vault.is_dir():
        print(f"Not a vault directory: {vault}", file=sys.stderr)
        return 2
    if args.expected_updated:
        try:
            dt.date.fromisoformat(args.expected_updated)
        except ValueError:
            print("--expected-updated must be YYYY-MM-DD", file=sys.stderr)
            return 2

    index_cache: dict[str, str] = {}
    for index_path in sorted(vault.glob("index*.md")):
        if index_path.is_file() and not index_path.is_symlink():
            index_cache[index_path.name] = index_path.read_text(encoding="utf-8")
    log_path = vault / "log.md"
    if log_path.is_file() and not log_path.is_symlink():
        log_lines = log_path.read_text(encoding="utf-8").splitlines()
        recent_log = "\n".join(log_lines[-240:])
    else:
        recent_log = ""

    results: list[dict[str, object]] = []
    setup_errors: list[str] = []
    for supplied in args.page:
        candidate = supplied if supplied.is_absolute() else vault / supplied
        try:
            page = contained_path(vault, candidate)
        except (FileNotFoundError, ValueError) as exc:
            setup_errors.append(str(exc))
            continue
        if page.suffix.lower() != ".md" or not page.is_file():
            setup_errors.append(f"Not a Markdown page: {page}")
            continue
        try:
            results.append(validate_page(vault, page, args, index_cache, recent_log))
        except (OSError, UnicodeError) as exc:
            setup_errors.append(f"{page}: {exc}")

    valid = not setup_errors and bool(results) and all(bool(item["valid"]) for item in results)
    output = {
        "vault": str(vault),
        "valid": valid,
        "setup_errors": setup_errors,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
