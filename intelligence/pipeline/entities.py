"""Stage 10: eligible Stage 9 canonical snapshot -> extraction -> atomic publish."""
from __future__ import annotations
import json
import sqlite3
import time
import uuid
from contextlib import closing
from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone

from intelligence import config as cfg
from intelligence.db.connection import connect_rw
from intelligence.db.entities import (STAGE8_KEY,STAGE9_KEY,ensure_entity_schema,snapshot,extraction_id,
                                      existing_ids,save_result,link_result)
from intelligence.db.relevance import context_id
from intelligence.db.runs import pipeline_guard,reconcile_stale_runs,register_run
from intelligence.entities.registry import REGISTRY
from intelligence.entities.extract import extract,validate_extraction
from intelligence.errors import EntityExtractionError,DatabaseError,SnapshotChanged
from intelligence.schemas import CleanArticle,RealEstateRelevanceResult,UAERealEstateRelevanceResult,EntityExtractionResult


@dataclass
class EntityReport:
    run_id:str
    started_at:str
    cleaning_version:str
    dedup_version:str
    relevance_version:str
    uae_relevance_version:str
    registry_version:str
    entity_extraction_version:str
    entity_registry_version:str
    completed_at:str|None=None
    status:str='RUNNING'
    stage9_run_id:str|None=None
    since:str|None=None
    records_seen:int=0
    eligible_stage9_records:int=0
    ineligible_count:int=0
    evaluated_count:int=0
    records_with_entities:int=0
    records_without_entities:int=0
    mention_count:int=0
    country_mentions:int=0
    emirate_mentions:int=0
    city_mentions:int=0
    area_mentions:int=0
    community_mentions:int=0
    project_mentions:int=0
    building_mentions:int=0
    developer_mentions:int=0
    failed_count:int=0
    skipped_count:int=0
    duration_ms:int=0
    error_count:int=0
    errors:list[dict]=field(default_factory=list)

    def fail(self,kind,ordinal=None):
        self.failed_count+=1;self.error_count+=1
        if len(self.errors)<100:self.errors.append({'type':kind,'record':ordinal})


def _decode(row,uae=False):
    data=dict(row)
    signals=('matched_uae_signals','matched_exclusion_signals') if uae else ('matched_positive_signals','matched_negative_signals')
    for name in signals:data[name]=tuple(json.loads(data[name]))
    flag='is_uae_real_estate_relevant' if uae else 'is_real_estate_relevant'
    if data[flag] not in (0,1):raise EntityExtractionError('Invalid upstream acceptance value')
    data[flag]=bool(data[flag])
    return (UAERealEstateRelevanceResult if uae else RealEstateRelevanceResult).model_validate(data)


def _contexts(value,report):
    run,stage9,stage8,links,clean_rows,group_rows=value
    report.stage9_run_id=run['run_id'] if run else None
    upstream8={tuple(r[k] for k in STAGE8_KEY):r for r in stage8}
    links=set(links);cleaned={(r['article_id'],r['raw_hash']):r for r in clean_rows}
    groups={r['group_id']:r for r in group_rows}
    for ordinal,row in enumerate(stage9,1):
        report.records_seen+=1
        try:
            uae=_decode(row,True)
            versions=(uae.cleaning_version,uae.dedup_version,uae.relevance_version,uae.uae_relevance_version,uae.registry_version)
            if versions!=(report.cleaning_version,report.dedup_version,report.relevance_version,report.uae_relevance_version,report.registry_version):
                raise EntityExtractionError('Stage 9 run links inconsistent versions')
            if not uae.is_uae_real_estate_relevant:
                report.ineligible_count+=1;continue
            key=tuple(getattr(uae,k) for k in STAGE8_KEY)
            if key not in links:raise EntityExtractionError('Stage 9 context absent from its Stage 8 run')
            topic=_decode(upstream8[key])
            if not topic.is_real_estate_relevant:raise EntityExtractionError('Stage 8 rejected context cannot be promoted')
            article=CleanArticle.model_validate(cleaned[(uae.article_id,uae.raw_hash)])
            if topic.group_id!=uae.group_id or context_id(article,uae.dedup_version,uae.group_id)!=uae.context_id:
                raise EntityExtractionError('Invalid upstream canonical context')
            if uae.group_id:
                group=groups[uae.group_id];members=json.loads(group['members_json'])
                if (not isinstance(members,list) or len(members)<2 or len(members)!=group['member_count']
                    or any(not isinstance(m,list) or len(m)!=2 or not all(isinstance(v,str) for v in m) for m in members)
                    or len(set(map(tuple,members)))!=len(members)
                    or [uae.article_id,uae.raw_hash] not in members
                    or (group['canonical_article_id'],group['canonical_raw_hash'])!=(uae.article_id,uae.raw_hash)
                    or any(tuple(m) not in cleaned for m in members)):
                    raise EntityExtractionError('Invalid duplicate provenance')
            report.eligible_stage9_records+=1
            yield ordinal,article,uae,topic
        except (ValueError,TypeError,KeyError,EntityExtractionError):
            report.fail('EntityExtractionError',ordinal)


