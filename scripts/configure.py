#!/usr/bin/env python3
"""Discover and persist per-user LLM Wiki Explain configuration."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


CONFIG_VERSION = 1
CONFIG_ENV = "LLM_WIKI_EXPLAIN_CONFIG"
NAME_CUES = ("wiki", "vault", "knowledge", "notes", "obsidian")


def default_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "llm-wiki-explain" / "config.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Override the per-user config path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show", help="Show the current config and validation status")
    subparsers.add_parser("validate", help="Validate the current config")

    discover = subparsers.add_parser("discover", help="Find likely local Obsidian or LLM wikis")
    discover.add_argument("--root", action="append", type=Path, help="Bounded root to scan; repeatable")
    discover.add_argument("--max-depth", type=int, default=4)
    discover.add_argument("--limit", type=int, default=10)

    obsidian = subparsers.add_parser("set-obsidian", help="Save a confirmed local wiki")
    obsidian.add_argument("--vault", required=True, type=Path)
    obsidian.add_argument("--project-label")
    obsidian.add_argument(
        "--allow-unindexed",
        action="store_true",
        help="Allow a confirmed Obsidian vault without index.md",
    )

    notion = subparsers.add_parser("set-notion", help="Save a confirmed Notion wiki target")
    notion.add_argument("--target", required=True)
    return parser.parse_args()


def output(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def config_path(args: argparse.Namespace) -> Path:
    return (args.config or default_config_path()).expanduser()


def read_config(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    if path.is_symlink():
        return None, "refusing to read a symlinked config file"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"cannot read config: {exc}"
    if not isinstance(data, dict):
        return None, "config root must be a JSON object"
    return data, None


def detect_schema(vault: Path) -> str:
    programming_markers = (
        vault / "CLAUDE.md",
        vault / "index.md",
        vault / "index-programming.md",
        vault / "index-cs.md",
        vault / "index-game-design.md",
    )
    if all(marker.is_file() for marker in programming_markers):
        return "programming-vault"
    if (vault / "index.md").is_file() and any(
        (vault / name).is_file() for name in ("CLAUDE.md", "AGENTS.md")
    ):
        return "instructed-indexed"
    if (vault / "index.md").is_file():
        return "indexed-markdown"
    if (vault / ".obsidian").is_dir():
        return "unindexed-obsidian"
    return "unknown"


def validate_config(data: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data is None:
        return ["config is missing"], warnings
    if data.get("version") != CONFIG_VERSION:
        errors.append(f"version must equal {CONFIG_VERSION}")

    backend = data.get("backend")
    if backend == "obsidian":
        settings = data.get("obsidian")
        if not isinstance(settings, dict):
            return errors + ["obsidian settings must be an object"], warnings
        raw_path = settings.get("vault_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return errors + ["obsidian.vault_path is required"], warnings
        vault = Path(raw_path).expanduser()
        if not vault.exists():
            errors.append(f"configured vault does not exist: {vault}")
        elif not vault.is_dir():
            errors.append(f"configured vault is not a directory: {vault}")
        else:
            resolved = vault.resolve()
            schema = detect_schema(resolved)
            if schema == "unknown":
                errors.append("configured path does not look like an Obsidian or indexed Markdown wiki")
            elif schema == "unindexed-obsidian":
                if not settings.get("allow_unindexed"):
                    errors.append("configured Obsidian vault has no index.md")
                else:
                    warnings.append("vault is unindexed; keep archive writes disabled until rules are defined")
            stored_schema = settings.get("schema")
            if stored_schema and stored_schema != schema:
                warnings.append(f"detected schema changed from {stored_schema} to {schema}")
    elif backend == "notion":
        settings = data.get("notion")
        if not isinstance(settings, dict):
            return errors + ["notion settings must be an object"], warnings
        target = settings.get("target")
        if not isinstance(target, str) or not target.strip():
            errors.append("notion.target is required")
        warnings.append("connector availability must be verified at runtime")
    else:
        errors.append("backend must be obsidian or notion")
    return errors, warnings


def write_config(path: Path, data: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError("refusing to overwrite a symlinked config file")
    parent = path.parent.expanduser()
    parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=parent,
            prefix="config.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_name = handle.name
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()


def default_discovery_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Documents",
        home / "Obsidian",
        home / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents",
    ]
    roots: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError):
            continue
        if resolved.is_dir() and resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)
    return roots


def candidate_details(path: Path) -> dict[str, Any] | None:
    markers: list[str] = []
    score = 0
    if (path / "index.md").is_file():
        markers.append("index.md")
        score += 50
    if (path / "CLAUDE.md").is_file():
        markers.append("CLAUDE.md")
        score += 30
    elif (path / "AGENTS.md").is_file():
        markers.append("AGENTS.md")
        score += 25
    if (path / ".obsidian").is_dir():
        markers.append(".obsidian")
        score += 20
    if any(cue in path.name.casefold() for cue in NAME_CUES):
        markers.append("name cue")
        score += 10
    if not markers or ("index.md" not in markers and ".obsidian" not in markers):
        return None
    return {
        "path": str(path),
        "score": score,
        "schema": detect_schema(path),
        "markers": markers,
    }


def discover(roots: list[Path], max_depth: int, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    found: dict[Path, dict[str, Any]] = {}
    scan_errors: list[str] = []

    def on_error(exc: OSError) -> None:
        scan_errors.append(str(exc))

    for supplied in roots:
        try:
            root = supplied.expanduser().resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            scan_errors.append(f"{supplied}: {exc}")
            continue
        if not root.is_dir():
            scan_errors.append(f"not a directory: {root}")
            continue
        for current, dirs, _files in os.walk(root, topdown=True, followlinks=False, onerror=on_error):
            path = Path(current)
            depth = len(path.relative_to(root).parts)
            if depth >= max_depth:
                dirs[:] = []
            else:
                dirs[:] = [
                    name
                    for name in dirs
                    if not name.startswith(".")
                    and name not in {"node_modules", "Library", "vendor", "venv"}
                    and not (path / name).is_symlink()
                ]
            details = candidate_details(path)
            if details:
                found[path] = details

    matches = sorted(found.values(), key=lambda item: (-int(item["score"]), str(item["path"])))
    return matches[:limit], scan_errors


def cmd_show(args: argparse.Namespace) -> int:
    path = config_path(args)
    data, read_error = read_config(path)
    if read_error:
        output({"configured": False, "valid": False, "config_path": str(path), "errors": [read_error]})
        return 1
    errors, warnings = validate_config(data)
    output(
        {
            "configured": data is not None,
            "valid": not errors,
            "config_path": str(path),
            "config": data,
            "errors": errors,
            "warnings": warnings,
        }
    )
    return 0 if data is not None and not errors else 1


def cmd_validate(args: argparse.Namespace) -> int:
    return cmd_show(args)


def cmd_discover(args: argparse.Namespace) -> int:
    if args.max_depth < 0 or args.max_depth > 12:
        print("--max-depth must be between 0 and 12", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 100:
        print("--limit must be between 1 and 100", file=sys.stderr)
        return 2
    roots = args.root or default_discovery_roots()
    matches, errors = discover(roots, args.max_depth, args.limit)
    output(
        {
            "roots": [str(root.expanduser()) for root in roots],
            "candidate_count": len(matches),
            "candidates": matches,
            "scan_errors": errors,
        }
    )
    return 0


def cmd_set_obsidian(args: argparse.Namespace) -> int:
    try:
        vault = args.vault.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        print(f"cannot resolve vault: {exc}", file=sys.stderr)
        return 2
    if not vault.is_dir():
        print(f"vault is not a directory: {vault}", file=sys.stderr)
        return 2
    schema = detect_schema(vault)
    if schema == "unknown":
        print("path does not look like an Obsidian or indexed Markdown wiki", file=sys.stderr)
        return 2
    if schema == "unindexed-obsidian" and not args.allow_unindexed:
        print("vault has no index.md; confirm and pass --allow-unindexed to save it", file=sys.stderr)
        return 2
    data = {
        "version": CONFIG_VERSION,
        "backend": "obsidian",
        "obsidian": {
            "vault_path": str(vault),
            "project_label": args.project_label or vault.name,
            "schema": schema,
            "allow_unindexed": bool(args.allow_unindexed),
        },
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    errors, warnings = validate_config(data)
    if errors:
        output({"saved": False, "errors": errors, "warnings": warnings})
        return 2
    path = config_path(args)
    try:
        write_config(path, data)
    except (OSError, ValueError) as exc:
        print(f"cannot write config: {exc}", file=sys.stderr)
        return 2
    output({"saved": True, "config_path": str(path), "config": data, "warnings": warnings})
    return 0


def cmd_set_notion(args: argparse.Namespace) -> int:
    target = args.target.strip()
    if not target:
        print("--target must not be empty", file=sys.stderr)
        return 2
    data = {
        "version": CONFIG_VERSION,
        "backend": "notion",
        "notion": {"target": target},
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    path = config_path(args)
    try:
        write_config(path, data)
    except (OSError, ValueError) as exc:
        print(f"cannot write config: {exc}", file=sys.stderr)
        return 2
    output(
        {
            "saved": True,
            "config_path": str(path),
            "config": data,
            "warnings": ["connector availability must be verified at runtime"],
        }
    )
    return 0


def main() -> int:
    args = parse_args()
    handlers = {
        "show": cmd_show,
        "validate": cmd_validate,
        "discover": cmd_discover,
        "set-obsidian": cmd_set_obsidian,
        "set-notion": cmd_set_notion,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
