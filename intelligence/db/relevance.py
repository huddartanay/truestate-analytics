"""Stage 8 parameterized persistence and immutable canonical context lookup."""

from __future__ import annotations

import hashlib
import json

from intelligence.db.cleaning import ensure_cleaning_schema

KEY = ('article_id', 'raw_hash', 'cleaning_version', 'dedup_version', 'relevance_version', 'context_id')


def ensure_relevance_schema(conn):
    ensure_cleaning_schema(conn)


def latest_context(conn, cleaning_version, dedup_version):
    # A single completed run avoids overlapping historical membership snapshots.
    # rowid breaks an operational timestamp tie without arbitrary UUID ordering.
    row = conn.execute(
        "SELECT run_id FROM dedup_run_log WHERE cleaning_version=? AND dedup_version=? "
        "AND status IN ('SUCCESS','PARTIAL_SUCCESS') ORDER BY completed_at DESC,rowid DESC LIMIT 1",
        (cleaning_version, dedup_version),
    ).fetchone()
    run_id = row[0] if row else None
    groups = [dict(r) for r in conn.execute(
        'SELECT g.* FROM duplicate_groups g JOIN dedup_run_groups r '
        'USING(cleaning_version,dedup_version,group_id) WHERE r.run_id=? ORDER BY g.group_id',
        (run_id,),
    )] if run_id else []
    return run_id, groups


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def context_id(article, dedup_version, group_id):
    return digest([article.cleaning_version, dedup_version, group_id, article.article_id, article.raw_hash])


def result_key(article, dedup_version, relevance_version, context):
    return (article.article_id, article.raw_hash, article.cleaning_version, dedup_version, relevance_version, context)


def existing_keys(conn, cleaning_version, dedup_version, relevance_version):
    return {tuple(row) for row in conn.execute(
        'SELECT ' + ','.join(KEY) + ' FROM real_estate_relevance WHERE cleaning_version=? AND dedup_version=? AND relevance_version=?',
        (cleaning_version, dedup_version, relevance_version),
    )}


def save_result(conn, result):
    data = result.model_dump(mode='json')
    for name in ('matched_positive_signals', 'matched_negative_signals'):
        data[name] = json.dumps(data[name], ensure_ascii=True, separators=(',', ':'))
    cursor = conn.execute(
        'INSERT INTO real_estate_relevance (' + ','.join(data) + ') VALUES (' +
        ','.join(':' + k for k in data) + ') ON CONFLICT (' + ','.join(KEY) + ') DO NOTHING', data,
    )
    return cursor.rowcount == 1


def link_result(conn, run_id, key):
    conn.execute('INSERT INTO relevance_run_results VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING', (run_id, *key))
