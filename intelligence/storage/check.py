"""
Integrity checker — reconciles JSONL raw records with article_sightings.

    python -m intelligence.storage.check
    python -m intelligence.storage.check --json

Detects, for every article_sightings row:
    - missing JSONL file             (file listed in pointer not on disk)
    - path violation                 (pointer resolves outside the raw root)
    - line beyond EOF                (raw_jsonl_line > file's line count)
    - invalid JSON at pointer
    - invalid RawArticleRecord at pointer
    - article_id mismatch
    - raw_hash mismatch
    - source_id mismatch
    - duplicate pointer              (two sightings share the same file+line)

Also detects:
    - orphan JSONL record            (JSONL line with no article_sightings row)

Read-only: NEVER modifies JSONL or SQLite. Exits non-zero when discrepancies
are found.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from intelligence import config as _cfg
from intelligence.db.connection import connect_ro
from intelligence.errors import RawPathViolation
from intelligence.schemas import RawArticleRecord
from intelligence.storage.raw import _read_specific_line, resolve_raw_path, open_raw_read


@dataclass
class Issue:
    kind: str                       # e.g. "MISSING_FILE"
    sighting_id: str | None
    path: str | None
    line: int | None
    detail: str


@dataclass
class CheckReport:
    sightings_checked: int = 0
    jsonl_lines_scanned: int = 0
    issues: list[Issue] = field(default_factory=list)


def _record_pointer_key(path_str: str, line: int) -> str:
    return f"{path_str}#{line}"


def run_check() -> CheckReport:
    report = CheckReport()
    raw_root = _cfg.RAW_ARTICLES_DIR

    # ── 1. Build the set of (path, line) pointers from article_sightings ──
    with connect_ro() as conn:
        rows = conn.execute(
            "SELECT sighting_id, source_id, article_id, raw_hash, "
            "       raw_jsonl_path, raw_jsonl_line FROM article_sightings"
        ).fetchall()

    seen_pointer: dict[str, str] = {}   # pointer_key → sighting_id (for dup detection)
    referenced: dict[str, set[int]] = defaultdict(set)  # path -> set of referenced lines
    file_cache: dict[str, list[str]] = {}  # path -> list of lines (loaded once per file)

    for row in rows:
        report.sightings_checked += 1
        sid = row["sighting_id"]
        path_str = row["raw_jsonl_path"]
        lineno = int(row["raw_jsonl_line"])

        # ── path safety ──
        try:
            path = resolve_raw_path(path_str)
        except RawPathViolation as e:
            report.issues.append(Issue("PATH_VIOLATION", sid, path_str, lineno, str(e)))
            continue

        if not path.exists():
            report.issues.append(Issue("MISSING_FILE", sid, path_str, lineno, "file not on disk"))
            continue

        # ── duplicate pointer ──
        key = _record_pointer_key(str(path), lineno)
        if key in seen_pointer:
            report.issues.append(Issue(
                "DUPLICATE_POINTER", sid, path_str, lineno,
                f"also referenced by sighting {seen_pointer[key]}",
            ))
        else:
            seen_pointer[key] = sid
        referenced[str(path)].add(lineno)

        # ── lazy load the target file ──
        if str(path) not in file_cache:
            with open_raw_read(path) as fh:
                file_cache[str(path)] = [l.rstrip("\n").rstrip("\r") for l in fh.readlines()]
        lines = file_cache[str(path)]
        if lineno < 1 or lineno > len(lines):
            report.issues.append(Issue(
                "LINE_BEYOND_EOF", sid, path_str, lineno,
                f"file has {len(lines)} lines",
            ))
            continue

        line = lines[lineno - 1]
        if not line.strip():
            report.issues.append(Issue(
                "BLANK_POINTER_LINE", sid, path_str, lineno,
                "pointer resolves to a blank line",
            ))
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            report.issues.append(Issue(
                "INVALID_JSON", sid, path_str, lineno, f"{e.msg} at col {e.colno}",
            ))
            continue

        try:
            record = RawArticleRecord.model_validate(obj)
        except Exception as e:
            report.issues.append(Issue(
                "SCHEMA_INVALID", sid, path_str, lineno, f"schema validation failed ({type(e).__name__})",
            ))
            continue

        if record.article_id != row["article_id"]:
            report.issues.append(Issue(
                "ARTICLE_ID_MISMATCH", sid, path_str, lineno,
                f"sighting={row['article_id']} vs record={record.article_id}",
            ))
        if record.raw_hash != row["raw_hash"]:
            report.issues.append(Issue(
                "RAW_HASH_MISMATCH", sid, path_str, lineno,
                f"sighting={row['raw_hash'][:12]}... vs record={record.raw_hash[:12]}...",
            ))
        if record.source_id != row["source_id"]:
            report.issues.append(Issue(
                "SOURCE_ID_MISMATCH", sid, path_str, lineno,
                f"sighting={row['source_id']} vs record={record.source_id}",
            ))

    # ── 2. Orphan detection — JSONL lines with no article_sightings row ──
    # Resolve iterdir() paths to canonical form so they match the DB pointers
    # already resolved through `resolve_raw_path()`. This fixes the macOS
    # /var → /private/var symlink discrepancy.
    if raw_root.exists():
        for path in raw_root.iterdir():
            if path.suffix != ".jsonl" or not path.is_file():
                continue
            try:
                canon = str(resolve_raw_path(path))
            except RawPathViolation as exc:
                report.issues.append(Issue('PATH_VIOLATION', None, str(path), None, str(exc)))
                continue
            with open_raw_read(path) as fh:
                for lineno, line in enumerate(fh, start=1):
                    report.jsonl_lines_scanned += 1
                    if not line.strip():
                        continue
                    if lineno not in referenced.get(canon, set()):
                        report.issues.append(Issue(
                            "ORPHAN_RECORD", None, str(path), lineno,
                            "JSONL line has no article_sightings pointer",
                        ))

    return report


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────────────────────


def _print(report: CheckReport) -> None:
    print(f"Sightings checked:   {report.sightings_checked}")
    print(f"JSONL lines scanned: {report.jsonl_lines_scanned}")
    print(f"Issues found:        {len(report.issues)}")
    if not report.issues:
        print("OK — JSONL and article_sightings agree.")
        return
    by_kind: dict[str, int] = defaultdict(int)
    for i in report.issues:
        by_kind[i.kind] += 1
    print()
    print("By kind:")
    for kind, n in sorted(by_kind.items()):
        print(f"  {kind:<24} {n}")
    print()
    print("Sample issues (first 20):")
    for issue in report.issues[:20]:
        loc = f"{issue.path}:{issue.line}" if issue.path else "-"
        print(f"  [{issue.kind:<22}] {loc}  {issue.detail}")
    if len(report.issues) > 20:
        print(f"  ... {len(report.issues) - 20} more")


def _print_json(report: CheckReport) -> None:
    payload = {
        "sightings_checked":  report.sightings_checked,
        "jsonl_lines_scanned": report.jsonl_lines_scanned,
        "issue_count":         len(report.issues),
        "issues": [
            {"kind": i.kind, "sighting_id": i.sighting_id,
             "path": i.path, "line": i.line, "detail": i.detail}
            for i in report.issues
        ],
    }
    print(json.dumps(payload, indent=2))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="intelligence.storage.check",
        description="Reconcile raw JSONL against article_sightings.",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(list(argv) if argv is not None else None)

    report = run_check()
    if args.json:
        _print_json(report)
    else:
        _print(report)
    return 0 if not report.issues else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
