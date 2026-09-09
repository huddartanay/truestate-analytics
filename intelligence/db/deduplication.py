"""Stage 7 persistence; never writes to raw or cleaned article storage."""

from __future__ import annotations

import json
import sqlite3

from intelligence.db.cleaning import ensure_cleaning_schema
from intelligence.deduplication.compare import Comparison
from intelligence.deduplication.groups import DuplicateGroup
from intelligence.deduplication.normalize import Identity


def ensure_dedup_schema(conn: sqlite3.Connection) -> None:
    """Reuse the shared atomic additive schema path; does not run cleaning."""
    ensure_cleaning_schema(conn)


def load_pairs(conn: sqlite3.Connection, cleaning_version: str, dedup_version: str) -> dict:
    rows = conn.execute(
        "SELECT left_article_id, left_raw_hash, right_article_id, right_raw_hash, duplicate_type "
        "FROM article_duplicate_pairs WHERE cleaning_version=? AND dedup_version=?",
        (cleaning_version, dedup_version),
    )
    return {((r[0], r[1]), (r[2], r[3])): r[4] for r in rows}


def save_pair(conn: sqlite3.Connection, a: Identity, b: Identity, result: Comparison,
              *, cleaning_version: str, dedup_version: str, created_at: str) -> bool:
    """Canonicalize both endpoints, insert once, never overwrite old scores."""
    if result.duplicate_type == "NOT_DUPLICATE":
        return False
    left, right = sorted((a, b))
    cursor = conn.execute(
        "INSERT INTO article_duplicate_pairs "
        "(cleaning_version,dedup_version,left_article_id,left_raw_hash,right_article_id,right_raw_hash,"
        "duplicate_type,exact_fingerprint,title_similarity,body_similarity,overall_similarity,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT (cleaning_version,dedup_version,left_article_id,left_raw_hash,right_article_id,right_raw_hash) DO NOTHING",
        (cleaning_version, dedup_version, *left, *right, result.duplicate_type,
         result.exact_fingerprint, result.title_similarity, result.body_similarity,
         result.overall_similarity, created_at),
    )
    return cursor.rowcount == 1


def save_group(conn: sqlite3.Connection, group: DuplicateGroup, *, run_id: str,
               cleaning_version: str, dedup_version: str, created_at: str) -> bool:
    cursor = conn.execute(
        "INSERT INTO duplicate_groups (cleaning_version,dedup_version,group_id,canonical_article_id,"
        "canonical_raw_hash,member_count,members_json,created_at) VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT (cleaning_version,dedup_version,group_id) DO NOTHING",
        (cleaning_version, dedup_version, group.group_id, *group.canonical, len(group.members),
         json.dumps(group.members, separators=(",", ":")), created_at),
    )
    inserted = cursor.rowcount == 1
    conn.execute(
        "INSERT INTO dedup_run_groups VALUES (?,?,?,?) ON CONFLICT (run_id,group_id) DO NOTHING",
        (run_id, cleaning_version, dedup_version, group.group_id),
    )
    return inserted


def groups_for_run(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """Return that run's group snapshots; older snapshots remain queryable."""
    return [dict(row) for row in conn.execute(
        "SELECT g.* FROM duplicate_groups g JOIN dedup_run_groups r "
        "USING (cleaning_version,dedup_version,group_id) WHERE r.run_id=? ORDER BY g.group_id",
        (run_id,),
    )]
