"""Offline Stage 7 orchestration over one immutable cleaning-version cohort.

No raw reader, fetcher, cleaning function, registry or network imports.
Each run snapshots cleaned rows and commits relationships/groups atomically.
Malformed rows are isolated; structural database failures roll back new Stage 7
results. Existing source rows and historical duplicate results are never edited.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from intelligence import config as cfg
from intelligence.db.connection import connect_rw
from intelligence.db.runs import pipeline_guard, reconcile_stale_runs, register_run
from intelligence.db.snapshots import cleaned_signature
from intelligence.db.deduplication import ensure_dedup_schema, load_pairs, save_group, save_pair
from intelligence.deduplication.compare import candidate_pairs, compare
from intelligence.deduplication.groups import build_groups
from intelligence.deduplication.normalize import prepare
from intelligence.errors import DatabaseError, DuplicateDetectionError, SnapshotChanged
from intelligence.schemas import CleanArticle

MAX_ERROR_DETAILS = 100


@dataclass
class DedupReport:
    run_id: str
    started_at: str
    cleaning_version: str
    dedup_version: str
    completed_at: str | None = None
    status: str = "RUNNING"
    records_seen: int = 0
    records_valid: int = 0
    records_failed: int = 0
    candidate_pairs: int = 0
    fuzzy_comparisons: int = 0
    pairs_skipped: int = 0
    exact_duplicates: int = 0
    near_duplicates: int = 0
    pairs_inserted: int = 0
    groups_evaluated: int = 0
    groups_created: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)
    since: str | None = None

    def fail(self, kind: str, ordinal: int | None = None) -> None:
        self.error_count += 1
        if len(self.errors) < MAX_ERROR_DETAILS:
            # Ordinal in the ordered SQL snapshot; no arbitrary input in logs.
            self.errors.append({"type": kind, "record": ordinal})


def _read_records(conn: sqlite3.Connection, report: DedupReport):
    records = {}
    anchors = set()
    since = datetime.fromisoformat(report.since) if report.since else None
    for ordinal, row in enumerate(conn.execute(
        "SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash",
        (report.cleaning_version,),
    ), 1):
        report.records_seen += 1
        try:
            record = prepare(CleanArticle.model_validate(dict(row)))
            if since is not None and record.article.retrieved_at.utcoffset() is None:
                raise DuplicateDetectionError('Cannot select an anchor with a naive retrieval timestamp')
            records[record.identity] = record
            report.records_valid += 1
            if since is None or record.article.retrieved_at >= since:
                anchors.add(record.identity)
        except Exception as exc:
            report.records_failed += 1
            report.fail(type(exc).__name__, ordinal)
    return records, anchors


def _compute(records, anchors, pairs, report: DedupReport):
    pending = []
    for a, b in candidate_pairs(records.values()):
        if a.identity not in anchors and b.identity not in anchors:
            continue
        report.candidate_pairs += 1
        key = (a.identity, b.identity)  # generator guarantees canonical order
        if key in pairs:
            report.pairs_skipped += 1
            kind = pairs[key]
        else:
            result = compare(a, b)
            report.fuzzy_comparisons += int(result.fuzzy_compared)
            kind = result.duplicate_type
            if kind != "NOT_DUPLICATE":
                pending.append((key, result))
                pairs[key] = kind
        report.exact_duplicates += int(kind == "EXACT_DUPLICATE")
        report.near_duplicates += int(kind == "NEAR_DUPLICATE")
    groups = build_groups(records, pairs, cleaning_version=report.cleaning_version,
                          dedup_version=report.dedup_version)
    report.groups_evaluated = len(groups)
    return pending, groups


def _persist(conn, pending, groups, report):
    for key, result in pending:
        report.pairs_inserted += int(save_pair(
            conn, *key, result, cleaning_version=report.cleaning_version,
            dedup_version=report.dedup_version, created_at=report.started_at,
        ))
    for group in groups:
        report.groups_created += int(save_group(
            conn, group, run_id=report.run_id, cleaning_version=report.cleaning_version,
            dedup_version=report.dedup_version, created_at=report.started_at,
        ))


def _finish_log(conn: sqlite3.Connection, report: DedupReport) -> None:
    data = asdict(report)
    data.pop('since')  # Stored in the additive ownership/context table.
    data["errors_json"] = json.dumps(data.pop("errors"), sort_keys=True)
    data["error_type"] = report.errors[0]["type"] if report.errors else None
    data["error_message"] = f"{report.error_count} errors; first {len(report.errors)} recorded" if report.error_count else None
    columns = [key for key in data if key not in {"run_id", "started_at", "cleaning_version", "dedup_version"}]
    # Column names come only from the internal report dataclass, never input.
    conn.execute("UPDATE dedup_run_log SET " + ",".join(f"{k}=:{k}" for k in columns)
                 + " WHERE run_id=:run_id", data)


def run_deduplication(*, cleaning_version: str = cfg.CLEANING_VERSION,
                      dedup_version: str = cfg.DEDUP_VERSION,
                      since: datetime | None = None) -> DedupReport:
    """Read snapshot -> unlocked computation -> checked atomic publication.

    Since selects retrieval anchors, never filters the candidate side. Only
    pairs touching an anchor are evaluated; groups include all stored positive
    edges. All classification thresholds, fingerprints and canonical ordering
    remain stage7-v1. Concurrent input changes abort publication for a safe retry.

    Schema initialization is additive, including on an empty database. A fresh
    successful run over no cleaned rows logs zero results and creates no raw
    directory. UUIDs/timing are operational; relationships/groups are stable.
    """
    for version in (cleaning_version, dedup_version):
        if not isinstance(version, str) or not version.strip() or len(version) > 64:
            raise DuplicateDetectionError("Versions must contain 1..64 characters")
    if since is not None:
        if since.utcoffset() is None:
            raise DuplicateDetectionError('since must be timezone-aware')
        since = since.astimezone(timezone.utc)
    start = time.monotonic()
    report = DedupReport(str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(),
                         cleaning_version, dedup_version, since=since.isoformat() if since else None)
    try:
        with pipeline_guard('dedupe') as lease, closing(connect_rw()) as conn:
            ensure_dedup_schema(conn)
            reconcile_stale_runs(conn, lease)
            with conn:
                conn.execute(
                    "INSERT INTO dedup_run_log (run_id,started_at,status,cleaning_version,dedup_version) "
                    "VALUES (?,?,'RUNNING',?,?)",
                    (report.run_id, report.started_at, cleaning_version, dedup_version),
                )
                register_run(conn, lease, report.run_id, report.started_at, since=report.since)
            try:
                conn.execute('BEGIN')
                signature = cleaned_signature(conn, cleaning_version)
                records, anchors = _read_records(conn, report)
                original_pairs = load_pairs(conn, cleaning_version, dedup_version)
                conn.commit()  # Release read snapshot before CPU work.
                pending, groups = _compute(records, anchors, dict(original_pairs), report)
                del records
                conn.execute("BEGIN IMMEDIATE")
                if (signature != cleaned_signature(conn, cleaning_version)
                        or original_pairs != load_pairs(conn, cleaning_version, dedup_version)):
                    raise SnapshotChanged('Cleaned cohort or duplicate relationships changed; rerun')
                _persist(conn, pending, groups, report)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',
                             (signature, 'dedupe', report.run_id))
                report.status = ('PARTIAL_SUCCESS' if report.records_valid else 'FAILED') if report.records_failed else 'SUCCESS'
                report.completed_at = datetime.now(timezone.utc).isoformat()
                report.duration_ms = int((time.monotonic() - start) * 1000)
                _finish_log(conn, report)  # Results and final success log commit together.
                conn.commit()
            except Exception as exc:
                conn.rollback()
                report.pairs_inserted = report.groups_created = report.groups_evaluated = 0
                report.fail("DatabaseError" if isinstance(exc, sqlite3.Error) else type(exc).__name__)
                report.status = "FAILED"
                report.completed_at = datetime.now(timezone.utc).isoformat()
                report.duration_ms = int((time.monotonic() - start) * 1000)
                with conn:
                    _finish_log(conn, report)
    except (sqlite3.Error, OSError, DatabaseError) as exc:
        raise DatabaseError("Duplicate database initialization or run logging failed") from exc
    return report


__all__ = ["DedupReport", "run_deduplication"]
