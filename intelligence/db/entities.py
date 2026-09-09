"""Stage 10 snapshots and relational mention persistence."""
from __future__ import annotations
import hashlib
import json

from intelligence.db.cleaning import ensure_cleaning_schema
from intelligence.db.uae_relevance import KEY as STAGE9_KEY
from intelligence.db.relevance import KEY as STAGE8_KEY
from intelligence.db.snapshots import _sql_value
from intelligence.errors import DatabaseError
from intelligence.schemas import EntityExtractionResult

KEY=STAGE9_KEY+('entity_extraction_version','entity_registry_version')


def ensure_entity_schema(conn):
    ensure_cleaning_schema(conn)


def snapshot(conn,versions):
    row=conn.execute("SELECT * FROM uae_relevance_run_log WHERE cleaning_version=? AND dedup_version=? AND relevance_version=? AND uae_relevance_version=? AND registry_version=? AND status IN ('SUCCESS','PARTIAL_SUCCESS') ORDER BY completed_at DESC,rowid DESC LIMIT 1",versions).fetchone()
    run=dict(row) if row else None
    stage9=[dict(r) for r in conn.execute('SELECT r.* FROM uae_real_estate_relevance r JOIN uae_relevance_run_results l USING('+','.join(STAGE9_KEY)+') WHERE l.run_id=? ORDER BY r.article_id,r.raw_hash,r.context_id',(run['run_id'],))] if run else []
    if run and len(stage9)!=conn.execute('SELECT count(*) FROM uae_relevance_run_results WHERE run_id=?',(run['run_id'],)).fetchone()[0]:
        raise DatabaseError('Unresolved Stage 9 result reference')
    stage8=[dict(r) for r in conn.execute('SELECT * FROM real_estate_relevance WHERE cleaning_version=? AND dedup_version=? AND relevance_version=? ORDER BY article_id,raw_hash,context_id',versions[:3])]
    links=[tuple(r) for r in conn.execute('SELECT '+','.join(STAGE8_KEY)+' FROM relevance_run_results WHERE run_id=? ORDER BY article_id,raw_hash,context_id',(run['stage8_run_id'],))] if run else []
    cleaned=[dict(r) for r in conn.execute('SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash',versions[:1])]
    groups=[dict(r) for r in conn.execute('SELECT * FROM duplicate_groups WHERE cleaning_version=? AND dedup_version=? ORDER BY group_id',versions[:2])]
    value=(run,stage9,stage8,links,cleaned,groups)
    signature=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=_sql_value).encode()).hexdigest()
    return signature,value


def extraction_id(upstream,extraction_version,registry_version):
    key=[getattr(upstream,k) for k in STAGE9_KEY]+[extraction_version,registry_version]
    return hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()


def existing_ids(conn,versions):
    return {r[0] for r in conn.execute('SELECT extraction_id FROM entity_extraction_results WHERE cleaning_version=? AND dedup_version=? AND relevance_version=? AND uae_relevance_version=? AND registry_version=? AND entity_extraction_version=? AND entity_registry_version=?',versions)}


def save_result(conn,result):
    data=result.model_dump(mode='json');mentions=data.pop('mentions');data.pop('entity_ids');data['mention_count']=len(mentions)
    inserted=conn.execute('INSERT INTO entity_extraction_results ('+','.join(data)+') VALUES ('+','.join(':'+k for k in data)+') ON CONFLICT DO NOTHING',data).rowcount==1
    if not inserted:return False
    for ordinal,mention in enumerate(mentions):
        row={'extraction_id':result.extraction_id,'mention_index':ordinal,**mention}
        conn.execute('INSERT INTO entity_mentions ('+','.join(row)+') VALUES ('+','.join(':'+k for k in row)+')',row)
    return True


def link_result(conn,run_id,identity):
    conn.execute('INSERT INTO entity_extraction_run_results VALUES (?,?) ON CONFLICT DO NOTHING',(run_id,identity))


def load_result(conn,identity):
    row=conn.execute('SELECT * FROM entity_extraction_results WHERE extraction_id=?',(identity,)).fetchone()
    if row is None:raise DatabaseError('Extraction result not found')
    data=dict(row);count=data.pop('mention_count');mentions=[]
    for row in conn.execute('SELECT * FROM entity_mentions WHERE extraction_id=? ORDER BY mention_index',(identity,)):
        m=dict(row);m.pop('extraction_id')
        if m.pop('mention_index')!=len(mentions):raise DatabaseError('Invalid mention sequence')
        mentions.append(m)
    if count!=len(mentions):raise DatabaseError('Mention count does not match result')
    return EntityExtractionResult.model_validate(data|{'mentions':mentions,'entity_ids':sorted({m['entity_id'] for m in mentions})})
