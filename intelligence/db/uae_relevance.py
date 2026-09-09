"""Stage 9 persistence and a single completed Stage 8 run's input snapshot."""
from __future__ import annotations

import hashlib
import json

from intelligence.db.cleaning import ensure_cleaning_schema
from intelligence.db.relevance import KEY as STAGE8_KEY
from intelligence.db.snapshots import _sql_value
from intelligence.errors import DatabaseError

KEY = STAGE8_KEY + ('uae_relevance_version', 'registry_version')


def ensure_uae_relevance_schema(conn):
    ensure_cleaning_schema(conn)


def snapshot(conn, cleaning_version, dedup_version, relevance_version):
    row = conn.execute(
        "SELECT * FROM relevance_run_log WHERE cleaning_version=? AND dedup_version=? AND relevance_version=? "
        "AND status IN ('SUCCESS','PARTIAL_SUCCESS') ORDER BY completed_at DESC,rowid DESC LIMIT 1",
        (cleaning_version, dedup_version, relevance_version),
    ).fetchone()
    run = dict(row) if row else None
    results = [dict(r) for r in conn.execute(
        'SELECT r.* FROM real_estate_relevance r JOIN relevance_run_results l USING('+','.join(STAGE8_KEY)+') '
        'WHERE l.run_id=? ORDER BY r.article_id,r.raw_hash,r.context_id', (run['run_id'],),
    )] if run else []
    if run and len(results) != conn.execute('SELECT count(*) FROM relevance_run_results WHERE run_id=?', (run['run_id'],)).fetchone()[0]:
        raise DatabaseError('Stage 8 run contains an unresolved result reference')
    cleaned = [dict(r) for r in conn.execute(
        'SELECT * FROM cleaned_articles WHERE cleaning_version=? ORDER BY article_id,raw_hash', (cleaning_version,))]
    groups = [dict(r) for r in conn.execute(
        'SELECT * FROM duplicate_groups WHERE cleaning_version=? AND dedup_version=? ORDER BY group_id',
        (cleaning_version, dedup_version))]
    value = (run, results, cleaned, groups)
    signature = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=_sql_value).encode()).hexdigest()
    return signature, value


def key_for(upstream, uae_version, registry_version):
    return tuple(getattr(upstream,k) for k in STAGE8_KEY) + (uae_version, registry_version)


def existing_keys(conn, versions):
    return {tuple(r) for r in conn.execute('SELECT '+','.join(KEY)+' FROM uae_real_estate_relevance '
        'WHERE cleaning_version=? AND dedup_version=? AND relevance_version=? AND uae_relevance_version=? AND registry_version=?',versions)}


def save_result(conn, result):
    data = result.model_dump(mode='json')
    for key in ('matched_uae_signals','matched_exclusion_signals'):
        data[key] = json.dumps(data[key], ensure_ascii=True, separators=(',', ':'))
    return conn.execute('INSERT INTO uae_real_estate_relevance ('+','.join(data)+') VALUES ('+
        ','.join(':'+k for k in data)+') ON CONFLICT ('+','.join(KEY)+') DO NOTHING',data).rowcount == 1


def link_result(conn, run_id, key):
    conn.execute('INSERT INTO uae_relevance_run_results VALUES ('+','.join('?' for _ in range(9))+') ON CONFLICT DO NOTHING', (run_id,*key))
