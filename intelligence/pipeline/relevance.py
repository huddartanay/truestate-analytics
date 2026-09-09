"""Offline Stage 8: canonical snapshot -> pure decisions -> atomic publication.

Does not import raw readers, acquisition, cleaner, dedup comparator or an LLM.
Upstream changes during computation abort publication and permit a safe retry.
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
from intelligence.db.relevance import (context_id, digest, ensure_relevance_schema, existing_keys,
                                       latest_context, link_result, result_key, save_result)
from intelligence.db.runs import pipeline_guard, reconcile_stale_runs, register_run
from intelligence.db.snapshots import cleaned_signature
from intelligence.errors import DatabaseError, RelevanceError, SnapshotChanged
from intelligence.relevance.classify import classify
from intelligence.schemas import CleanArticle, RealEstateRelevanceResult


@dataclass
class RelevanceReport:
    run_id: str
    started_at: str
    cleaning_version: str
    dedup_version: str
    relevance_version: str
    since: str | None = None
    completed_at: str | None = None
    status: str = 'RUNNING'
    records_seen: int = 0
    canonical_records_seen: int = 0
    relevant_count: int = 0
    irrelevant_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)
    dedup_run_id: str | None = None

    def fail(self, kind, ordinal=None):
        self.failed_count += 1
        self.error_count += 1
        if len(self.errors) < 100:
            self.errors.append({'type': kind, 'record': ordinal})


def _cohort(conn, groups, report):
    records = {}
    for ordinal, row in enumerate(conn.execute(
        'SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash',
        (report.cleaning_version,),
    ), 1):
        report.records_seen += 1
        try:
            article = CleanArticle.model_validate(dict(row))
            if report.since and article.retrieved_at.utcoffset() is None:
                raise RelevanceError('Retrieval cutoff requires timezone-aware input')
            records[(article.article_id, article.raw_hash)] = article
        except (ValueError, RelevanceError) as exc:
            report.fail(type(exc).__name__, ordinal)
    claimed = set()
    contexts = []
    for ordinal, group in enumerate(groups, 1):
        try:
            members = tuple(tuple(m) for m in json.loads(group['members_json']))
            canonical = (group['canonical_article_id'], group['canonical_raw_hash'])
            if (len(members) != group['member_count'] or len(members) < 2
                    or len(set(members)) != len(members) or canonical not in members
                    or any(len(m) != 2 or not all(isinstance(v, str) for v in m) for m in members)):
                raise RelevanceError('Malformed canonical membership')
        except (ValueError, TypeError, RelevanceError) as exc:
            # Unknown membership makes singleton fallback unsafe: structural stop.
            raise RelevanceError('Invalid Stage 7 membership snapshot') from exc
        if claimed.intersection(members):
            raise RelevanceError('Overlapping groups in one Stage 7 run')
        claimed.update(members)
        if any(member not in records for member in members):
            report.fail('InvalidGroupMember', ordinal)
            continue
        contexts.append((records[canonical], group['group_id'], members))
    contexts.extend((record, None, (identity,)) for identity, record in sorted(records.items()) if identity not in claimed)
    cutoff = datetime.fromisoformat(report.since) if report.since else None
    return [(a, g) for a, g, members in contexts
            if cutoff is None or any(records[m].retrieved_at >= cutoff for m in members)]


def _finish(conn, report, start):
    report.completed_at = datetime.now(timezone.utc).isoformat()
    report.duration_ms = int((time.monotonic() - start) * 1000)
    data = asdict(report)
    data['errors_json'] = json.dumps(data.pop('errors'), sort_keys=True)
    data['error_type'] = report.errors[0]['type'] if report.errors else None
    data['error_message'] = f'{report.error_count} errors; first {len(report.errors)} recorded' if report.errors else None
    conn.execute('UPDATE relevance_run_log SET ' + ','.join(k + '=:' + k for k in data if k != 'run_id') + ' WHERE run_id=:run_id', data)


def run_relevance(*, cleaning_version=cfg.CLEANING_VERSION, dedup_version=cfg.DEDUP_VERSION,
                  relevance_version=cfg.RELEVANCE_VERSION, since: datetime | None = None):
    for version in (cleaning_version, dedup_version, relevance_version):
        if not isinstance(version, str) or not version.strip() or len(version) > 64:
            raise RelevanceError('Versions must contain 1..64 characters')
    if since is not None:
        if since.utcoffset() is None:
            raise RelevanceError('since must be timezone-aware')
        since = since.astimezone(timezone.utc)
    start = time.monotonic()
    report = RelevanceReport(str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(),
                             cleaning_version, dedup_version, relevance_version,
                             since=since.isoformat() if since else None)
    try:
        with pipeline_guard('relevance') as lease, closing(connect_rw()) as conn:
            ensure_relevance_schema(conn)
            reconcile_stale_runs(conn, lease)
            with conn:
                conn.execute("INSERT INTO relevance_run_log (run_id,started_at,status,cleaning_version,dedup_version,relevance_version,since) VALUES (?,?,'RUNNING',?,?,?,?)",
                             (report.run_id, report.started_at, cleaning_version, dedup_version, relevance_version, report.since))
                register_run(conn, lease, report.run_id, report.started_at, since=report.since)
            try:
                conn.execute('BEGIN')
                signature = cleaned_signature(conn, cleaning_version)
                upstream = latest_context(conn, cleaning_version, dedup_version)
                report.dedup_run_id = upstream[0]
                contexts = _cohort(conn, upstream[1], report)
                existing = existing_keys(conn, cleaning_version, dedup_version, relevance_version)
                conn.commit()
                pending, keys = [], []
                for ordinal, (article, group) in enumerate(contexts, 1):
                    report.canonical_records_seen += 1
                    context = context_id(article, dedup_version, group)
                    key = result_key(article, dedup_version, relevance_version, context)
                    if key in existing:
                        report.skipped_count += 1
                        keys.append(key)
                        continue
                    try:
                        decision = classify(article)
                        result = RealEstateRelevanceResult(
                            article_id=article.article_id, raw_hash=article.raw_hash,
                            cleaning_version=cleaning_version, dedup_version=dedup_version,
                            relevance_version=relevance_version, context_id=context, group_id=group,
                            evaluated_at=report.started_at, **asdict(decision),
                        )
                        pending.append(result); keys.append(key)
                    except Exception as exc:
                        report.fail(type(exc).__name__, ordinal)
                conn.execute('BEGIN IMMEDIATE')
                if signature != cleaned_signature(conn, cleaning_version) or upstream != latest_context(conn, cleaning_version, dedup_version):
                    raise SnapshotChanged('Upstream relevance context changed; rerun')
                for result in pending:
                    if save_result(conn, result):
                        report.relevant_count += int(result.is_real_estate_relevant)
                        report.irrelevant_count += int(not result.is_real_estate_relevant)
                    else:
                        report.skipped_count += 1
                for key in keys:
                    link_result(conn, report.run_id, key)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',
                             (digest([signature, upstream]), 'relevance', report.run_id))
                report.status = ('PARTIAL_SUCCESS' if keys else 'FAILED') if report.error_count else 'SUCCESS'
                _finish(conn, report, start)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                report.relevant_count = report.irrelevant_count = 0
                report.fail('DatabaseError' if isinstance(exc, sqlite3.Error) else type(exc).__name__)
                report.status = 'FAILED'
                with conn:
                    _finish(conn, report, start)
    except (sqlite3.Error, OSError, DatabaseError) as exc:
        raise DatabaseError('Relevance database initialization or run logging failed') from exc
    return report
