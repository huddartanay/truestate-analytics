"""Stage 11: stored Stage 10 snapshot, offline extraction, atomic publication."""
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from collections import defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from intelligence import config as cfg
from intelligence.db.connection import connect_rw
from intelligence.db.events import (VERSION_FIELDS,STAGE8_KEY,STAGE9_KEY,ensure_event_schema,
                                    snapshot,decode_entity,existing_ids,save_result,link_result)
from intelligence.db.relevance import context_id
from intelligence.db.runs import pipeline_guard,reconcile_stale_runs,register_run
from intelligence.entities.normalize import normalize
from intelligence.enums import EventType
from intelligence.events.extract import extract,validate_input,validate_events
from intelligence.events.identity import result_id,UPSTREAM_KEY
from intelligence.errors import EventExtractionError,EntityExtractionError,DatabaseError,SnapshotChanged
from intelligence.pipeline.entities import _decode
from intelligence.schemas import CleanArticle,EventExtractionResult


@dataclass
class EventReport:
    run_id: str
    started_at: str
    cleaning_version: str
    dedup_version: str
    relevance_version: str
    uae_relevance_version: str
    registry_version: str
    entity_extraction_version: str
    entity_registry_version: str
    event_extraction_version: str
    completed_at: str | None = None
    status: str = 'RUNNING'
    stage10_run_id: str | None = None
    since: str | None = None
    records_seen: int = 0
    eligible_stage10_records: int = 0
    evaluated_count: int = 0
    records_with_events: int = 0
    records_without_events: int = 0
    event_count: int = 0
    event_type_counts: dict = field(default_factory=lambda:{t.value:0 for t in EventType})
    failed_count: int = 0
    skipped_count: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)

    def fail(self,kind,ordinal=None):
        self.failed_count += 1
        self.error_count += 1
        if len(self.errors)<100:
            self.errors.append({'type':kind,'record':ordinal})


def _contexts(value,report):
    run,rows,mentions,run9,run8,stage9,stage8,clean_rows,group_rows = value
    report.stage10_run_id = run['run_id'] if run else None
    by_mention = defaultdict(list)
    for row in mentions:
        by_mention[row['extraction_id']].append(row)
    uae = {tuple(r[k] for k in STAGE9_KEY):r for r in stage9}
    topic = {tuple(r[k] for k in STAGE8_KEY):r for r in stage8}
    cleaned = {(r['article_id'],r['raw_hash']):r for r in clean_rows}
    groups = {r['group_id']:r for r in group_rows}
    for ordinal,row in enumerate(rows,1):
        report.records_seen += 1
        try:
            upstream = decode_entity(row,by_mention[row['extraction_id']])
            if tuple(getattr(upstream,k) for k in VERSION_FIELDS)!=tuple(getattr(report,k) for k in VERSION_FIELDS):
                raise EventExtractionError('Stage 10 result versions disagree with run')
            stage9_result = _decode(uae[tuple(getattr(upstream,k) for k in STAGE9_KEY)],True)
            stage8_result = _decode(topic[tuple(getattr(upstream,k) for k in STAGE8_KEY)])
            article = CleanArticle.model_validate(cleaned[(upstream.article_id,upstream.raw_hash)])
            validate_input(article,upstream,stage9_result,stage8_result)
            if any(normalize(m.matched_text)!=m.normalized_alias for m in upstream.mentions):
                raise EventExtractionError('Stage 10 alias/evidence mismatch')
            if context_id(article,upstream.dedup_version,upstream.group_id)!=upstream.context_id:
                raise EventExtractionError('Invalid canonical context')
            if upstream.group_id:
                group = groups[upstream.group_id]
                members = json.loads(group['members_json'])
                if (not isinstance(members,list) or len(members)<2 or len(members)!=group['member_count']
                    or any(not isinstance(m,list) or len(m)!=2 or not all(isinstance(v,str) for v in m) for m in members)
                    or len(set(map(tuple,members)))!=len(members)
                    or [upstream.article_id,upstream.raw_hash] not in members
                    or (group['canonical_article_id'],group['canonical_raw_hash'])!=(upstream.article_id,upstream.raw_hash)
                    or any(tuple(m) not in cleaned for m in members)):
                    raise EventExtractionError('Invalid canonical provenance')
            report.eligible_stage10_records += 1
            yield ordinal,article,upstream,stage9_result,stage8_result
        except (ValueError,TypeError,KeyError,DatabaseError,EventExtractionError,EntityExtractionError):
            report.fail('EventExtractionError',ordinal)


