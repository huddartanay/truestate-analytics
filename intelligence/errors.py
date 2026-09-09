"""
Typed exception hierarchy for the intelligence layer.

Every subsystem raises a subclass of `IntelligenceError`. No bare `except:`
clauses. No silent failures. Every caught exception is either re-raised or
recorded to a structured log/table (`feed_run_log`, later `llm_call_log`,
`query_logs`).

Stage 4 introduces the ingestion errors below. Later stages extend the
hierarchy without touching this file's existing types.
"""

from __future__ import annotations


class IntelligenceError(Exception):
    """Root of the intelligence layer's typed exception tree."""


class CleaningError(IntelligenceError):
    """Stage 6 input policy or orchestration failure; never repairs raw data."""


class DuplicateDetectionError(IntelligenceError):
    """Stage 7 policy or comparison failure; source records remain intact."""


class OperationLockError(IntelligenceError):
    """Bounded local advisory lock failed or is unsupported."""


class SnapshotChanged(IntelligenceError):
    """Upstream cohort changed during computation; rerun against a new snapshot."""


# ─────────────────────────────────────────────────────────────────────────────
# INGESTION ERRORS (Stage 4)
# ─────────────────────────────────────────────────────────────────────────────


class IngestionError(IntelligenceError):
    """Base for anything that happens during RSS ingestion."""


class SourceNotRegistered(IngestionError):
    """
    A source_id was requested via CLI or code that is not in the authoritative
    registry. Raised BEFORE any HTTP call is made — enforces the "registry is
    the security boundary" rule.
    """


class SourceNotEnabled(IngestionError):
    """A registered source was requested but its `enabled` flag is False."""


class SourceRSSMissing(IngestionError):
    """A registered source has no rss_url (RSS_UNAVAILABLE). Cannot be fetched."""


class RSSUnavailable(IngestionError):
    """
    The RSS URL could not be reached in a normal way: DNS failure, connection
    refused, TLS error, HTTP 4xx (other than 304), HTTP 5xx. Records the
    HTTP status when available.
    """

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status


class RSSMalformed(IngestionError):
    """
    The URL returned bytes but they do not parse as RSS/Atom, or parsed but
    contained no `<channel>` / feed metadata. Distinguishes malformed content
    from a valid empty feed (see `RSSEmpty` below).
    """


class RSSEmpty(IngestionError):
    """
    The feed parsed cleanly and is a valid RSS/Atom document, but contains
    ZERO entries. Not a fatal error — the fetcher records success with
    entries_seen=0.
    """


class FeedTimeout(IngestionError):
    """Connect or read timed out. Retryable on the next scheduled run."""


class RateLimitedLocally(IngestionError):
    """
    Blocked by our own per-source refresh_interval_minutes guard. Not an
    external failure — the fetcher records `SKIPPED_RATE_LIMIT` and moves on.
    """


class NotModified(IngestionError):
    """
    Server responded 304 Not Modified in response to conditional headers.
    Not a failure — the fetcher records `NOT_MODIFIED` and moves on.
    """


# ─────────────────────────────────────────────────────────────────────────────
# STORAGE ERRORS (Stage 4)
# ─────────────────────────────────────────────────────────────────────────────


class StorageError(IntelligenceError):
    """Base for issues writing to disk or SQLite."""


class DatabaseError(StorageError):
    """SQLite connection, migration or query failure."""


class JSONLWriteError(StorageError):
    """Append to the raw JSONL log failed."""


# ─────────────────────────────────────────────────────────────────────────────
# RAW STORAGE ERRORS (Stage 5)
# ─────────────────────────────────────────────────────────────────────────────


class RawRecordInvalid(StorageError):
    """A JSONL line was not valid JSON or did not validate as RawArticleRecord."""


class RawFileMissing(StorageError):
    """A JSONL file referenced by article_sightings.raw_jsonl_path does not exist."""


class RawPointerInvalid(StorageError):
    """
    An article_sightings pointer (raw_jsonl_path, raw_jsonl_line) is broken:
    the file exists but the line is missing, or the record found there does
    not match the expected article_id / raw_hash.
    """


class RawIntegrityError(StorageError):
    """A cross-check between JSONL and SQLite found a discrepancy."""


class RawPathViolation(StorageError):
    """
    A JSONL path resolved outside the intelligence raw-storage root. Raised
    by every read helper before opening any file.
    """


class RelevanceError(IntelligenceError):
    """Invalid Stage 8 input or canonical context; never includes article text."""


class UAERelevanceError(IntelligenceError):
    """Invalid Stage 9 eligibility, source or upstream context; sanitized."""


class EntityExtractionError(IntelligenceError):
    """Invalid Stage 10 context, mention or bounded extraction."""


class EntityRegistryError(EntityExtractionError):
    """Invalid or conflicting canonical definitions/aliases/hierarchy."""


class EventExtractionError(IntelligenceError):
    """Invalid Stage 11 input, bounded event evidence or associations."""


__all__ = [
    "EventExtractionError",
    "EntityExtractionError", "EntityRegistryError",
    "UAERelevanceError",
    "RelevanceError",
    "IntelligenceError",
    "CleaningError",
    "DuplicateDetectionError",
    "OperationLockError",
    "SnapshotChanged",
    "IngestionError",
    "SourceNotRegistered",
    "SourceNotEnabled",
    "SourceRSSMissing",
    "RSSUnavailable",
    "RSSMalformed",
    "RSSEmpty",
    "FeedTimeout",
    "RateLimitedLocally",
    "NotModified",
    "StorageError",
    "DatabaseError",
    "JSONLWriteError",
    "RawRecordInvalid",
    "RawFileMissing",
    "RawPointerInvalid",
    "RawIntegrityError",
    "RawPathViolation",
]


class MetricExtractionError(IntelligenceError):
    """Invalid Stage 12 evidence, dimensions or upstream context."""


__all__ += ['MetricExtractionError']
