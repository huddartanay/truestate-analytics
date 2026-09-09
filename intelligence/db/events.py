"""Stage 11 immutable input snapshot and relational event persistence."""
from __future__ import annotations
import json
import hashlib

from intelligence.db.cleaning import ensure_cleaning_schema as ensure_event_schema
from intelligence.db.entities import STAGE8_KEY, STAGE9_KEY
from intelligence.db.snapshots import _sql_value
from intelligence.events.identity import result_id
from intelligence.errors import DatabaseError
from intelligence.schemas import EntityExtractionResult, EventExtractionResult

VERSION_FIELDS = ('cleaning_version','dedup_version','relevance_version','uae_relevance_version',
                  'registry_version','entity_extraction_version','entity_registry_version')


def snapshot(conn, versions, *, run_id=None):
    where = ' AND '.join(k+'=?' for k in VERSION_FIELDS)
    row = conn.execute("SELECT * FROM entity_extraction_run_log WHERE " + where +
        " AND status IN ('SUCCESS','PARTIAL_SUCCESS') AND completed_at IS NOT NULL ORDER BY completed_at DESC,rowid DESC LIMIT 1", versions).fetchone()
    if run_id is not None:
        row = conn.execute('SELECT * FROM entity_extraction_run_log WHERE run_id=? AND '+where,(run_id,*versions)).fetchone()
        if not row or row['status'] not in ('SUCCESS','PARTIAL_SUCCESS') or not row['completed_at']:
            raise DatabaseError('Missing anchored completed Stage 10 run')
    run = dict(row) if row else None
    results = [dict(r) for r in conn.execute('SELECT r.* FROM entity_extraction_results r JOIN entity_extraction_run_results l USING(extraction_id) WHERE l.run_id=? ORDER BY r.extraction_id', (run['run_id'],))] if run else []
    if run and len(results)!=conn.execute('SELECT count(*) FROM entity_extraction_run_results WHERE run_id=?',(run['run_id'],)).fetchone()[0]:
        raise DatabaseError('Unresolved Stage 10 run reference')
    mentions = [dict(r) for r in conn.execute('SELECT m.* FROM entity_mentions m JOIN entity_extraction_run_results l USING(extraction_id) WHERE l.run_id=? ORDER BY m.extraction_id,m.mention_index',(run['run_id'],))] if run else []
    # Anchor to the Stage 9/8 runs that produced this Stage 10 cohort, even when
    # newer upstream runs exist and have not yet been processed by Stage 10.
    run9 = conn.execute('SELECT * FROM uae_relevance_run_log WHERE run_id=?',(run['stage9_run_id'],)).fetchone() if run else None
    run9 = dict(run9) if run9 else None
    run8 = conn.execute('SELECT * FROM relevance_run_log WHERE run_id=?',(run9['stage8_run_id'],)).fetchone() if run9 else None
    run8 = dict(run8) if run8 else None
    if results and (not run9 or not run8 or not run9['completed_at'] or not run8['completed_at']
                    or run9['status'] not in ('SUCCESS','PARTIAL_SUCCESS') or run8['status'] not in ('SUCCESS','PARTIAL_SUCCESS')):
        raise DatabaseError('Missing completed upstream run provenance')
    stage9 = [dict(r) for r in conn.execute('SELECT r.* FROM uae_real_estate_relevance r JOIN uae_relevance_run_results l USING('+','.join(STAGE9_KEY)+') WHERE l.run_id=? ORDER BY r.article_id,r.raw_hash,r.context_id',(run9['run_id'],))] if run9 else []
    stage8 = [dict(r) for r in conn.execute('SELECT r.* FROM real_estate_relevance r JOIN relevance_run_results l USING('+','.join(STAGE8_KEY)+') WHERE l.run_id=? ORDER BY r.article_id,r.raw_hash,r.context_id',(run8['run_id'],))] if run8 else []
    cleaned = [dict(r) for r in conn.execute('SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash',versions[:1])]
    groups = [dict(r) for r in conn.execute('SELECT * FROM duplicate_groups WHERE cleaning_version=? AND dedup_version=? ORDER BY group_id',versions[:2])]
    value = (run, results, mentions, run9, run8, stage9, stage8, cleaned, groups)
    signature = hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=_sql_value).encode()).hexdigest()
    return signature,value


def decode_entity(row, mentions):
    data = dict(row)
    count = data.pop('mention_count')
    decoded = []
    for row in mentions:
        mention = dict(row)
        if mention.pop('extraction_id')!=data['extraction_id'] or mention.pop('mention_index')!=len(decoded):
            raise DatabaseError('Invalid Stage 10 mention sequence')
        decoded.append(mention)
    if count!=len(decoded):
        raise DatabaseError('Invalid Stage 10 mention count')
    return EntityExtractionResult.model_validate(data|{'mentions':decoded,'entity_ids':sorted({m['entity_id'] for m in decoded})})


def existing_ids(conn, version):
    return {r[0] for r in conn.execute('SELECT event_result_id FROM event_extraction_results WHERE event_extraction_version=?',(version,))}


def save_result(conn, result):
    data = result.model_dump(mode='json')
    events = data.pop('events')
    data['event_count'] = len(events)
    inserted = conn.execute('INSERT INTO event_extraction_results ('+','.join(data)+') VALUES ('+','.join(':'+k for k in data)+') ON CONFLICT DO NOTHING',data).rowcount==1
    if not inserted:
        return False
    for index, event in enumerate(events):
        links = event.pop('entity_links')
        event.update(extraction_id=result.extraction_id,event_index=index)
        conn.execute('INSERT INTO real_estate_event_instances ('+','.join(event)+') VALUES ('+','.join(':'+k for k in event)+')',event)
        for link in links:
            row = dict(event_id=event['event_id'],extraction_id=result.extraction_id,**link)
            conn.execute('INSERT INTO event_entity_links ('+','.join(row)+') VALUES ('+','.join(':'+k for k in row)+')',row)
    return True


def link_result(conn, run_id, identity):
    conn.execute('INSERT INTO event_run_results VALUES (?,?) ON CONFLICT DO NOTHING',(run_id,identity))


def load_result(conn, identity):
    row = conn.execute('SELECT * FROM event_extraction_results WHERE event_result_id=?',(identity,)).fetchone()
    if row is None:
        raise DatabaseError('Event extraction result not found')
    data = dict(row)
    count = data.pop('event_count')
    events = []
    for row in conn.execute('SELECT * FROM real_estate_event_instances WHERE event_result_id=? ORDER BY event_index',(identity,)):
        event = dict(row)
        if event.pop('event_index')!=len(events) or event.pop('extraction_id')!=data['extraction_id']:
            raise DatabaseError('Invalid event sequence or lineage')
        links = []
        for row in conn.execute('SELECT l.*,m.entity_id AS mentioned_entity FROM event_entity_links l JOIN entity_mentions m USING(extraction_id,mention_index) WHERE l.event_id=? ORDER BY l.entity_id',(event['event_id'],)):
            link = dict(row)
            if link.pop('mentioned_entity')!=link['entity_id'] or link.pop('extraction_id')!=data['extraction_id']:
                raise DatabaseError('Entity link disagrees with Stage 10 mention')
            link.pop('event_id')
            links.append(link)
        if len(links)!=conn.execute('SELECT count(*) FROM event_entity_links WHERE event_id=?',(event['event_id'],)).fetchone()[0]:
            raise DatabaseError('Unresolved event entity link')
        event['entity_links'] = links
        events.append(event)
    if count!=len(events):
        raise DatabaseError('Event count disagrees with extraction result')
    return EventExtractionResult.model_validate(data|{'events':events})
