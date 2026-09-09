"""
Read helpers for the raw JSONL layer.

Every helper:

* streams (no full-file loads)
* validates paths against the intelligence raw-storage root
* returns validated ``RawArticleRecord`` instances
* rejects arbitrary filesystem traversal
* raises typed ``StorageError`` subclasses on any problem

None of these helpers modify raw storage or SQLite.
"""

from __future__ import annotations

import json
import errno
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

from intelligence import config as _cfg
from intelligence.db.connection import connect_ro
from intelligence.errors import (
    RawFileMissing,
    RawPathViolation,
    RawPointerInvalid,
    RawRecordInvalid,
)
from intelligence.schemas import RawArticleRecord
from intelligence.storage.rotation import day_partitions, _partition_index


# ─────────────────────────────────────────────────────────────────────────────
# PATH SAFETY
# ─────────────────────────────────────────────────────────────────────────────


def resolve_raw_path(path: Path | str) -> Path:
    """
    Resolve ``path`` and verify it lives underneath ``RAW_ARTICLES_DIR``.

    Rejects:
      * absolute paths outside the raw root
      * relative paths containing ``..`` that escape the raw root
      * symlinks that point outside the raw root
      * non-jsonl files

    Raises :class:`RawPathViolation` on any violation.
    """
    raw_root = _cfg.RAW_ARTICLES_DIR.resolve()
    p = Path(path)
    # Reject absolute paths that are not already inside raw_root
    if p.is_absolute():
        candidate = p.resolve()
    else:
        candidate = (raw_root / p).resolve()

    try:
        candidate.relative_to(raw_root)
    except ValueError:
        raise RawPathViolation(
            f"Path {path!r} resolves to {candidate!s}, which is outside "
            f"{raw_root!s}."
        ) from None

    if candidate.suffix != ".jsonl":
        raise RawPathViolation(f"Only .jsonl files are permitted (got {candidate.name!r})")

    return candidate


# ─────────────────────────────────────────────────────────────────────────────
# STREAMING READ
# ─────────────────────────────────────────────────────────────────────────────


@contextmanager
def open_raw_read(path: Path | str):
    """Validate confinement and open through no-follow directory descriptors.

    Existing internal symlinks resolve to their confined target. Replacing a
    resolved component with a symlink between checking and opening is rejected.
    The configured root and its ancestors remain trusted deployment paths.
    """
    safe = resolve_raw_path(path)
    root = _cfg.RAW_ARTICLES_DIR.resolve()
    parts = safe.relative_to(root).parts
    directory = fd = None
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in parts[:-1]:
            next_dir = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_dir
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        stream = os.fdopen(fd, 'r', encoding='utf-8')
        fd = None  # Stream now owns the descriptor.
        with stream:
            yield stream
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise RawPathViolation('Raw path changed or contains an unsafe link') from exc
        raise
    finally:
        if fd is not None:
            os.close(fd)
        if directory is not None:
            os.close(directory)


