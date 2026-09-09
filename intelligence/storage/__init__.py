"""
Raw JSONL storage layer (Stage 5).

The raw layer is the immutable source boundary between RSS ingestion
(Stage 4) and every downstream stage. Nothing here cleans, deduplicates,
classifies, or otherwise transforms article content. It only defines the
storage contract and provides safe, streaming, path-checked access.

Public surface:

    intelligence.storage.raw
        iter_raw(day)                — stream one day's records
        iter_raw_since(dt)           — stream all records with retrieved_at >= dt
        lookup_raw(sighting_id)      — resolve one sighting to a validated record
        resolve_raw_path(path)       — path-safety helper (module-private-ish)

    intelligence.storage.rotation
        current_partition_path(day)  — writer helper used by fetch.py

    intelligence.storage.validate
        CLI: python -m intelligence.storage.validate <file>

    intelligence.storage.check
        CLI: python -m intelligence.storage.check
"""

from intelligence.storage.raw import (
    iter_raw,
    iter_raw_since,
    lookup_raw,
    resolve_raw_path,
)
from intelligence.storage.rotation import (
    current_partition_path,
    day_partitions,
)

__all__ = [
    "iter_raw",
    "iter_raw_since",
    "lookup_raw",
    "resolve_raw_path",
    "current_partition_path",
    "day_partitions",
]
