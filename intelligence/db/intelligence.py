"""Anchored Stage 12 snapshots and transaction-owned serving persistence."""
from collections import defaultdict
from dataclasses import asdict
import json
from intelligence.db.metrics import snapshot as event_snapshot, VERSION_FIELDS as EVENT_VERSIONS
from intelligence.db.snapshots import _sql_value
from intelligence.errors import DatabaseError
from intelligence.schemas import MetricExtractionResult
from intelligence.serving.policy import identity
from intelligence.metrics.identity import decimal_text
from intelligence.storage.raw import open_raw_read, _parse_and_validate
from pathlib import Path

VERSION_FIELDS=EVENT_VERSIONS+('metric_extraction_version',)
TABLES=('intelligence_builds','intelligence_current','intelligence_articles','intelligence_article_entities',
        'intelligence_events','intelligence_event_entities','intelligence_observations','market_series',
        'market_movements','market_movement_unavailable','market_rankings','market_ranking_entries',
        'intelligence_run_log','intelligence_run_results')


def snapshot(conn,versions):
    where=' AND '.join(k+'=?' for k in VERSION_FIELDS)
    row=conn.execute("SELECT * FROM metric_run_log WHERE "+where+" AND status IN ('SUCCESS','PARTIAL_SUCCESS') AND completed_at IS NOT NULL ORDER BY completed_at DESC,rowid DESC LIMIT 1",versions).fetchone()
    run=dict(row) if row else None
    if run is None: return identity(('EMPTY',versions)),(None,[],[],[],[],None,[])
    run_id=run['run_id']
    def select(sql): return [dict(r) for r in conn.execute(sql,(run_id,))]
    results=select('SELECT r.* FROM metric_extraction_results r JOIN metric_run_results l USING(metric_result_id) WHERE l.run_id=? ORDER BY r.metric_result_id')
    if len(results)!=conn.execute('SELECT count(*) FROM metric_run_results WHERE run_id=?',(run_id,)).fetchone()[0]:
        raise DatabaseError('Unresolved Stage 12 cohort reference')
    if results and not run['stage11_run_id']: raise DatabaseError('Missing Stage 12 anchor')
    observations=select('SELECT o.* FROM market_observations o JOIN metric_run_results l USING(metric_result_id) WHERE l.run_id=? ORDER BY o.metric_result_id,o.observation_index')
    links=select('SELECT x.* FROM observation_entity_links x JOIN market_observations o USING(observation_id) JOIN metric_run_results l USING(metric_result_id) WHERE l.run_id=? ORDER BY x.observation_id,x.entity_id')
    events=select('SELECT x.* FROM observation_event_links x JOIN market_observations o USING(observation_id) JOIN metric_run_results l USING(metric_result_id) WHERE l.run_id=? ORDER BY x.observation_id,x.event_id')
    upstream=event_snapshot(conn,versions[:8],run_id=run['stage11_run_id'])[1] if run['stage11_run_id'] else None
    pointers=select('SELECT s.* FROM article_sightings s JOIN metric_extraction_results r ON s.article_id=r.article_id AND s.raw_hash=r.raw_hash AND s.source_id=r.source_id JOIN metric_run_results l USING(metric_result_id) WHERE l.run_id=? ORDER BY s.sighting_id')
    value=(run,results,observations,links,events,upstream,pointers)
    # Snapshot signature handles malformed SQLite BLOBs without leaking them.
    return identity(json.loads(json.dumps(value,sort_keys=True,default=_sql_value))),value


def raw_urls(pointers):
    """One streaming pass per referenced raw file, never copies raw_payload."""
    grouped=defaultdict(dict);result={}
    for row in pointers: grouped[row['raw_jsonl_path']][row['raw_jsonl_line']]=row
    for path,wanted in grouped.items():
        remaining=set(wanted)
        with open_raw_read(path) as stream:
            for number,line in enumerate(stream,1):
                if number not in wanted: continue
                raw=_parse_and_validate(Path(path),number,line)
                pointer=wanted[number]
                key=(raw.source_id,raw.article_id,raw.raw_hash)
                if key!=tuple(pointer[k] for k in ('source_id','article_id','raw_hash')):
                    raise DatabaseError('Raw provenance mismatch')
                result[key]=raw.raw_url or None;remaining.remove(number)
                if not remaining: break
        if remaining: raise DatabaseError('Missing raw provenance line')
    return result


