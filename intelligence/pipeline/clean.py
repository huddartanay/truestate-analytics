"""Offline Stage 6 orchestration with record-level failure isolation.

This boundary reuses Stage 5's line reader, schema parser, path guard and
partition index for its own detailed counters. Stage 5 also exposes optional
error callbacks for callers that need record-level continuation.
No raw directory is created, no raw file is opened for writing.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from intelligence import config as _cfg
from intelligence.cleaning.clean import clean_article
from intelligence.db.cleaning import already_cleaned, ensure_cleaning_schema, save_clean_article
from intelligence.db.connection import connect_rw
from intelligence.db.runs import pipeline_guard, reconcile_stale_runs, register_run
from intelligence.errors import CleaningError, DatabaseError, RawPathViolation
from intelligence.storage.raw import _iter_lines, _parse_and_validate, resolve_raw_path
from intelligence.storage.rotation import _partition_index

MAX_ERROR_DETAILS = 100


@dataclass
class CleaningReport:
    run_id: str
    started_at: str
    cleaning_version: str
    since: str | None = None
    completed_at: str | None = None
    status: str = "RUNNING"
    records_seen: int = 0
    records_cleaned: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    files_failed: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)

    def fail(self, kind: str, path: Path | None = None, line: int | None = None) -> None:
        self.error_count += 1
        if len(self.errors) < MAX_ERROR_DETAILS:
            self.errors.append({"type": kind, "file": path.name if path else None, "line": line})


def _paths() -> list[Path]:
    """Snapshot existing daily partitions, using the Stage 5 naming/order rule.

    Include broken links for error reporting; reject links before opening below.
    Non-partition files are outside the daily raw-storage contract.
    """
    root = _cfg.RAW_ARTICLES_DIR
    if not root.exists():
        return []
    paths = []
    for path in root.iterdir():
        index = _partition_index(path.name, path.name[:10])
        if index is not None:
            paths.append((path.name[:10], index, path.name, path))
    return [item[-1] for item in sorted(paths)]


def _process_file(conn: sqlite3.Connection, path: Path, report: CleaningReport,
                  since: datetime | None) -> None:
    """Commit each successful record; bad records never poison the next one."""
    try:
        safe_path = resolve_raw_path(path)
        # Reject partition symlinks, including in-root aliases. As with the
        # Stage 5 reader, callers must not replace files concurrently with reads.
        if path.is_symlink():
            raise RawPathViolation("Cleaning does not follow partition symlinks")
        for line_number, line in _iter_lines(safe_path):
            if not line.strip():
                continue
            report.records_seen += 1
            try:
                raw = _parse_and_validate(safe_path, line_number, line)
                if since is not None:
                    if raw.retrieved_at.utcoffset() is None:
                        raise CleaningError("Cannot apply --since to a naive retrieved_at")
                    if raw.retrieved_at < since:
                        report.records_skipped += 1
                        continue
                if already_cleaned(conn, raw.article_id, raw.raw_hash, report.cleaning_version):
                    report.records_skipped += 1
                    continue
                article = clean_article(raw, cleaning_version=report.cleaning_version)
                with conn:
                    inserted = save_clean_article(conn, article)
                if inserted:
                    report.records_cleaned += 1
                else:
                    report.records_skipped += 1
            except sqlite3.Error:
                # DB failures are run-level failures; do not repeatedly attempt
                # writes on a full/unavailable/incompatible database.
                report.records_failed += 1
                report.fail("DatabaseError", path, line_number)
                raise
            except Exception as exc:
                # Individual parsing/cleaning failures are visible, with no raw
                # payload or Pydantic input fragments included in persisted logs.
                report.records_failed += 1
                report.fail(type(exc).__name__, path, line_number)
    except (OSError, UnicodeError, RawPathViolation) as exc:
        report.files_failed += 1
        report.fail(type(exc).__name__, path)


def _finish_log(conn: sqlite3.Connection, report: CleaningReport) -> None:
    values = asdict(report)
    values["errors_json"] = json.dumps(values.pop("errors"), sort_keys=True)
    values["error_type"] = report.errors[0]["type"] if report.errors else None
    values["error_message"] = (
        f"{report.error_count} errors; first {len(report.errors)} locations in errors_json"
        if report.error_count else None
    )
    with conn:
        conn.execute(
            "UPDATE cleaning_run_log SET completed_at=:completed_at, status=:status, "
            "records_seen=:records_seen, records_cleaned=:records_cleaned, "
            "records_failed=:records_failed, records_skipped=:records_skipped, "
            "files_failed=:files_failed, duration_ms=:duration_ms, error_count=:error_count, "
            "error_type=:error_type, error_message=:error_message, errors_json=:errors_json "
            "WHERE run_id=:run_id", values,
        )


def run_cleaning(*, since: datetime | None = None,
                 cleaning_version: str = _cfg.CLEANING_VERSION) -> CleaningReport:
    """Clean existing partitions; --since means retrieved_at >= UTC cutoff.

    All partitions are inspected (partition day is write time, not necessarily
    retrieval time). Naive retrieval values are preserved without a filter;
    with a cutoff they are record failures, never assigned an invented zone.
    Empty/missing raw storage is a successful zero-record run, logged in SQLite.
    Failures to initialize or finalize SQLite raise DatabaseError to the CLI.
    """
    if not cleaning_version or len(cleaning_version) > 64:
        raise CleaningError("Invalid cleaning_version")
    if since is not None:
        if since.utcoffset() is None:
            raise CleaningError("since must be timezone-aware")
        since = since.astimezone(timezone.utc)
    started = time.monotonic()
    report = CleaningReport(
        str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), cleaning_version,
        since=since.isoformat() if since else None,
    )
    try:
        with pipeline_guard('clean') as lease, closing(connect_rw()) as conn:
            ensure_cleaning_schema(conn)
            reconcile_stale_runs(conn, lease)
            with conn:
                conn.execute(
                    "INSERT INTO cleaning_run_log (run_id, started_at, status, cleaning_version, since) "
                    "VALUES (?, ?, 'RUNNING', ?, ?)",
                    (report.run_id, report.started_at, cleaning_version, report.since),
                )
                register_run(conn, lease, report.run_id, report.started_at, since=report.since)
            fatal = False
            try:
                for path in _paths():
                    _process_file(conn, path, report, since)
            except sqlite3.Error:
                conn.rollback()
                fatal = True
            except OSError as exc:
                report.files_failed += 1
                report.fail(type(exc).__name__)
                fatal = True
            report.status = "SUCCESS"
            if report.error_count or fatal:
                # Skips can be old records outside --since, so only newly
                # committed rows establish partial success on an errored run.
                report.status = "PARTIAL_SUCCESS" if report.records_cleaned else "FAILED"
            report.completed_at = datetime.now(timezone.utc).isoformat()
            report.duration_ms = int((time.monotonic() - started) * 1000)
            _finish_log(conn, report)
    except (sqlite3.Error, OSError, DatabaseError) as exc:
        raise DatabaseError("Cleaning database initialization or run logging failed") from exc
    return report


__all__ = ["CleaningReport", "run_cleaning"]
