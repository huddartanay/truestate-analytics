"""
SQLite connection factories and schema application.

Two access modes:

    connect_rw()   read-write, used by the pipeline. WAL mode, FKs on,
                   NORMAL synchronous (safe with WAL on commit boundaries).
    connect_ro()   read-only, used by the Streamlit UI in later stages.

`apply_schema()` runs `schema.sql` idempotently and stamps `schema_meta`
with the SCHEMA_VERSION from config.

Stage 4 uses only these two tables from the schema: feed_run_log,
article_sightings. The full intelligence schema lands in Stage 13.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from intelligence import config as _cfg
from intelligence.errors import DatabaseError

SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema.sql"


def _db_path_default() -> Path:
    """Look up DB_PATH from config at call time so tests can patch it."""
    return _cfg.DB_PATH


def _apply_pragmas(conn: sqlite3.Connection, *, write: bool) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    if write:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")


def connect_rw(db_path: Path | str | None = None) -> sqlite3.Connection:
    """
    Open a read-write connection. Caller is responsible for closing it.
    Prefer `with connect_rw() as conn:` to guarantee transactional commit.
    """
    p = Path(db_path if db_path is not None else _db_path_default())
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(
            str(p),
            timeout=10.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
    except sqlite3.Error as e:  # pragma: no cover
        raise DatabaseError(f"Could not open {p}: {e}") from e
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn, write=True)
    return conn


def connect_ro(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a strictly read-only connection (safe for the UI to hold)."""
    p = Path(db_path if db_path is not None else _db_path_default())
    if not p.exists():
        raise DatabaseError(f"Database not initialised at {p}. Run `apply_schema` first.")
    try:
        conn = sqlite3.connect(
            f"file:{p}?mode=ro", uri=True,
            timeout=5.0, detect_types=sqlite3.PARSE_DECLTYPES,
        )
    except sqlite3.Error as e:  # pragma: no cover
        raise DatabaseError(f"Could not open {p} read-only: {e}") from e
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn, write=False)
    return conn


def apply_schema(db_path: Path | str | None = None) -> None:
    """
    Idempotently apply `schema.sql` and record the applied version.

    Safe to call at every process start; CREATE TABLE IF NOT EXISTS makes
    running it against an already-migrated DB a no-op.
    """
    _cfg.ensure_data_dirs()
    sql = SCHEMA_SQL_PATH.read_text()
    p = Path(db_path if db_path is not None else _db_path_default())
    # Shared additive migration validates the version and commits DDL/stamp
    # atomically. Import locally because the migration module uses this factory.
    from contextlib import closing
    from intelligence.db.cleaning import ensure_cleaning_schema
    with closing(connect_rw(p)) as conn:
        ensure_cleaning_schema(conn)


def ensure_ready(db_path: Path | str | None = None) -> None:
    """
    Convenience wrapper: creates the data dir, applies the schema if the DB
    is missing or the schema tables are absent, no-op otherwise.
    """
    p = Path(db_path if db_path is not None else _db_path_default())
    if not p.exists():
        apply_schema(p)
        return
    with connect_ro(p) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feed_run_log'"
        ).fetchone()
    if row is None:
        apply_schema(p)


__all__ = ["apply_schema", "connect_rw", "connect_ro", "ensure_ready"]