def _finish(conn,report,start):
    report.completed_at=datetime.now(timezone.utc).isoformat();report.duration_ms=int((time.monotonic()-start)*1000)
    data=asdict(report);data['errors_json']=json.dumps(data.pop('errors'),sort_keys=True)
    data['error_type']=report.errors[0]['type'] if report.errors else None
    data['error_message']=f'{report.error_count} errors; first {len(report.errors)} recorded' if report.errors else None
    conn.execute('UPDATE entity_extraction_run_log SET '+','.join(k+'=:'+k for k in data if k!='run_id')+' WHERE run_id=:run_id',data)


def run_entities(*,cleaning_version=cfg.CLEANING_VERSION,dedup_version=cfg.DEDUP_VERSION,
                 relevance_version=cfg.RELEVANCE_VERSION,uae_relevance_version=cfg.UAE_RELEVANCE_VERSION,
                 registry_version=cfg.REGISTRY_VERSION,entity_extraction_version=cfg.ENTITY_EXTRACTION_VERSION,
                 registry=REGISTRY):
    versions=(cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,entity_extraction_version,registry.version)
    if any(not isinstance(v,str) or not v.strip() or len(v)>64 for v in versions):raise EntityExtractionError('Versions must contain 1..64 characters')
    start=time.monotonic();report=EntityReport(str(uuid.uuid4()),datetime.now(timezone.utc).isoformat(),*versions)
    try:
        with pipeline_guard('entities') as lease,closing(connect_rw()) as conn:
            ensure_entity_schema(conn);reconcile_stale_runs(conn,lease)
            with conn:
                conn.execute("INSERT INTO entity_extraction_run_log (run_id,started_at,status,cleaning_version,dedup_version,relevance_version,uae_relevance_version,registry_version,entity_extraction_version,entity_registry_version) VALUES (?,?,'RUNNING',?,?,?,?,?,?,?)",(report.run_id,report.started_at,*versions))
                register_run(conn,lease,report.run_id,report.started_at)
            try:
                conn.execute('BEGIN');signature,value=snapshot(conn,versions[:5]);existing=existing_ids(conn,versions);conn.commit()
                pending,identities=[],[]
                for ordinal,article,uae,topic in _contexts(value,report):
                    identity=extraction_id(uae,entity_extraction_version,registry.version)
                    if identity in existing:
                        report.skipped_count+=1;identities.append(identity);continue
                    try:
                        report.evaluated_count+=1
                        output=extract(article,uae,topic,registry=registry)
                        validate_extraction(output,article,registry)
                        result=EntityExtractionResult(extraction_id=identity,**{k:getattr(uae,k) for k in STAGE9_KEY},
                            group_id=uae.group_id,entity_extraction_version=entity_extraction_version,entity_registry_version=registry.version,
                            evaluated_at=report.started_at,**asdict(output))
                        pending.append(result);identities.append(identity)
                    except Exception:report.fail('EntityExtractionError',ordinal)
                conn.execute('BEGIN IMMEDIATE')
                if signature!=snapshot(conn,versions[:5])[0]:raise SnapshotChanged('Stage 10 upstream snapshot changed; rerun')
                for result in pending:
                    if save_result(conn,result):
                        report.records_with_entities+=int(bool(result.mentions));report.records_without_entities+=int(not result.mentions)
                        report.mention_count+=len(result.mentions)
                        for mention in result.mentions:
                            name=mention.entity_type.value.lower()+'_mentions';setattr(report,name,getattr(report,name)+1)
                    else:report.skipped_count+=1
                for identity in identities:link_result(conn,report.run_id,identity)
                conn.execute('UPDATE pipeline_run_owners SET cohort_hash=? WHERE pipeline=? AND run_id=?',(signature,'entities',report.run_id))
                report.status=('PARTIAL_SUCCESS' if identities else 'FAILED') if report.error_count else 'SUCCESS'
                _finish(conn,report,start);conn.commit()
            except Exception as exc:
                conn.rollback()
                for name in ('records_with_entities','records_without_entities','mention_count','country_mentions','emirate_mentions','city_mentions','area_mentions','community_mentions','project_mentions','building_mentions','developer_mentions'):setattr(report,name,0)
                report.fail('SnapshotChanged' if isinstance(exc,SnapshotChanged) else 'DatabaseError' if isinstance(exc,(sqlite3.Error,DatabaseError)) else 'EntityExtractionError')
                report.status='FAILED'
                with conn:_finish(conn,report,start)
    except (sqlite3.Error,OSError,DatabaseError) as exc:
        raise DatabaseError('Entity extraction initialization or run logging failed') from exc
    return report
