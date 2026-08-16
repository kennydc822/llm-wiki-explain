#!/usr/bin/env python3
"""Rank candidate Obsidian pages for a term without modifying the vault."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _wiki import (
    as_string_list,
    contained_path,
    first_h1,
    normalize,
    parse_frontmatter,
    tokens,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--domain", help="Only return pages with this frontmatter domain")
    return parser.parse_args()


def field_score(query: str, query_tokens: set[str], label: str, value: str) -> tuple[int, list[str]]:
    normalized = normalize(value)
    if not normalized:
        return 0, []
    if normalized == query:
        return 100, [f"exact {label}"]
    score = 0
    reasons: list[str] = []
    if query in normalized:
        score += 48
        reasons.append(f"{label} phrase match")
    elif len(normalized) >= 4 and normalized in query:
        score += 36
        reasons.append(f"{label} narrower phrase match")
    overlap = query_tokens & tokens(value)
    if overlap:
        ratio = len(overlap) / max(len(query_tokens), 1)
        score += round(32 * ratio)
        reasons.append(f"{label} token overlap")
    return score, reasons


def main() -> int:
    args = parse_args()
    if not args.query.strip():
        print("--query must not be empty", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 100:
        print("--limit must be between 1 and 100", file=sys.stderr)
        return 2

    try:
        vault = args.vault.expanduser().resolve(strict=True)
        wiki_root = contained_path(vault, vault / "wiki")
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not wiki_root.is_dir():
        print(f"Not a wiki directory: {wiki_root}", file=sys.stderr)
        return 2

    index_text = ""
    for index_path in sorted(vault.glob("index*.md")):
        if index_path.is_file() and not index_path.is_symlink():
            index_text += "\n" + index_path.read_text(encoding="utf-8")

    query = normalize(args.query)
    query_tokens = tokens(args.query)
    matches: list[dict[str, object]] = []
    skipped: list[str] = []

    for unresolved in sorted(wiki_root.rglob("*.md")):
        if unresolved.is_symlink() or any(part.startswith("_") for part in unresolved.relative_to(wiki_root).parts[:-1]):
            continue
        try:
            path = contained_path(vault, unresolved)
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError) as exc:
            skipped.append(f"{unresolved}: {exc}")
            continue

        metadata, body, parse_warnings = parse_frontmatter(text)
        domains = as_string_list(metadata.get("domain"))
        if args.domain and args.domain not in domains:
            continue
        title = first_h1(body)
        aliases = as_string_list(metadata.get("aliases"))
        stem = path.stem

        candidates = [("filename", stem), ("title", title)]
        candidates.extend(("alias", alias) for alias in aliases)
        scored = [field_score(query, query_tokens, label, value) for label, value in candidates]
        best_score, best_reasons = max(scored, key=lambda item: item[0], default=(0, []))
        score = best_score
        reasons = list(best_reasons)

        normalized_body = normalize(body)
        if query and query in normalized_body:
            occurrences = normalized_body.count(query)
            score += min(18, 6 + occurrences)
            reasons.append("body phrase match")
        else:
            body_overlap = query_tokens & tokens(body)
            if body_overlap:
                score += min(10, len(body_overlap) * 3)
                reasons.append("body token overlap")

        wikilink = f"[[{stem}]]"
        if score > 0 and (wikilink in index_text or f"[[{stem}|" in index_text):
            score += 12
            reasons.append("indexed page")
        if str(metadata.get("status", "")) == "stub":
            score -= 8
            reasons.append("stub penalty")

        if score <= 0:
            continue
        matches.append(
            {
                "path": path.relative_to(vault).as_posix(),
                "wikilink": wikilink,
                "title": title or stem,
                "type": metadata.get("type"),
                "domain": domains,
                "status": metadata.get("status"),
                "aliases": aliases,
                "score": score,
                "reasons": reasons,
                "parse_warnings": parse_warnings,
            }
        )

    matches.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    result = {
        "query": args.query,
        "domain": args.domain,
        "vault": str(vault),
        "match_count": len(matches),
        "matches": matches[: args.limit],
        "skipped": skipped,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