def _iter_lines(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (line_number_1_based, raw_line_without_newline) for a JSONL file."""
    with open_raw_read(path) as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            yield lineno, line


def _parse_and_validate(path: Path, lineno: int, line: str) -> RawArticleRecord:
    """Parse one JSONL line + validate against RawArticleRecord."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as e:
        raise RawRecordInvalid(
            f"{path.name}:{lineno} — invalid JSON: {e.msg} (col {e.colno})"
        ) from e
    try:
        return RawArticleRecord.model_validate(obj)
    except Exception as e:
        raise RawRecordInvalid(
            f"{path.name}:{lineno} — schema validation failed ({type(e).__name__})"
        ) from e


def iter_raw(day: date | str, *, on_error: Callable[[RawRecordInvalid], None] | None = None) -> Iterator[RawArticleRecord]:
    """
    Stream every valid raw record for ``day`` in write order (base partition
    first, then .01, .02, ...). Skips blank lines. Malformed lines raise
    :class:`RawRecordInvalid` by default, ending the generator. To continue,
    supply an on_error callback which receives each typed file/line error.
    Errors are never silently discarded and raw bytes are never repaired.
    """
    day_iso = day if isinstance(day, str) else day.isoformat()
    for path in day_partitions(day_iso):
        for lineno, line in _iter_lines(path):
            try:
                yield _parse_and_validate(path, lineno, line)
            except RawRecordInvalid as exc:
                if on_error is None:
                    raise
                on_error(exc)


def iter_raw_since(dt: datetime, *, on_error: Callable[[RawRecordInvalid], None] | None = None) -> Iterator[RawArticleRecord]:
    """
    Stream every valid raw record with ``retrieved_at >= dt``, walking all
    existing partitions, independent of their filenames' dates. Both cutoff
    and compared retrieval timestamps must be aware; never assign a timezone.
    """
    if dt.utcoffset() is None:
        raise RawRecordInvalid('Retrieval cutoff must be timezone-aware')
    dt = dt.astimezone(timezone.utc)

    raw_root = _cfg.RAW_ARTICLES_DIR
    if not raw_root.exists():
        return

    # Collect every calendar day that has a partition on disk, then filter.
    days: set[str] = set()
    for p in raw_root.iterdir():
        if _partition_index(p.name, p.name[:10]) is not None:
            days.add(p.name[:10])
    for day in sorted(days):
        for path in day_partitions(day):
            for lineno, line in _iter_lines(path):
                try:
                    rec = _parse_and_validate(path, lineno, line)
                    if rec.retrieved_at.utcoffset() is None:
                        raise RawRecordInvalid(f'{path.name}:{lineno} — retrieval timestamp has no timezone')
                    if rec.retrieved_at >= dt:
                        yield rec
                except RawRecordInvalid as exc:
                    if on_error is None:
                        raise
                    on_error(exc)


# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP BY SIGHTING
# ─────────────────────────────────────────────────────────────────────────────


def _read_specific_line(path: Path, target_line: int) -> str:
    """Read one specific 1-based line efficiently. Streams up to the target."""
    with open_raw_read(path) as fh:
        for lineno, line in enumerate(fh, start=1):
            if lineno == target_line:
                return line.rstrip("\n").rstrip("\r")
    raise RawPointerInvalid(
        f"{path.name} has fewer than {target_line} lines"
    )


def lookup_raw(sighting_id: str) -> RawArticleRecord:
    """
    Resolve one ``article_sightings.sighting_id`` to a validated raw record.

    Chain:

        1. SELECT the sighting row (raw_jsonl_path, raw_jsonl_line,
           article_id, raw_hash, source_id) from article_sightings.
        2. Path-check raw_jsonl_path against the raw-storage root.
        3. Confirm the file exists.
        4. Read the specific line.
        5. Parse + validate as RawArticleRecord.
        6. Cross-check that article_id + raw_hash + source_id match the
           sighting row (guards against a stale or corrupt pointer).

    Raises :class:`RawPointerInvalid` on any mismatch,
    :class:`RawFileMissing` when the file is absent, and
    :class:`RawPathViolation` if the pointer would escape the raw root.
    """
    with connect_ro() as conn:
        row = conn.execute(
            "SELECT sighting_id, source_id, article_id, raw_hash, "
            "       raw_jsonl_path, raw_jsonl_line "
            "FROM article_sightings WHERE sighting_id = ?",
            (sighting_id,),
        ).fetchone()

    if row is None:
        raise RawPointerInvalid(f"No article_sightings row for sighting_id={sighting_id!r}")

    path = resolve_raw_path(row["raw_jsonl_path"])
    if not path.exists():
        raise RawFileMissing(f"{path.name} does not exist on disk")

    line = _read_specific_line(path, int(row["raw_jsonl_line"]))
    record = _parse_and_validate(path, int(row["raw_jsonl_line"]), line)

    if record.article_id != row["article_id"]:
        raise RawPointerInvalid(
            f"article_id mismatch: sighting={row['article_id']}, "
            f"record={record.article_id} at {path.name}:{row['raw_jsonl_line']}"
        )
    if record.raw_hash != row["raw_hash"]:
        raise RawPointerInvalid(
            f"raw_hash mismatch: sighting={row['raw_hash']}, "
            f"record={record.raw_hash} at {path.name}:{row['raw_jsonl_line']}"
        )
    if record.source_id != row["source_id"]:
        raise RawPointerInvalid(
            f"source_id mismatch: sighting={row['source_id']}, "
            f"record={record.source_id} at {path.name}:{row['raw_jsonl_line']}"
        )
    return record


__all__ = ["resolve_raw_path", "open_raw_read", "iter_raw", "iter_raw_since", "lookup_raw"]
