"""Additive Stage 6 schema readiness and parameterized cleaned persistence.

The fetcher's existing ensure_ready/apply_schema interfaces are unchanged.
Cleaning applies the shared CREATE IF NOT EXISTS schema inside one explicit
transaction, including the version stamp, without creating raw directories.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from intelligence import config as _cfg
from intelligence.db.connection import SCHEMA_SQL_PATH
from intelligence.errors import DatabaseError
from intelligence.schemas import CleanArticle


def ensure_cleaning_schema(conn: sqlite3.Connection) -> None:
    """Apply shared v0.9 additive DDL to empty/v0.1–v0.9 DBs.

    Caller supplies a fresh connection and owns its lifetime. No DROP, ALTER,
    replacement, or updates to Stage 4 records. This is not a general migration
    framework. sqlite3.complete_statement keeps execution in one transaction
    (executescript would commit a previously opened transaction).
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        version = None
        if "schema_meta" in tables:
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = ?", ("schema_version",),
            ).fetchone()
            version = row[0] if row else None
        if version not in (None, "v0.1", "v0.2", "v0.3", "v0.4", "v0.5", "v0.6", "v0.7", "v0.8", "v0.9"):
            raise DatabaseError("Stage 6 cannot migrate this schema version")
        statement = ""
        for line in SCHEMA_SQL_PATH.read_text(encoding="utf-8").splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                conn.execute(statement)
                statement = ""
        conn.execute(
            "INSERT INTO schema_meta (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            ("schema_version", _cfg.SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    except (sqlite3.Error, OSError, DatabaseError) as exc:
        conn.rollback()
        # Do not include SQL, payloads or arbitrary exception text in CLI output.
        raise DatabaseError("Stage 6 additive schema initialization failed") from exc


def already_cleaned(conn: sqlite3.Connection, article_id: str, raw_hash: str,
                    cleaning_version: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM cleaned_articles WHERE article_id=? AND raw_hash=? AND cleaning_version=?",
        (article_id, raw_hash, cleaning_version),
    ).fetchone() is not None


def save_clean_article(conn: sqlite3.Connection, article: CleanArticle) -> bool:
    """Insert once; return whether inserted. Caller commits/rolls back.

    An application-level lookup avoids repeated work; the named SQL conflict
    target is still authoritative when two cleaners race. Never replace a row.
    """
    data = article.model_dump(mode="json")
    cursor = conn.execute(
        "INSERT INTO cleaned_articles "
        "(article_id, raw_hash, cleaning_version, source_id, source_name, rss_url, "
        "retrieved_at, content_type, clean_title, clean_body, normalized_published_at, "
        "detected_language, word_count, date_parse_error) "
        "VALUES (:article_id, :raw_hash, :cleaning_version, :source_id, :source_name, :rss_url, "
        ":retrieved_at, :content_type, :clean_title, :clean_body, :normalized_published_at, "
        ":detected_language, :word_count, :date_parse_error) "
        "ON CONFLICT (article_id, raw_hash, cleaning_version) DO NOTHING",
        data,
    )
    return cursor.rowcount == 1


__all__ = ["ensure_cleaning_schema", "already_cleaned", "save_clean_article"]
