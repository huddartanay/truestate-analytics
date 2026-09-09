"""
RSS/Atom fetcher.

FLOW
────
For each registered `Source` selected by the caller:

    1. Registry check          (only registered sources ever get fetched)
    2. Rate-limit guard        (skip if last successful run < refresh_interval_minutes)
    3. Conditional GET         (send If-None-Match / If-Modified-Since if we have them)
    4. HTTP fetch              (HTTPS-only, cert-verified, timeouts, size cap)
    5. Feed parse              (feedparser)
    6. Per-entry sighting      (deterministic article_id + raw_hash;
                                new sighting → append JSONL line +
                                                     insert article_sightings row;
                                repeat sighting → UPDATE last_seen_at + counter)
    7. feed_run_log record     (SUCCESS / NOT_MODIFIED / SKIPPED_RATE_LIMIT /
                                FAILED_*)

Errors are typed (intelligence.errors), raised in a controlled way per
source, and never allowed to stop the run for other sources.

STRICT LIMITS
─────────────
This module fetches ONLY from `source.rss_url` where `source` came from
`intelligence.sources.registry.REGISTRY`. It does not accept arbitrary URLs
from anywhere, including CLI arguments. The `--source <id>` flag in the CLI
resolves through the registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Serialises count-then-append into the JSONL file. Under bounded thread
# concurrency two workers could otherwise both read `existing = N` before
# either appends, producing colliding `raw_jsonl_line` pointers. This lock
# guarantees "count → append → return line_no" is atomic per file across
# threads inside one process.
_JSONL_APPEND_LOCK = threading.Lock()

import certifi
import feedparser

from intelligence import config as _cfg
from intelligence.config import (
    RSS_MAX_BYTES,
    RSS_MAX_CONCURRENT,
    RSS_TIMEOUT_SECONDS,
    RSS_USER_AGENT,
    ensure_data_dirs,
)
from intelligence.db.connection import connect_rw, ensure_ready
from intelligence.db.locking import advisory_lock, bounded_thread_lock
from intelligence.errors import (
    FeedTimeout,
    NotModified,
    RSSMalformed,
    RSSUnavailable,
    RateLimitedLocally,
    SourceNotEnabled,
    SourceNotRegistered,
    SourceRSSMissing,
    JSONLWriteError,
)
from intelligence.schemas import Source
from intelligence.sources.registry import REGISTRY


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT-TYPE + STATUSES
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_TYPE = "rss"   # covers Atom too; feedparser normalises both

RunStatus = str  # SUCCESS | NOT_MODIFIED | SKIPPED_RATE_LIMIT | FAILED_*


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC RESULT TYPES
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RunResult:
    """Outcome of one source's fetch attempt."""

    run_id: str
    source_id: str
    status: RunStatus
    http_status: Optional[int] = None
    entries_seen: int = 0
    entries_new: int = 0
    entries_duplicate: int = 0
    duration_ms: int = 0
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class FetchReport:
    """Aggregate outcome of one `run(...)` call across many sources."""

    started_at: datetime
    finished_at: datetime
    results: list[RunResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    def count(self, status: RunStatus) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def articles_new(self) -> int:
        return sum(r.entries_new for r in self.results)

    @property
    def articles_duplicate(self) -> int:
        return sum(r.entries_duplicate for r in self.results)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY GUARDS — the security boundary
# ─────────────────────────────────────────────────────────────────────────────


def _registry_index() -> dict[str, Source]:
    return {s.source_id: s for s in REGISTRY}


def resolve_source(source_id: str) -> Source:
    """
    The ONLY way a caller may obtain a fetchable Source. Rejects unknown IDs
    before any HTTP call is made.
    """
    idx = _registry_index()
    if source_id not in idx:
        raise SourceNotRegistered(
            f"source_id={source_id!r} is not in the authoritative registry. "
            f"Only registered sources can be fetched."
        )
    return idx[source_id]


def _select_default() -> list[Source]:
    """Enabled + AVAILABLE_RSS + has rss_url."""
    return [s for s in REGISTRY if s.enabled and s.rss_url is not None]


def _select_tier(tier_name: str) -> list[Source]:
    """`tier_2_only` / `tier_1_only` / `tier_3_only` → enabled sources in that tier."""
    from intelligence.enums import SourceTier
    mapping = {
        "tier_1_only": SourceTier.TIER_1,
        "tier_2_only": SourceTier.TIER_2,
        "tier_3_only": SourceTier.TIER_3,
    }
    if tier_name not in mapping:
        raise ValueError(f"Unknown selection {tier_name!r}")
    tier = mapping[tier_name]
    return [s for s in REGISTRY if s.source_tier == tier and s.enabled and s.rss_url is not None]


# ─────────────────────────────────────────────────────────────────────────────
# IDENTITY — deterministic article_id + raw_hash
# ─────────────────────────────────────────────────────────────────────────────


def compute_article_id(source_id: str, entry: dict) -> str:
    """
    Deterministic per-source article identity.

    Strategy (in order of preference):

        1. RSS 2.0 <guid>        (entry.id or entry.guid)
        2. Atom <id>             (also entry.id in feedparser)
        3. Article URL           (entry.link)
        4. Fallback: hash(title + published) — ONLY when the above are absent

    In every case, prefix with source_id so two sources cannot collide on
    each other's IDs even if they carry identical GUIDs.
    """
    guid = entry.get("id") or entry.get("guid") or entry.get("link")
    if not guid:
        title = (entry.get("title") or "").strip()
        published = (entry.get("published") or entry.get("updated") or "").strip()
        guid = f"{title}::{published}"
    key = f"{source_id}::{guid}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def compute_raw_hash(entry: dict) -> str:
    """
    Content hash — a body edit produces a NEW raw_hash so the sighting is
    recorded as a distinct row (article_id stays the same).

    Uses the stable fields we always have; if content changes upstream we
    want to know.
    """
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    published = (entry.get("published") or entry.get("updated") or "").strip()
    # feedparser produces either 'summary' or 'content' (list of dicts)
    body = entry.get("summary") or ""
    if not body and entry.get("content"):
        try:
            body = " ".join(c.get("value", "") for c in entry["content"])
        except Exception:  # pragma: no cover - defensive
            body = ""
    payload = f"{title}\n{link}\n{published}\n{body}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP — HTTPS-only, cert-verified, size-bounded, timeouts
# ─────────────────────────────────────────────────────────────────────────────

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def _http_get(url: str, *, etag: str | None, last_modified: str | None) -> tuple[int, bytes, dict]:
    """
    One HTTP GET. Returns (status, body, response_headers).

    Raises: `RSSUnavailable` for HTTP errors, `FeedTimeout` for timeouts.
    On HTTP 304 we return (304, b"", headers) rather than raise — the caller
    handles that path.
    """
    if not url.lower().startswith("https://"):
        raise RSSUnavailable(f"Non-HTTPS URL rejected: {url!r}")

    headers = {
        "User-Agent": RSS_USER_AGENT,
        "Accept": (
            "application/rss+xml, application/atom+xml, "
            "application/xml, text/xml, */*;q=0.1"
        ),
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    req = Request(url, headers=headers)
    socket.setdefaulttimeout(RSS_TIMEOUT_SECONDS)
    try:
        with urlopen(req, timeout=RSS_TIMEOUT_SECONDS, context=_SSL_CTX) as resp:
            code = resp.status
            body = resp.read(RSS_MAX_BYTES)
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return code, body, resp_headers
    except HTTPError as e:
        if e.code == 304:
            hdrs = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
            return 304, b"", hdrs
        raise RSSUnavailable(f"HTTP {e.code}", http_status=e.code) from e
    except URLError as e:
        raise RSSUnavailable(f"URL error: {str(e.reason)[:120]}") from e
    except socket.timeout as e:
        raise FeedTimeout(f"timeout after {RSS_TIMEOUT_SECONDS}s") from e
    except ssl.SSLError as e:
        raise RSSUnavailable(f"SSL: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────────────────────────────────────────


def _parse_feed(body: bytes) -> feedparser.FeedParserDict:
    """
    Parse an RSS/Atom document. Distinguishes truly malformed from valid-empty.
    """
    parsed = feedparser.parse(body)
    version = parsed.get("version") or ""
    bozo = getattr(parsed, "bozo", 0)
    # Truly malformed: bozo AND no version. Valid empty: version present, 0 entries.
    if bozo and not version:
        exc = str(parsed.get("bozo_exception", "unknown"))[:120]
        raise RSSMalformed(f"parse error: {exc}")
    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# JSONL append
# ─────────────────────────────────────────────────────────────────────────────


def _jsonl_path_for_now() -> Path:
    """
    Daily UTC-partitioned raw log, honouring the Stage-5 rotation policy.

    Once a partition exceeds ``RAW_JSONL_MAX_BYTES`` new writes roll over into
    ``YYYY-MM-DD.NN.jsonl``. Historical files are never renamed, so existing
    ``article_sightings.raw_jsonl_path`` pointers stay valid across rotation.
    """
    from intelligence.storage.rotation import current_partition_path
    return current_partition_path(datetime.now(timezone.utc).date())


def _append_jsonl(record: dict) -> tuple[Path, int]:
    """
    Append one JSON record as one line. Returns (path, 1-based line_no).

    Rotation contract (Stage 5):
      * ``current_partition_path`` returns the target partition; if the base
        file is at/over ``RAW_JSONL_MAX_BYTES`` a new ``.NN`` partition is
        used automatically.
      * The record is written as a single line — never split across files.
      * The line number returned is the 1-based line inside the returned
        path. It is stable because we never truncate or rewrite JSONL files
        (they are append-only).
    """
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    # ── The critical section ──────────────────────────────────────────────
    # `current_partition_path` may itself decide to roll over inside the
    # lock — that keeps two concurrent workers from picking the same "next
    # partition" and racing on its first line number.
    with bounded_thread_lock(_JSONL_APPEND_LOCK), advisory_lock(_cfg.RAW_ARTICLES_DIR / '.append.lock'):
        path = _jsonl_path_for_now()
        from intelligence.storage.raw import resolve_raw_path
        safe_path = resolve_raw_path(path)
        if path.is_symlink():
            raise JSONLWriteError('Refusing to append through a partition symlink')
        existing = 0
        if path.exists():
            with open(safe_path, "rb") as fh:
                existing = sum(1 for _ in fh)
                if fh.tell():
                    fh.seek(-1, os.SEEK_END)
                    if fh.read(1) != b'\n':
                        raise JSONLWriteError('Raw partition has an incomplete trailing line')
        line_no = existing + 1
        with open(safe_path, "a", encoding="utf-8") as fh:
            fh.write(payload + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return path, line_no


# ─────────────────────────────────────────────────────────────────────────────
# RAW ARTICLE OBJECT (Stage 2 shape) — no cleaning, only assembly
# ─────────────────────────────────────────────────────────────────────────────


def build_raw_article(source: Source, entry: dict) -> dict:
    """
    Assemble one raw article dict from a feedparser entry, preserving raw
    fields verbatim. No HTML strip, no whitespace collapse, no Unicode
    normalisation — those are Stage 6.
    """
    article_id = compute_article_id(source.source_id, entry)
    raw_hash = compute_raw_hash(entry)

    raw_title = entry.get("title", "")
    raw_url = entry.get("link", "")
    raw_published = entry.get("published") or entry.get("updated") or ""

    # feedparser exposes body via summary + content list
    raw_body = entry.get("summary", "")
    if not raw_body and entry.get("content"):
        try:
            raw_body = " ".join(c.get("value", "") for c in entry["content"])
        except Exception:  # pragma: no cover
            raw_body = ""

    return {
        # identity
        "article_id":       article_id,
        "raw_hash":         raw_hash,
        # source
        "source_id":        source.source_id,
        "source_name":      source.source_name,
        "rss_url":          str(source.rss_url),
        # raw content (Stage 4 — untouched)
        "raw_title":        raw_title,
        "raw_body":         raw_body,
        "raw_url":          raw_url,
        "raw_published_at": raw_published,
        # transport
        "retrieved_at":     datetime.now(timezone.utc).isoformat(),
        "content_type":     CONTENT_TYPE,
        # complete original entry for downstream re-classification
        "raw_payload":      _entry_to_jsonable(entry),
    }


def _entry_to_jsonable(entry: Any) -> dict:
    """feedparser entries are FeedParserDict; convert to plain JSON-safe dict."""
    def _norm(v):
        if isinstance(v, dict):
            return {k: _norm(val) for k, val in v.items()}
        if isinstance(v, (list, tuple)):
            return [_norm(x) for x in v]
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        # feedparser exposes time.struct_time via *_parsed
        try:
            return json.loads(json.dumps(v, default=str))
        except Exception:  # pragma: no cover
            return str(v)
    return {k: _norm(entry.get(k)) for k in entry.keys()}


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMIT + CONDITIONAL-CACHE STATE
# ─────────────────────────────────────────────────────────────────────────────


def _last_success(conn, source_id: str) -> Optional[dict]:
    """Most-recent SUCCESS or NOT_MODIFIED run for this source, if any."""
    row = conn.execute(
        "SELECT started_at, etag, last_modified FROM feed_run_log "
        "WHERE source_id = ? AND status IN ('SUCCESS', 'NOT_MODIFIED') "
        "ORDER BY started_at DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    return dict(row) if row else None


def _within_refresh_window(last_success_iso: str, refresh_interval_minutes: int) -> bool:
    try:
        last = datetime.fromisoformat(last_success_iso)
    except Exception:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - last
    return delta.total_seconds() < refresh_interval_minutes * 60


# ─────────────────────────────────────────────────────────────────────────────
# SIGHTING WRITE (idempotent)
# ─────────────────────────────────────────────────────────────────────────────


def _record_sighting(
    conn,
    *,
    source_id: str,
    article_id: str,
    raw_hash: str,
    raw_article: dict,
) -> tuple[bool, tuple[Path, int]]:
    """
    Record one sighting.

    Returns (is_new, (jsonl_path, jsonl_line)).

    - New sighting (unique triple): appends JSONL, inserts sighting row.
    - Repeat sighting (same triple): no JSONL append, bumps last_seen_at + counter,
      returns the ORIGINAL (path, line) pointer.
    """
    # Reserve the SQLite writer before checking identity, so independent
    # ingestion processes cannot both append the same new sighting. Caller
    # retains transaction ownership. JSONL + SQLite still cannot commit as one
    # filesystem transaction: a crash can leave an orphan, detected by check.py.
    if not conn.in_transaction:
        conn.execute('BEGIN IMMEDIATE')
    else:
        conn.execute('UPDATE article_sightings SET sighting_count=sighting_count WHERE 0')
    row = conn.execute(
        "SELECT sighting_id, raw_jsonl_path, raw_jsonl_line, sighting_count "
        "FROM article_sightings "
        "WHERE source_id = ? AND article_id = ? AND raw_hash = ?",
        (source_id, article_id, raw_hash),
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if row:
        conn.execute(
            "UPDATE article_sightings "
            "SET last_seen_at = ?, sighting_count = sighting_count + 1 "
            "WHERE sighting_id = ?",
            (now, row["sighting_id"]),
        )
        return False, (Path(row["raw_jsonl_path"]), int(row["raw_jsonl_line"]))

    # Append under the process lock, then insert the stable pointer under the
    # reserved SQLite writer. A rollback never rewrites historical JSONL.
    path, line_no = _append_jsonl(raw_article)
    sighting_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO article_sightings "
        "(sighting_id, source_id, article_id, raw_hash, first_seen_at, last_seen_at, "
        " sighting_count, raw_jsonl_path, raw_jsonl_line) "
        "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (sighting_id, source_id, article_id, raw_hash, now, now, str(path), line_no),
    )
    return True, (path, line_no)


# ─────────────────────────────────────────────────────────────────────────────
# ONE-SOURCE FETCH
# ─────────────────────────────────────────────────────────────────────────────


def fetch_one(source: Source, *, ignore_rate_limit: bool = False) -> RunResult:
    """
    Fetch a single source end-to-end. Never raises — all errors are caught
    and returned in the RunResult (with typed `error_type`).

    ignore_rate_limit: bypass the per-source refresh window (for --source).
    """
    if not source.enabled:
        raise SourceNotEnabled(f"source_id={source.source_id!r} is not enabled")
    if source.rss_url is None:
        raise SourceRSSMissing(f"source_id={source.source_id!r} has no rss_url")

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    ensure_data_dirs()
    ensure_ready()

    result = RunResult(run_id=run_id, source_id=source.source_id, status="SUCCESS")

    with connect_rw() as conn:
        # ── rate-limit guard ────────────────────────────────────────────
        last = _last_success(conn, source.source_id)
        if last and not ignore_rate_limit and _within_refresh_window(
            last["started_at"], source.refresh_interval_minutes
        ):
            result.status = "SKIPPED_RATE_LIMIT"
            result.error_type = RateLimitedLocally.__name__
            result.error_message = (
                f"Last success {last['started_at']}; refresh interval "
                f"{source.refresh_interval_minutes} min"
            )
            result.duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
            _write_run_log(conn, source, started_at, result)
            conn.commit()
            return result

        etag = last["etag"] if last else None
        last_modified = last["last_modified"] if last else None

    # ── HTTP GET (outside the SQLite transaction to avoid holding write lock) ──
    try:
        t0 = time.monotonic()
        http_status, body, resp_headers = _http_get(
            str(source.rss_url), etag=etag, last_modified=last_modified
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
    except FeedTimeout as e:
        result.status = "FAILED_TIMEOUT"
        result.error_type = FeedTimeout.__name__
        result.error_message = str(e)[:500]
    except RSSUnavailable as e:
        result.status = "FAILED_UNAVAILABLE"
        result.http_status = e.http_status
        result.error_type = RSSUnavailable.__name__
        result.error_message = str(e)[:500]
    except Exception as e:  # pragma: no cover - defensive
        result.status = "FAILED_OTHER"
        result.error_type = type(e).__name__
        result.error_message = str(e)[:500]
    else:
        result.http_status = http_status
        # Capture ETag/Last-Modified for the next conditional GET
        result.etag = resp_headers.get("etag")
        result.last_modified = resp_headers.get("last-modified")

        if http_status == 304:
            result.status = "NOT_MODIFIED"
            result.error_type = NotModified.__name__
            result.error_message = "server responded 304 Not Modified"
        else:
            # ── Parse ───────────────────────────────────────────────────
            try:
                parsed = _parse_feed(body)
            except RSSMalformed as e:
                result.status = "FAILED_MALFORMED"
                result.error_type = RSSMalformed.__name__
                result.error_message = str(e)[:500]
            else:
                entries = parsed.entries
                result.entries_seen = len(entries)
                if not entries:
                    result.status = "FAILED_EMPTY"
                    result.error_type = "RSSEmpty"
                    result.error_message = "valid feed, zero entries"
                else:
                    # ── Per-entry sighting (single write txn) ───────────
                    try:
                        with connect_rw() as conn:
                            for entry in entries:
                                raw = build_raw_article(source, entry)
                                is_new, _ = _record_sighting(
                                    conn,
                                    source_id=source.source_id,
                                    article_id=raw["article_id"],
                                    raw_hash=raw["raw_hash"],
                                    raw_article=raw,
                                )
                                if is_new:
                                    result.entries_new += 1
                                else:
                                    result.entries_duplicate += 1
                            conn.commit()
                    except Exception as e:  # pragma: no cover - defensive
                        result.status = "FAILED_OTHER"
                        result.error_type = type(e).__name__
                        result.error_message = str(e)[:500]

    result.duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    # ── Persist the run log ─────────────────────────────────────────────
    with connect_rw() as conn:
        _write_run_log(conn, source, started_at, result)
        conn.commit()

    return result


def _write_run_log(conn, source: Source, started_at: datetime, r: RunResult) -> None:
    conn.execute(
        "INSERT INTO feed_run_log "
        "(run_id, source_id, started_at, completed_at, status, http_status, "
        " entries_seen, entries_new, entries_duplicate, duration_ms, "
        " etag, last_modified, error_type, error_message) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            r.run_id, source.source_id,
            started_at.isoformat(),
            datetime.now(timezone.utc).isoformat(),
            r.status, r.http_status,
            r.entries_seen, r.entries_new, r.entries_duplicate, r.duration_ms,
            r.etag, r.last_modified,
            r.error_type, r.error_message,
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MANY-SOURCE FETCH (bounded concurrency, per-source isolation)
# ─────────────────────────────────────────────────────────────────────────────


def fetch(
    sources: list[Source],
    *,
    max_concurrent: int = RSS_MAX_CONCURRENT,
    ignore_rate_limit: bool = False,
) -> FetchReport:
    """
    Fetch many sources with bounded concurrency.

    Threaded (not async): the workload is I/O-bound on independent hosts,
    the total source count is small (~10), and SQLite is happier with a
    single writer at a time. `feedparser` and `urlopen` are blocking.
    Each source runs in its own thread but only briefly holds a SQLite write
    transaction (per-source), so writer contention stays low.

    A per-source failure never affects other sources. Every source produces
    a RunResult regardless of outcome.
    """
    started = datetime.now(timezone.utc)
    report = FetchReport(started_at=started, finished_at=started)

    if not sources:
        report.finished_at = datetime.now(timezone.utc)
        return report

    ensure_ready()

    with ThreadPoolExecutor(max_workers=max_concurrent) as ex:
        futures = {
            ex.submit(fetch_one, s, ignore_rate_limit=ignore_rate_limit): s
            for s in sources
        }
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                report.results.append(fut.result())
            except Exception as e:  # pragma: no cover - fetch_one shouldn't raise
                report.results.append(RunResult(
                    run_id=str(uuid.uuid4()), source_id=src.source_id,
                    status="FAILED_OTHER", error_type=type(e).__name__,
                    error_message=str(e)[:500],
                ))

    report.finished_at = datetime.now(timezone.utc)
    return report


__all__ = [
    "RunResult", "FetchReport",
    "resolve_source",
    "fetch_one", "fetch",
    "compute_article_id", "compute_raw_hash", "build_raw_article",
    "CONTENT_TYPE",
]