def decode_metric(row,observations,links,events,entity,event):
    data=dict(row);count=data.pop('observation_count');decoded=[]
    event_ids={e.event_id for e in event.events}
    for row in observations:
        o=dict(row)
        if o.pop('observation_index')!=len(decoded) or o.pop('extraction_id')!=entity.extraction_id or o.pop('event_result_id')!=event.event_result_id:
            raise DatabaseError('Stage 12 observation lineage mismatch')
        associated=[]
        for row in links.get(o['observation_id'],()):
            link=dict(row);link.pop('observation_id')
            if link.pop('extraction_id')!=entity.extraction_id or not 0<=link['mention_index']<len(entity.mentions) or entity.mentions[link['mention_index']].entity_id!=link['entity_id']:
                raise DatabaseError('Stage 12 entity association mismatch')
            associated.append(link)
        ids=[]
        for row in events.get(o['observation_id'],()):
            if row['event_result_id']!=event.event_result_id or row['event_id'] not in event_ids:
                raise DatabaseError('Stage 12 event association mismatch')
            ids.append(row['event_id'])
        decoded.append(o|{'entity_links':associated,'associated_event_ids':ids})
    if count!=len(decoded): raise DatabaseError('Stage 12 observation count mismatch')
    return MetricExtractionResult.model_validate(data|{'events':[],'observations':decoded})


def insert(conn,table,data):
    if table not in TABLES: raise ValueError('Unknown serving table')
    conn.execute('INSERT INTO '+table+' ('+','.join(data)+') VALUES ('+','.join(':'+k for k in data)+')',data)


def publish(conn,bundle,report,policy):
    """Caller owns BEGIN IMMEDIATE and rollback for this entire publication."""
    build=report.build_id
    insert(conn,'intelligence_builds',dict(build_id=build,cohort_hash=report.cohort_hash,stage12_run_id=report.stage12_run_id,
        intelligence_build_version=report.intelligence_build_version,market_movement_version=report.market_movement_version,
        ranking_version=report.ranking_version,policy_id=policy.policy_id,policy_json=json.dumps(asdict(policy),default=str,sort_keys=True),
        created_at=report.started_at,counts_json=json.dumps(report.counts,sort_keys=True)))
    for row in bundle.articles: insert(conn,'intelligence_articles',dict(build_id=build,**row))
    for row in bundle.entities: insert(conn,'intelligence_article_entities',dict(build_id=build,**row))
    for row in bundle.events: insert(conn,'intelligence_events',dict(build_id=build,**row))
    for row in bundle.event_links: insert(conn,'intelligence_event_entities',dict(build_id=build,**row))
    for series in bundle.series: insert(conn,'market_series',dict(build_id=build,series_id=series.series_id,**asdict(series)))
    for row in bundle.observations: insert(conn,'intelligence_observations',dict(build_id=build,**row))
    for m in bundle.movements:
        insert(conn,'market_movements',dict(build_id=build,movement_id=m.movement_id,series_id=m.current.series.series_id,
            current_observation_id=m.current.observation_id,comparison_observation_id=m.previous.observation_id,basis=m.basis,
            period=m.current.period.label,change_pct=decimal_text(m.change_pct),classification=m.classification,
            provenance='SYSTEM_CALCULATED',market_movement_version=m.version,policy_id=m.policy_id))
    for oid,basis,reason in bundle.unavailable:
        insert(conn,'market_movement_unavailable',dict(build_id=build,observation_id=oid,basis=basis,reason=reason))
    for ranking in bundle.rankings:
        insert(conn,'market_rankings',dict(build_id=build,ranking_id=ranking['ranking_id'],**ranking['dimensions']))
        for entry in ranking['entries']:
            insert(conn,'market_ranking_entries',dict(build_id=build,ranking_id=ranking['ranking_id'],**entry))


def load_movements(conn,build_id):
    return [dict(row) for row in conn.execute('SELECT * FROM market_movements WHERE build_id=? ORDER BY movement_id',(build_id,))]
