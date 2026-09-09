"""Stage 12: stored Stage 11 snapshot, offline extraction, atomic publication."""
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
from intelligence.db.metrics import (VERSION_FIELDS,ensure_metric_schema,snapshot,decode_event,existing_ids,save_result,link_result)
from intelligence.db.runs import pipeline_guard,reconcile_stale_runs,register_run
from intelligence.enums import MetricType
from intelligence.metrics.extract import extract,validate_input,validate_observations
from intelligence.metrics.identity import result_id
from intelligence.errors import EventExtractionError,MetricExtractionError,DatabaseError,SnapshotChanged
from intelligence.schemas import MetricExtractionResult


@dataclass
class MetricReport:
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
    metric_extraction_version: str
    completed_at: str | None = None
    status: str = 'RUNNING'
    stage11_run_id: str | None = None
    since: str | None = None
    records_seen: int = 0
    eligible_stage11_records: int = 0
    evaluated_count: int = 0
    records_with_observations: int = 0
    records_without_observations: int = 0
    observation_count: int = 0
    metric_type_counts: dict = field(default_factory=lambda:{t.value:0 for t in MetricType})
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
    run,rows,instances,links,entity_value=value
    report.stage11_run_id=run['run_id'] if run else None
    from intelligence.pipeline.events import _contexts as entity_contexts, EventReport
    audit=EventReport(report.run_id,report.started_at,*(getattr(report,k) for k in VERSION_FIELDS))
    contexts={u.extraction_id:(a,u,s9,s8) for _,a,u,s9,s8 in entity_contexts(entity_value,audit)}
    by_event=defaultdict(list);by_link=defaultdict(list)
    for row in instances: by_event[row['event_result_id']].append(row)
    for row in links: by_link[row['event_id']].append(row)
    for ordinal,row in enumerate(rows,1):
        report.records_seen+=1
        try:
            article,entities,s9,s8=contexts[row['extraction_id']]
            upstream=decode_event(row,by_event[row['event_result_id']],by_link,entities)
            if any(getattr(upstream,k)!=getattr(report,k) for k in VERSION_FIELDS):
                raise MetricExtractionError('Stage 11 version mismatch')
            validate_input(article,entities,upstream,s9,s8)
            report.eligible_stage11_records+=1
            yield ordinal,article,entities,upstream,s9,s8
        except (ValueError,TypeError,KeyError,DatabaseError,MetricExtractionError,EventExtractionError):
            report.fail('MetricExtractionError',ordinal)


def _finish(conn,report,start):
    report.completed_at = datetime.now(timezone.utc).isoformat()
    report.duration_ms = int((time.monotonic()-start)*1000)
    data = asdict(report)
    data['errors_json'] = json.dumps(data.pop('errors'),sort_keys=True)
    data['metric_type_counts_json'] = json.dumps(data.pop('metric_type_counts'),sort_keys=True)
    data['error_type'] = report.errors[0]['type'] if report.errors else None
    data['error_message'] = f'{report.error_count} errors; first {len(report.errors)} recorded' if report.errors else None
    conn.execute('UPDATE metric_run_log SET '+','.join(k+'=:'+k for k in data if k!='run_id')+' WHERE run_id=:run_id',data)


def run_metrics(*,cleaning_version=cfg.CLEANING_VERSION,dedup_version=cfg.DEDUP_VERSION,
               relevance_version=cfg.RELEVANCE_VERSION,uae_relevance_version=cfg.UAE_RELEVANCE_VERSION,
               registry_version=cfg.REGISTRY_VERSION,entity_extraction_version=cfg.ENTITY_EXTRACTION_VERSION,
               entity_registry_version=cfg.ENTITY_REGISTRY_VERSION,event_extraction_version=cfg.EVENT_EXTRACTION_VERSION,
               metric_extraction_version=cfg.METRIC_EXTRACTION_VERSION):
    versions = (cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,
                entity_extraction_version,entity_registry_version,event_extraction_version,metric_extraction_version)
    if any(not isinstance(v,str) or not v.strip() or len(v)>64 for v in versions):
        raise MetricExtractionError('Versions must contain 1..64 characters')
    start = time.monotonic()
    report = MetricReport(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),*versions)
    try:
        with pipeline_guard('metrics') as lease,closing(connect_rw()) as conn:
            ensure_metric_schema(conn)
            reconcile_stale_runs(conn,lease)
            with conn:
                conn.execute("INSERT INTO metric_run_log (run_id,started_at,status,"+','.join(VERSION_FIELDS)+",metric_extraction_version) VALUES (?,?,'RUNNING',"+','.join('?' for _ in versions)+')',(report.run_id,report.started_at,*versions))
                register_run(conn,lease,report.run_id,report.started_at)
            try:
                conn.execute('BEGIN')
                signature,value = snapshot(conn,versions[:8])
                existing = existing_ids(conn,metric_extraction_version)
                conn.commit()
                pending,identities = [],[]
                for ordinal,article,entities,upstream,stage9,stage8 in _contexts(value,report):
                    identity = result_id(upstream.event_result_id,metric_extraction_version)
                    if identity in existing:
                        report.skipped_count += 1
                        identities.append(identity)
                        continue
                    try:
                        report.evaluated_count += 1
                        observations = extract(article,entities,upstream,stage9,stage8,version=metric_extraction_version)
                        validate_observations(observations,article,entities,upstream,metric_extraction_version)
                        result = MetricExtractionResult(**(upstream.model_dump()|dict(events=(),
                            metric_result_id=identity,metric_extraction_version=metric_extraction_version,
                            source_id=article.source_id,observations=observations,evaluated_at=report.started_at)))
                        pending.append(result)
                        identities.append(identity)
                    except Exception:
                        report.fail('MetricExtractionError',ordinal)
                conn.execute('BEGIN IMMEDIATE')
                if signature!=snapshot(conn,versions[:8])[0]:
                    raise SnapshotChanged('Stage 12 upstream snapshot changed; rerun')
                for result in pending:
                    if save_result(conn,result):
                        report.records_with_observations += int(bool(result.observations))
                        report.records_without_observations += int(not result.observations)
                        report.observation_count += len(result.observations)
                        for observation in result.observations:
                            report.metric_type_counts[observation.metric.value] += 1
                    else:
                        report.skipped_count += 1
                for identity in identities:
                    link_result(conn,report.run_id,identity)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',(signature,'metrics',report.run_id))
                report.status = ('PARTIAL_SUCCESS' if identities else 'FAILED') if report.error_count else 'SUCCESS'
                _finish(conn,report,start)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                report.records_with_observations = report.records_without_observations = report.observation_count = 0
                report.metric_type_counts = {t.value:0 for t in MetricType}
                report.fail('SnapshotChanged' if isinstance(exc,SnapshotChanged) else 'DatabaseError' if isinstance(exc,(sqlite3.Error,DatabaseError)) else 'MetricExtractionError')
                report.status = 'FAILED'
                with conn:
                    _finish(conn,report,start)
    except (sqlite3.Error,OSError,DatabaseError) as exc:
        raise DatabaseError('Metric extraction initialization or run logging failed') from exc
    return report
