"""
JSONL rotation policy.

Contract
────────
* Daily partitioning is preserved: base file for a day is
  ``YYYY-MM-DD.jsonl``.
* When the current partition would exceed ``RAW_JSONL_MAX_BYTES``, subsequent
  writes go to ``YYYY-MM-DD.NN.jsonl`` where NN is a zero-padded 2-digit
  index starting at ``01`` and incrementing monotonically. NN wraps to
  ``100`` etc. cleanly for very high-volume days.
* Existing files are NEVER renamed. Historical
  ``article_sightings.raw_jsonl_path`` pointers therefore stay valid across
  rotation forever.
* JSON records are never split across files — each JSONL line is a complete
  object. Rotation decisions are made before opening a file for append, on
  a per-record basis.

Public entry point:

    current_partition_path(day) -> Path
        Returns the Path a new record should append to for ``day``.
        Ensures the raw-articles directory exists.

    day_partitions(day) -> list[Path]
        Returns every partition file for ``day``, in write order
        (``YYYY-MM-DD.jsonl`` first, then ``.01``, ``.02``, ...).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from intelligence import config as _cfg

_PARTITION_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\.(\d{2,}))?\.jsonl$")


def _raw_dir() -> Path:
    """Late-bind to allow tests to patch DATA_DIR / RAW_ARTICLES_DIR."""
    p = _cfg.RAW_ARTICLES_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _partition_index(filename: str, day_iso: str) -> Optional[int]:
    """
    Return the partition index for a filename:
        "YYYY-MM-DD.jsonl"      -> 0
        "YYYY-MM-DD.01.jsonl"   -> 1
        "YYYY-MM-DD.42.jsonl"   -> 42
    Files belonging to a different day return None.
    """
    m = _PARTITION_RE.match(filename)
    if not m or m.group(1) != day_iso:
        return None
    return int(m.group(2)) if m.group(2) is not None else 0


def _partition_path(day_iso: str, index: int) -> Path:
    """Materialise a partition path from its index (0 → base, N → .NN)."""
    if index == 0:
        return _raw_dir() / f"{day_iso}.jsonl"
    return _raw_dir() / f"{day_iso}.{index:02d}.jsonl"


def day_partitions(day: date | str) -> list[Path]:
    """
    Every partition for a given day, ordered by write sequence
    (base first, then .01, .02, ...). Returns [] if none exist.
    """
    day_iso = day if isinstance(day, str) else day.isoformat()
    raw_dir = _cfg.RAW_ARTICLES_DIR
    if not raw_dir.exists():
        return []
    hits: list[tuple[int, Path]] = []
    for p in raw_dir.iterdir():
        if not p.is_file():
            continue
        idx = _partition_index(p.name, day_iso)
        if idx is not None:
            hits.append((idx, p))
    return [p for _, p in sorted(hits, key=lambda t: t[0])]


def current_partition_path(day: date | str) -> Path:
    """
    Path that a new record for ``day`` should append to.

    Algorithm (safe under Stage 4's "never rename an existing file" rule):

        1. If ``YYYY-MM-DD.jsonl`` does not exist yet, use it.
        2. Otherwise scan every existing partition for the day, pick the
           highest-indexed one, and:
             - if its size < RAW_JSONL_MAX_BYTES, use it;
             - else create the next partition (``highest+1``) and use it.
    """
    day_iso = day if isinstance(day, str) else day.isoformat()
    limit = _cfg.RAW_JSONL_MAX_BYTES
    partitions = day_partitions(day_iso)

    if not partitions:
        base = _partition_path(day_iso, 0)
        return base

    highest = partitions[-1]
    idx_match = _partition_index(highest.name, day_iso)
    highest_idx = idx_match if idx_match is not None else 0

    if highest.stat().st_size < limit:
        return highest

    return _partition_path(day_iso, highest_idx + 1)


__all__ = ["current_partition_path", "day_partitions"]