def _finish(conn,report,start):
    report.completed_at = datetime.now(timezone.utc).isoformat()
    report.duration_ms = int((time.monotonic()-start)*1000)
    data = asdict(report)
    data['errors_json'] = json.dumps(data.pop('errors'),sort_keys=True)
    data['event_type_counts_json'] = json.dumps(data.pop('event_type_counts'),sort_keys=True)
    data['error_type'] = report.errors[0]['type'] if report.errors else None
    data['error_message'] = f'{report.error_count} errors; first {len(report.errors)} recorded' if report.errors else None
    conn.execute('UPDATE event_run_log SET '+','.join(k+'=:'+k for k in data if k!='run_id')+' WHERE run_id=:run_id',data)


def run_events(*,cleaning_version=cfg.CLEANING_VERSION,dedup_version=cfg.DEDUP_VERSION,
               relevance_version=cfg.RELEVANCE_VERSION,uae_relevance_version=cfg.UAE_RELEVANCE_VERSION,
               registry_version=cfg.REGISTRY_VERSION,entity_extraction_version=cfg.ENTITY_EXTRACTION_VERSION,
               entity_registry_version=cfg.ENTITY_REGISTRY_VERSION,event_extraction_version=cfg.EVENT_EXTRACTION_VERSION):
    versions = (cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,
                entity_extraction_version,entity_registry_version,event_extraction_version)
    if any(not isinstance(v,str) or not v.strip() or len(v)>64 for v in versions):
        raise EventExtractionError('Versions must contain 1..64 characters')
    start = time.monotonic()
    report = EventReport(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),*versions)
    try:
        with pipeline_guard('events') as lease,closing(connect_rw()) as conn:
            ensure_event_schema(conn)
            reconcile_stale_runs(conn,lease)
            with conn:
                conn.execute("INSERT INTO event_run_log (run_id,started_at,status,"+','.join(VERSION_FIELDS)+",event_extraction_version) VALUES (?,?,'RUNNING',"+','.join('?' for _ in versions)+')',(report.run_id,report.started_at,*versions))
                register_run(conn,lease,report.run_id,report.started_at)
            try:
                conn.execute('BEGIN')
                signature,value = snapshot(conn,versions[:7])
                existing = existing_ids(conn,event_extraction_version)
                conn.commit()
                pending,identities = [],[]
                for ordinal,article,upstream,stage9,stage8 in _contexts(value,report):
                    identity = result_id(upstream.extraction_id,event_extraction_version)
                    if identity in existing:
                        report.skipped_count += 1
                        identities.append(identity)
                        continue
                    try:
                        report.evaluated_count += 1
                        events = extract(article,upstream,stage9,stage8,version=event_extraction_version)
                        validate_events(events,article,upstream,event_extraction_version)
                        result = EventExtractionResult(event_result_id=identity,extraction_id=upstream.extraction_id,
                            **{k:getattr(upstream,k) for k in UPSTREAM_KEY},group_id=upstream.group_id,
                            event_extraction_version=event_extraction_version,location_scope=upstream.location_scope,
                            events=events,evaluated_at=report.started_at)
                        pending.append(result)
                        identities.append(identity)
                    except Exception:
                        report.fail('EventExtractionError',ordinal)
                conn.execute('BEGIN IMMEDIATE')
                if signature!=snapshot(conn,versions[:7])[0]:
                    raise SnapshotChanged('Stage 11 upstream snapshot changed; rerun')
                for result in pending:
                    if save_result(conn,result):
                        report.records_with_events += int(bool(result.events))
                        report.records_without_events += int(not result.events)
                        report.event_count += len(result.events)
                        for event in result.events:
                            report.event_type_counts[event.event_type.value] += 1
                    else:
                        report.skipped_count += 1
                for identity in identities:
                    link_result(conn,report.run_id,identity)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',(signature,'events',report.run_id))
                report.status = ('PARTIAL_SUCCESS' if identities else 'FAILED') if report.error_count else 'SUCCESS'
                _finish(conn,report,start)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                report.records_with_events = report.records_without_events = report.event_count = 0
                report.event_type_counts = {t.value:0 for t in EventType}
                report.fail('SnapshotChanged' if isinstance(exc,SnapshotChanged) else 'DatabaseError' if isinstance(exc,(sqlite3.Error,DatabaseError)) else 'EventExtractionError')
                report.status = 'FAILED'
                with conn:
                    _finish(conn,report,start)
    except (sqlite3.Error,OSError,DatabaseError) as exc:
        raise DatabaseError('Event extraction initialization or run logging failed') from exc
    return report
