"""Anchored Stage 11 snapshots and exact relational observation persistence."""
import hashlib
import json
from intelligence.db.cleaning import ensure_cleaning_schema as ensure_metric_schema
from intelligence.db.events import snapshot as entity_snapshot, VERSION_FIELDS as ENTITY_VERSIONS
from intelligence.db.snapshots import _sql_value
from intelligence.errors import DatabaseError
from intelligence.schemas import EventExtractionResult,MetricExtractionResult

VERSION_FIELDS=ENTITY_VERSIONS+('event_extraction_version',)


def snapshot(conn,versions,*,run_id=None):
    where=' AND '.join(k+'=?' for k in VERSION_FIELDS)
    params=tuple(versions)
    if run_id is not None:
        where+=' AND run_id=?';params+=(run_id,)
    row=conn.execute("SELECT * FROM event_run_log WHERE "+where+" AND status IN ('SUCCESS','PARTIAL_SUCCESS') AND completed_at IS NOT NULL ORDER BY completed_at DESC,rowid DESC LIMIT 1",params).fetchone()
    if run_id is not None and row is None: raise DatabaseError('Missing anchored Stage 11 run')
    run=dict(row) if row else None
    results=[dict(r) for r in conn.execute('SELECT r.* FROM event_extraction_results r JOIN event_run_results l USING(event_result_id) WHERE l.run_id=? ORDER BY r.event_result_id',(run['run_id'],))] if run else []
    if run and len(results)!=conn.execute('SELECT count(*) FROM event_run_results WHERE run_id=?',(run['run_id'],)).fetchone()[0]:
        raise DatabaseError('Unresolved Stage 11 run reference')
    if results and not run['stage10_run_id']:
        raise DatabaseError('Missing Stage 11 cohort provenance')
    instances=[dict(r) for r in conn.execute('SELECT e.* FROM real_estate_event_instances e JOIN event_run_results l USING(event_result_id) WHERE l.run_id=? ORDER BY e.event_result_id,e.event_index',(run['run_id'],))] if run else []
    links=[dict(r) for r in conn.execute('SELECT x.* FROM event_entity_links x JOIN real_estate_event_instances e USING(event_id) JOIN event_run_results l USING(event_result_id) WHERE l.run_id=? ORDER BY x.event_id,x.entity_id',(run['run_id'],))] if run else []
    upstream=entity_snapshot(conn,versions[:7],run_id=run['stage10_run_id'])[1] if run and run['stage10_run_id'] else (None,[],[],None,None,[],[],[],[])
    value=(run,results,instances,links,upstream)
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=_sql_value).encode()).hexdigest(),value


def decode_event(row,instances,links,entity):
    data=dict(row);count=data.pop('event_count');events=[]
    for row in instances:
        event=dict(row)
        if event.pop('event_index')!=len(events) or event.pop('extraction_id')!=entity.extraction_id:
            raise DatabaseError('Invalid Stage 11 sequence or entity lineage')
        decoded=[]
        for row in links.get(event['event_id'],[]):
            link=dict(row);link.pop('event_id')
            if link.pop('extraction_id')!=entity.extraction_id or not 0<=link['mention_index']<len(entity.mentions) or entity.mentions[link['mention_index']].entity_id!=link['entity_id']:
                raise DatabaseError('Invalid Stage 11 entity link')
            decoded.append(link)
        events.append(event|{'entity_links':decoded})
    if len(events)!=count: raise DatabaseError('Invalid Stage 11 event count')
    return EventExtractionResult.model_validate(data|{'events':events})


def existing_ids(conn,version):
    return {r[0] for r in conn.execute('SELECT metric_result_id FROM metric_extraction_results WHERE metric_extraction_version=?',(version,))}


def save_result(conn,result):
    data=result.model_dump(mode='json');observations=data.pop('observations');data.pop('events')
    data['observation_count']=len(observations)
    if conn.execute('INSERT INTO metric_extraction_results ('+','.join(data)+') VALUES ('+','.join(':'+k for k in data)+') ON CONFLICT DO NOTHING',data).rowcount!=1:
        return False
    for index,o in enumerate(observations):
        links=o.pop('entity_links');events=o.pop('associated_event_ids')
        o.update(extraction_id=result.extraction_id,event_result_id=result.event_result_id,observation_index=index)
        conn.execute('INSERT INTO market_observations ('+','.join(o)+') VALUES ('+','.join(':'+k for k in o)+')',o)
        for link in links:
            data=dict(observation_id=o['observation_id'],extraction_id=result.extraction_id,**link)
            conn.execute('INSERT INTO observation_entity_links ('+','.join(data)+') VALUES ('+','.join(':'+k for k in data)+')',data)
        for event in events:
            conn.execute('INSERT INTO observation_event_links VALUES (?,?,?)',(o['observation_id'],result.event_result_id,event))
    return True


def link_result(conn,run_id,identity):
    conn.execute('INSERT INTO metric_run_results VALUES (?,?) ON CONFLICT DO NOTHING',(run_id,identity))


def load_result(conn,identity):
    row=conn.execute('SELECT * FROM metric_extraction_results WHERE metric_result_id=?',(identity,)).fetchone()
    if row is None: raise DatabaseError('Metric result missing')
    data=dict(row);count=data.pop('observation_count');observations=[]
    for row in conn.execute('SELECT * FROM market_observations WHERE metric_result_id=? ORDER BY observation_index',(identity,)):
        o=dict(row)
        if o.pop('observation_index')!=len(observations) or o.pop('extraction_id')!=data['extraction_id'] or o.pop('event_result_id')!=data['event_result_id']:
            raise DatabaseError('Observation lineage or sequence mismatch')
        links=[]
        for row in conn.execute('SELECT l.*,m.entity_id AS mentioned_entity FROM observation_entity_links l LEFT JOIN entity_mentions m USING(extraction_id,mention_index) WHERE observation_id=? ORDER BY l.entity_id',(o['observation_id'],)):
            link=dict(row);link.pop('observation_id')
            if link.pop('extraction_id')!=data['extraction_id'] or link.pop('mentioned_entity')!=link['entity_id']:
                raise DatabaseError('Observation mention mismatch')
            links.append(link)
        events=[]
        for row in conn.execute('SELECT l.*,e.event_result_id AS parent_result FROM observation_event_links l LEFT JOIN real_estate_event_instances e USING(event_id) WHERE observation_id=? ORDER BY l.event_id',(o['observation_id'],)):
            if row['parent_result']!=data['event_result_id'] or row['event_result_id']!=data['event_result_id']:
                raise DatabaseError('Observation event mismatch')
            events.append(row['event_id'])
        observations.append(o|{'entity_links':links,'associated_event_ids':events})
    if count!=len(observations): raise DatabaseError('Observation count mismatch')
    return MetricExtractionResult.model_validate(data|{'events':[],'observations':observations})
