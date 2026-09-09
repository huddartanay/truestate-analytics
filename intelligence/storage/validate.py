"""
Streaming JSONL validator.

    python -m intelligence.storage.validate <jsonl-file>
    python -m intelligence.storage.validate --day 2026-09-07
    python -m intelligence.storage.validate --json <file>

Reads line-by-line, never loads the file into memory. Parses each line as
JSON, validates as RawArticleRecord, reports counts and per-failure line
numbers, exits non-zero if any record is invalid. Does not modify the file.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from intelligence.errors import RawPathViolation
from intelligence.storage.raw import (
    _parse_and_validate, resolve_raw_path, open_raw_read,
)
from intelligence.storage.rotation import day_partitions


@dataclass
class ValidationResult:
    file: str
    total_lines: int = 0
    blank_lines: int = 0
    valid: int = 0
    malformed_json: int = 0
    schema_failures: int = 0
    failures: list[tuple[int, str]] = field(default_factory=list)  # (line_no, message)


def validate_file(path: Path) -> ValidationResult:
    result = ValidationResult(file=str(path))
    with open_raw_read(path) as fh:
        for lineno, raw in enumerate(fh, start=1):
            result.total_lines += 1
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                result.blank_lines += 1
                continue
            try:
                # Distinguish JSON errors from schema errors for reporting
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                result.malformed_json += 1
                result.failures.append((lineno, f"JSON: {e.msg} at col {e.colno}"))
                continue
            try:
                # Reuse the same validator the read helpers use
                _parse_and_validate(path, lineno, json.dumps(obj))  # already parsed once above
                result.valid += 1
            except Exception as e:
                result.schema_failures += 1
                result.failures.append((lineno, f"schema: {str(e)[:160]}"))
    return result


def _print(result: ValidationResult) -> None:
    print(f"File: {result.file}")
    print(f"  total lines:       {result.total_lines}")
    print(f"  blank lines:       {result.blank_lines}")
    print(f"  valid records:     {result.valid}")
    print(f"  malformed JSON:    {result.malformed_json}")
    print(f"  schema failures:   {result.schema_failures}")
    if result.failures:
        print("  Failures:")
        for lineno, msg in result.failures[:40]:
            print(f"    line {lineno}: {msg}")
        if len(result.failures) > 40:
            print(f"    ... {len(result.failures) - 40} more")


def _print_json(results: Iterable[ValidationResult]) -> None:
    payload = [
        {
            "file":              r.file,
            "total_lines":       r.total_lines,
            "blank_lines":       r.blank_lines,
            "valid_records":     r.valid,
            "malformed_json":    r.malformed_json,
            "schema_failures":   r.schema_failures,
            "failures":          [{"line": lno, "message": msg} for lno, msg in r.failures],
        }
        for r in results
    ]
    print(json.dumps(payload, indent=2))


def _resolve_targets(args: argparse.Namespace) -> list[Path]:
    """Path-safe target resolution — CLI file arguments cannot escape the raw root."""
    targets: list[Path] = []
    if args.day:
        for p in day_partitions(args.day):
            targets.append(p)
    for f in args.files:
        targets.append(resolve_raw_path(f))
    return targets


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="intelligence.storage.validate",
        description="Streaming validator for raw JSONL articles.",
    )
    ap.add_argument("files", nargs="*", help="JSONL paths (must live under raw storage root).")
    ap.add_argument("--day", help="Validate every partition for YYYY-MM-DD.")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args(list(argv) if argv is not None else None)

    try:
        targets = _resolve_targets(args)
    except RawPathViolation as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if not targets:
        print("No files to validate. Pass file paths or --day YYYY-MM-DD.", file=sys.stderr)
        return 2

    results = [validate_file(p) for p in targets]

    if args.json:
        _print_json(results)
    else:
        for r in results:
            _print(r)

    invalid = sum(r.malformed_json + r.schema_failures for r in results)
    return 0 if invalid == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
