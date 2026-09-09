"""Offline merged Stage 13. One immutable build and atomic CURRENT publication."""
from contextlib import closing
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import sqlite3
import time
import uuid
from intelligence import config as cfg
from intelligence.db.cleaning import ensure_cleaning_schema
from intelligence.db.connection import connect_rw
from intelligence.db.intelligence import VERSION_FIELDS, snapshot, raw_urls, publish
from intelligence.db.runs import pipeline_guard, register_run, reconcile_stale_runs
from intelligence.errors import DatabaseError, SnapshotChanged
from intelligence.serving.build import contexts, build
from intelligence.serving.policy import POLICY, identity

BUILD_VERSIONS=('intelligence_build_version','market_movement_version','ranking_version')


@dataclass
class IntelligenceReport:
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
    intelligence_build_version: str
    market_movement_version: str
    ranking_version: str
    completed_at: str | None = None
    status: str = 'RUNNING'
    stage12_run_id: str | None = None
    build_id: str | None = None
    cohort_hash: str | None = None
    counts: dict = field(default_factory=dict)
    reused_count: int = 0
    failed_count: int = 0
    duration_ms: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)

    @property
    def versions(self): return tuple(getattr(self,k) for k in VERSION_FIELDS+BUILD_VERSIONS)


def finish(conn,report,start):
    report.completed_at=datetime.now(timezone.utc).isoformat()
    report.duration_ms=int((time.monotonic()-start)*1000)
    data=asdict(report)
    data['counts_json']=json.dumps(data.pop('counts'),sort_keys=True)
    data['errors_json']=json.dumps(data.pop('errors'),sort_keys=True)
    data['error_type']=report.errors[0]['type'] if report.errors else None
    data['error_message']='Stage 13 publication failed; previous build retained' if report.errors else None
    conn.execute('UPDATE intelligence_run_log SET '+','.join(k+'=:'+k for k in data if k!='run_id')+' WHERE run_id=:run_id',data)


def run_intelligence(*,cleaning_version=cfg.CLEANING_VERSION,dedup_version=cfg.DEDUP_VERSION,
    relevance_version=cfg.RELEVANCE_VERSION,uae_relevance_version=cfg.UAE_RELEVANCE_VERSION,registry_version=cfg.REGISTRY_VERSION,
    entity_extraction_version=cfg.ENTITY_EXTRACTION_VERSION,entity_registry_version=cfg.ENTITY_REGISTRY_VERSION,
    event_extraction_version=cfg.EVENT_EXTRACTION_VERSION,metric_extraction_version=cfg.METRIC_EXTRACTION_VERSION,
    intelligence_build_version=cfg.INTELLIGENCE_BUILD_VERSION,market_movement_version=cfg.MARKET_MOVEMENT_VERSION,
    ranking_version=cfg.RANKING_VERSION,policy=POLICY):
    versions=(cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,
              entity_extraction_version,entity_registry_version,event_extraction_version,metric_extraction_version,
              intelligence_build_version,market_movement_version,ranking_version)
    if any(not isinstance(v,str) or not v.strip() or len(v)>64 for v in versions): raise ValueError('Invalid version')
    report=IntelligenceReport(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),*versions)
    report.active_component='DATABASE';report.active_record=None
    start=time.monotonic()
    try:
        with pipeline_guard('intelligence') as lease,closing(connect_rw()) as conn:
            ensure_cleaning_schema(conn);reconcile_stale_runs(conn,lease)
            with conn:
                names=VERSION_FIELDS+BUILD_VERSIONS
                conn.execute('INSERT INTO intelligence_run_log(run_id,started_at,status,'+','.join(names)+") VALUES (?,?,'RUNNING',"+','.join('?' for _ in versions)+')',(report.run_id,report.started_at,*versions))
                register_run(conn,lease,report.run_id,report.started_at)
            try:
                conn.execute('BEGIN');signature,value=snapshot(conn,versions[:9]);conn.commit()
                inputs,cohort,excluded=contexts(value,report)
                urls=raw_urls(value[6])
                report.cohort_hash=identity((cohort,sorted(urls.items())))
                report.build_id=identity((report.cohort_hash,versions,policy.policy_id))
                report.counts=excluded
                existing=conn.execute('SELECT counts_json FROM intelligence_builds WHERE build_id=?',(report.build_id,)).fetchone()
                bundle=None
                if existing:
                    report.reused_count=1;report.counts=json.loads(existing[0])
                else:
                    bundle=build(inputs,urls,report,policy)
                report.active_record=None
                report.active_component='PUBLICATION'
                conn.execute('BEGIN IMMEDIATE')
                new_signature,new_value=snapshot(conn,versions[:9])
                if signature!=new_signature or urls!=raw_urls(new_value[6]): raise SnapshotChanged('Stage 12 snapshot changed')
                if bundle is not None: publish(conn,bundle,report,policy)
                conn.execute("INSERT INTO intelligence_current VALUES ('CURRENT',?) ON CONFLICT(channel) DO UPDATE SET build_id=excluded.build_id",(report.build_id,))
                conn.execute('INSERT INTO intelligence_run_results VALUES (?,?)',(report.run_id,report.build_id))
                conn.execute("UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline='intelligence' AND run_id=?",(report.cohort_hash,report.run_id))
                report.status='SUCCESS';finish(conn,report,start);conn.commit()
            except Exception as exc:
                conn.rollback();report.status='FAILED';report.failed_count=report.error_count=1
                report.errors=[dict(type='SnapshotChanged' if isinstance(exc,SnapshotChanged) else 'IntelligenceBuildError',component=getattr(exc,'component',report.active_component),record=report.active_record)]
                report.build_id=None;report.reused_count=0;report.counts={}
                with conn: finish(conn,report,start)
    except (sqlite3.Error,OSError,DatabaseError) as exc:
        raise DatabaseError('Intelligence initialization or run logging failed') from exc
    return report
