"""Stage 9: Stage 8 snapshot -> eligible canonical decisions -> atomic publish.

No acquisition, Stage 8 reclassification, deduplication or entity extraction.
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
from intelligence.db.relevance import context_id
from intelligence.db.uae_relevance import (ensure_uae_relevance_schema, snapshot, existing_keys,
                                           key_for, save_result, link_result)
from intelligence.db.runs import pipeline_guard, reconcile_stale_runs, register_run
from intelligence.errors import DatabaseError, UAERelevanceError, SnapshotChanged
from intelligence.schemas import CleanArticle, RealEstateRelevanceResult, UAERealEstateRelevanceResult
from intelligence.uae_relevance.classify import classify


@dataclass
class UAERelevanceReport:
    run_id: str
    started_at: str
    cleaning_version: str
    dedup_version: str
    relevance_version: str
    uae_relevance_version: str
    registry_version: str
    completed_at: str | None = None
    status: str = 'RUNNING'
    stage8_run_id: str | None = None
    since: str | None = None
    records_seen: int = 0
    eligible_stage8_records: int = 0
    ineligible_count: int = 0
    evaluated_count: int = 0
    uae_relevant_count: int = 0
    not_uae_relevant_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)

    def fail(self, kind, ordinal=None):
        self.failed_count += 1
        self.error_count += 1
        if len(self.errors) < 100:
            self.errors.append({'type': kind, 'record': ordinal})


def _contexts(value, report):
    run, rows, clean_rows, group_rows = value
    report.stage8_run_id = run['run_id'] if run else None
    cleaned = {(r['article_id'],r['raw_hash']):r for r in clean_rows}
    groups = {r['group_id']:r for r in group_rows}
    for ordinal, row in enumerate(rows,1):
        report.records_seen += 1
        try:
            data = dict(row)
            for name in ('matched_positive_signals','matched_negative_signals'):
                data[name] = tuple(json.loads(data[name]))
            if data['is_real_estate_relevant'] not in (0,1):
                raise UAERelevanceError('Invalid Stage 8 eligibility value')
            data['is_real_estate_relevant'] = bool(data['is_real_estate_relevant'])
            upstream = RealEstateRelevanceResult.model_validate(data)
            if (upstream.cleaning_version,upstream.dedup_version,upstream.relevance_version) != (report.cleaning_version,report.dedup_version,report.relevance_version):
                raise UAERelevanceError('Stage 8 run links inconsistent versions')
            if not upstream.is_real_estate_relevant:
                report.ineligible_count += 1
                continue
            article = CleanArticle.model_validate(cleaned[(upstream.article_id,upstream.raw_hash)])
            if context_id(article,upstream.dedup_version,upstream.group_id) != upstream.context_id:
                raise UAERelevanceError('Invalid Stage 8 context hash')
            if upstream.group_id:
                group = groups[upstream.group_id]
                members = json.loads(group['members_json'])
                canonical = [upstream.article_id,upstream.raw_hash]
                if (canonical != [group['canonical_article_id'],group['canonical_raw_hash']]
                        or canonical not in members or len(members)!=group['member_count']
                        or len(members)<2 or any(not isinstance(m,list) or len(m)!=2 or not all(isinstance(v,str) for v in m) for m in members)
                        or len({tuple(m) for m in members})!=len(members)
                        or any(tuple(m) not in cleaned for m in members)):
                    raise UAERelevanceError('Invalid canonical provenance')
            report.eligible_stage8_records += 1
            yield ordinal, article, upstream
        except (ValueError, TypeError, KeyError, UAERelevanceError):
            report.fail('UAERelevanceError',ordinal)


def _finish(conn, report, start):
    report.completed_at = datetime.now(timezone.utc).isoformat()
    report.duration_ms = int((time.monotonic()-start)*1000)
    data = asdict(report)
    data['errors_json'] = json.dumps(data.pop('errors'),sort_keys=True)
    data['error_type'] = report.errors[0]['type'] if report.errors else None
    data['error_message'] = f'{report.error_count} errors; first {len(report.errors)} recorded' if report.errors else None
    conn.execute('UPDATE uae_relevance_run_log SET '+','.join(k+'=:'+k for k in data if k!='run_id')+' WHERE run_id=:run_id',data)


def run_uae_relevance(*, cleaning_version=cfg.CLEANING_VERSION, dedup_version=cfg.DEDUP_VERSION,
                      relevance_version=cfg.RELEVANCE_VERSION, uae_relevance_version=cfg.UAE_RELEVANCE_VERSION):
    versions = (cleaning_version,dedup_version,relevance_version,uae_relevance_version,cfg.REGISTRY_VERSION)
    if any(not isinstance(v,str) or not v.strip() or len(v)>64 for v in versions):
        raise UAERelevanceError('Versions must contain 1..64 characters')
    start = time.monotonic()
    report = UAERelevanceReport(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),*versions)
    try:
        with pipeline_guard('uae_relevance') as lease, closing(connect_rw()) as conn:
            ensure_uae_relevance_schema(conn)
            reconcile_stale_runs(conn,lease)
            with conn:
                conn.execute("INSERT INTO uae_relevance_run_log (run_id,started_at,status,cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version) VALUES (?,?,'RUNNING',?,?,?,?,?)",
                             (report.run_id,report.started_at,*versions))
                register_run(conn,lease,report.run_id,report.started_at)
            try:
                conn.execute('BEGIN')
                signature,value = snapshot(conn,*versions[:3])
                existing = existing_keys(conn,versions)
                conn.commit()
                pending, keys = [], []
                for ordinal, article, upstream in _contexts(value,report):
                    key = key_for(upstream,uae_relevance_version,report.registry_version)
                    if key in existing:
                        report.skipped_count += 1
                        keys.append(key)
                        continue
                    try:
                        report.evaluated_count += 1
                        decision = classify(article,upstream)
                        result = UAERealEstateRelevanceResult(
                            **{k:getattr(upstream,k) for k in ('article_id','raw_hash','cleaning_version','dedup_version','relevance_version','context_id','group_id')},
                            uae_relevance_version=uae_relevance_version,registry_version=report.registry_version,
                            evaluated_at=report.started_at,**asdict(decision))
                        pending.append(result);keys.append(key)
                    except Exception:
                        report.fail('UAERelevanceError',ordinal)
                conn.execute('BEGIN IMMEDIATE')
                if signature != snapshot(conn,*versions[:3])[0]:
                    raise SnapshotChanged('Stage 9 upstream snapshot changed; rerun')
                for result in pending:
                    if save_result(conn,result):
                        report.uae_relevant_count += int(result.is_uae_real_estate_relevant)
                        report.not_uae_relevant_count += int(not result.is_uae_real_estate_relevant)
                    else:
                        report.skipped_count += 1
                for key in keys:
                    link_result(conn,report.run_id,key)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',
                             (signature,'uae_relevance',report.run_id))
                report.status = ('PARTIAL_SUCCESS' if keys else 'FAILED') if report.error_count else 'SUCCESS'
                _finish(conn,report,start)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                report.uae_relevant_count = report.not_uae_relevant_count = 0
                report.fail('SnapshotChanged' if isinstance(exc,SnapshotChanged) else 'DatabaseError' if isinstance(exc,(sqlite3.Error,DatabaseError)) else 'UAERelevanceError')
                report.status = 'FAILED'
                with conn:
                    _finish(conn,report,start)
    except (sqlite3.Error,OSError,DatabaseError) as exc:
        raise DatabaseError('UAE relevance initialization or run logging failed') from exc
    return report
