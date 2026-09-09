"""
Command-line entry point for the intelligence pipeline.

    python -m intelligence.pipeline.run --fetch-only
    python -m intelligence.pipeline.run --fetch-only --source khaleejtimes-uae
    python -m intelligence.pipeline.run --fetch-only --sources tier_2_only
    python -m intelligence.pipeline.run --fetch-only --ignore-rate-limit
    python -m intelligence.pipeline.run --clean-only --since 2026-09-07
    python -m intelligence.pipeline.run --dedupe-only
    python -m intelligence.pipeline.run --relevance-only
    python -m intelligence.pipeline.run --uae-relevance-only
    python -m intelligence.pipeline.run --entities-only --json
    python -m intelligence.pipeline.run --events-only --json
    python -m intelligence.pipeline.run --metrics-only --json
    python -m intelligence.pipeline.run --build-intelligence-only --json

Design rules enforced here:
  * Registry is the security boundary. `--source <id>` only accepts a
    registered source_id; the CLI cannot fetch arbitrary URLs.
  * All nine operational modes are exclusive, independently imported.
  * Fetch exits 0 unless every source failed (existing Stage 4 semantics).
    Cleaning exits 0 on success, 1 on partial success/failure, 2 on usage errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from intelligence.pipeline.fetch import FetchReport


def _select_sources(args: argparse.Namespace):
    """Resolve which sources to fetch. Registry-only, no arbitrary URLs."""
    from intelligence.pipeline.fetch import resolve_source
    from intelligence.sources.registry import REGISTRY, enabled_sources

    if args.source:
        s = resolve_source(args.source)   # raises SourceNotRegistered on unknown id
        return [s]
    if args.sources == "tier_1_only":
        from intelligence.enums import SourceTier
        return [s for s in REGISTRY
                if s.source_tier == SourceTier.TIER_1 and s.enabled and s.rss_url is not None]
    if args.sources == "tier_2_only":
        from intelligence.enums import SourceTier
        return [s for s in REGISTRY
                if s.source_tier == SourceTier.TIER_2 and s.enabled and s.rss_url is not None]
    if args.sources == "tier_3_only":
        from intelligence.enums import SourceTier
        return [s for s in REGISTRY
                if s.source_tier == SourceTier.TIER_3 and s.enabled and s.rss_url is not None]
    if args.sources == "all_enabled":
        return list(enabled_sources())
    # Default: enabled sources only
    return list(enabled_sources())


def _print_report(report: FetchReport) -> None:
    print(f"{'STATUS':<20} {'SEEN':>5} {'NEW':>5} {'DUP':>5} {'MS':>6}  SOURCE  (note)")
    print("-" * 100)
    for r in sorted(report.results, key=lambda x: x.source_id):
        note = ""
        if r.error_message:
            note = f"  — {r.error_message[:60]}"
        elif r.http_status is not None:
            note = f"  http={r.http_status}"
        print(f"{r.status:<20} {r.entries_seen:>5} {r.entries_new:>5} "
              f"{r.entries_duplicate:>5} {r.duration_ms:>6}  {r.source_id}{note}")
    print("-" * 100)
    dur = (report.finished_at - report.started_at).total_seconds()
    print(f"Sources: {report.total}   "
          f"SUCCESS: {report.count('SUCCESS')}   "
          f"NOT_MODIFIED: {report.count('NOT_MODIFIED')}   "
          f"SKIPPED_RATE_LIMIT: {report.count('SKIPPED_RATE_LIMIT')}   "
          f"FAILED_UNAVAILABLE: {report.count('FAILED_UNAVAILABLE')}   "
          f"FAILED_MALFORMED: {report.count('FAILED_MALFORMED')}   "
          f"FAILED_TIMEOUT: {report.count('FAILED_TIMEOUT')}   "
          f"FAILED_EMPTY: {report.count('FAILED_EMPTY')}   "
          f"FAILED_OTHER: {report.count('FAILED_OTHER')}")
    print(f"New articles: {report.articles_new}   Duplicate sightings: {report.articles_duplicate}")
    print(f"Wall time: {dur:.1f}s")


def _json_report(report: FetchReport) -> str:
    return json.dumps({
        "started_at":  report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "articles_new":       report.articles_new,
        "articles_duplicate": report.articles_duplicate,
        "results": [
            {
                "source_id": r.source_id, "status": r.status,
                "http_status": r.http_status,
                "entries_seen": r.entries_seen, "entries_new": r.entries_new,
                "entries_duplicate": r.entries_duplicate,
                "duration_ms": r.duration_ms,
                "etag": r.etag, "last_modified": r.last_modified,
                "error_type": r.error_type, "error_message": r.error_message,
                "run_id": r.run_id,
            }
            for r in report.results
        ],
    }, indent=2)


def _since_date(value: str) -> datetime:
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError
        return datetime.combine(date.fromisoformat(value), time.min, tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError("--since requires a valid YYYY-MM-DD date") from None


def _clean(args: argparse.Namespace) -> int:
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.clean import run_cleaning

    try:
        report = run_cleaning(since=args.since)
    except IntelligenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f"Cleaning {report.status}: seen={report.records_seen} "
              f"cleaned={report.records_cleaned} skipped={report.records_skipped} "
              f"failed={report.records_failed} files_failed={report.files_failed} "
              f"version={report.cleaning_version} duration_ms={report.duration_ms}")
        for error in report.errors:
            print(f"  {error['type']} at {error['file']}:{error['line']}")
    return 0 if report.status == "SUCCESS" else 1


def _dedupe(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.deduplicate import run_deduplication

    try:
        report = run_deduplication(since=args.since, cleaning_version=(
            args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION
        ))
    except IntelligenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f"Deduplication {report.status}: seen={report.records_seen} "
              f"candidates={report.candidate_pairs} exact={report.exact_duplicates} "
              f"near={report.near_duplicates} inserted={report.pairs_inserted} "
              f"groups={report.groups_evaluated} failed={report.records_failed} "
              f"version={report.dedup_version} duration_ms={report.duration_ms}")
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status == "SUCCESS" else 1


def _relevance(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.relevance import run_relevance

    try:
        report = run_relevance(since=args.since, cleaning_version=(
            args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION))
    except IntelligenceError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f'Relevance {report.status}: seen={report.records_seen} canonical={report.canonical_records_seen} '
              f'relevant={report.relevant_count} irrelevant={report.irrelevant_count} '
              f'skipped={report.skipped_count} failed={report.failed_count} '
              f'version={report.relevance_version} duration_ms={report.duration_ms}')
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status == 'SUCCESS' else 1


def _uae_relevance(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.uae_relevance import run_uae_relevance
    try:
        report = run_uae_relevance(cleaning_version=args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION)
    except IntelligenceError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f'UAE relevance {report.status}: eligible={report.eligible_stage8_records} '
              f'evaluated={report.evaluated_count} accepted={report.uae_relevant_count} '
              f'rejected={report.not_uae_relevant_count} skipped={report.skipped_count} '
              f'ineligible={report.ineligible_count} failed={report.failed_count} '
              f'version={report.uae_relevance_version} duration_ms={report.duration_ms}')
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status == 'SUCCESS' else 1


def _entities(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.entities import run_entities
    try:
        report=run_entities(cleaning_version=args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION)
    except IntelligenceError as exc:
        print(f'error: {exc}',file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report),indent=2))
    else:
        print(f'Entities {report.status}: eligible={report.eligible_stage9_records} evaluated={report.evaluated_count} '
              f'with_entities={report.records_with_entities} without_entities={report.records_without_entities} '
              f'mentions={report.mention_count} skipped={report.skipped_count} failed={report.failed_count} '
              f'version={report.entity_extraction_version} registry={report.entity_registry_version} duration_ms={report.duration_ms}')
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status=='SUCCESS' else 1


def _events(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.events import run_events
    try:
        report = run_events(cleaning_version=args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION)
    except IntelligenceError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f'Events {report.status}: eligible={report.eligible_stage10_records} evaluated={report.evaluated_count} '
              f'with_events={report.records_with_events} without_events={report.records_without_events} '
              f'events={report.event_count} skipped={report.skipped_count} failed={report.failed_count} '
              f'version={report.event_extraction_version} duration_ms={report.duration_ms}')
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status == 'SUCCESS' else 1


def _metrics(args: argparse.Namespace) -> int:
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.metrics import run_metrics
    try:
        report = run_metrics(cleaning_version=args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION)
    except IntelligenceError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(f'Metrics {report.status}: eligible={report.eligible_stage11_records} evaluated={report.evaluated_count} '
              f'with_observations={report.records_with_observations} without_observations={report.records_without_observations} '
              f'observations={report.observation_count} skipped={report.skipped_count} failed={report.failed_count} '
              f'version={report.metric_extraction_version} duration_ms={report.duration_ms}')
        for error in report.errors:
            print(f"  {error['type']} at record {error['record']}")
    return 0 if report.status == 'SUCCESS' else 1


def _intelligence(args):
    from intelligence.config import CLEANING_VERSION
    from intelligence.errors import IntelligenceError
    from intelligence.pipeline.intelligence import run_intelligence
    try:
        report=run_intelligence(cleaning_version=args.cleaning_version if args.cleaning_version is not None else CLEANING_VERSION)
    except (IntelligenceError,ValueError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(asdict(report),indent=2))
    else:
        print(f'Intelligence {report.status}: build={report.build_id} reused={report.reused_count} failed={report.failed_count} duration_ms={report.duration_ms}')
        print(json.dumps(report.counts,sort_keys=True))
        for error in report.errors: print(json.dumps(error,sort_keys=True))
    return 0 if report.status=='SUCCESS' else 1


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="intelligence.pipeline.run",
        description="Intelligence pipeline: RSS fetch, cleaning, deduplication, relevance, entities, events and metrics.",
    )
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument(
        "--fetch-only", action="store_true",
        help="Fetch RSS only (existing Stage 4 behavior).",
    )
    modes.add_argument(
        "--clean-only", action="store_true",
        help="Clean existing raw RSS records without any network requests.",
    )
    modes.add_argument(
        "--dedupe-only", action="store_true",
        help="Detect duplicate content in existing cleaned rows; no fetching or cleaning.",
    )
    modes.add_argument('--relevance-only', action='store_true',
                       help='Classify real-estate relevance using existing canonical metadata, offline.')
    modes.add_argument('--build-intelligence-only',action='store_true',
                       help='Build UAE intelligence, deterministic market movements and rankings offline.')
    modes.add_argument('--metrics-only', action='store_true',
                       help='Extract numeric market observations from stored Stage 11 contexts, offline.')
    modes.add_argument('--events-only', action='store_true',
                       help='Extract event instances from stored Stage 10 contexts, offline.')
    modes.add_argument('--entities-only', action='store_true',
                       help='Extract registered entities from accepted stored Stage 9 contexts, offline.')
    modes.add_argument('--uae-relevance-only', action='store_true',
                       help='Classify UAE relevance of stored Stage 8 accepted contexts, offline.')
    ap.add_argument(
        "--cleaning-version", metavar="VERSION",
        help="Offline stages after cleaning: cleaned cohort (default: configured CLEANING_VERSION).",
    )
    ap.add_argument(
        "--since", type=_since_date, metavar="YYYY-MM-DD",
        help="UTC retrieval cutoff. Dedupe retains older candidates; relevance selects any matching group member.",
    )
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument(
        "--source", metavar="SOURCE_ID",
        help="Fetch a single registered source (resolved via the registry).",
    )
    grp.add_argument(
        "--sources", choices=["all_enabled", "tier_1_only", "tier_2_only", "tier_3_only"],
        default=None,
        help="Fetch a subset. Defaults to enabled sources only.",
    )
    ap.add_argument(
        "--ignore-rate-limit", action="store_true",
        help="Bypass per-source refresh window. Use for controlled diagnostics only.",
    )
    ap.add_argument(
        "--concurrency", type=int, default=None,
        help="Override RSS_MAX_CONCURRENT for this run.",
    )
    ap.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON.",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.build_intelligence_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        if args.since is not None:
            ap.error('Stage 13 consumes the latest completed Stage 12 cohort; --since is unsupported')
        return _intelligence(args)
    if args.metrics_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        if args.since is not None:
            ap.error('Stage 12 consumes the latest completed Stage 11 cohort; --since is unsupported')
        return _metrics(args)
    if args.events_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        if args.since is not None:
            ap.error('Stage 11 consumes the latest completed Stage 10 cohort; --since is unsupported')
        return _events(args)
    if args.entities_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        if args.since is not None:
            ap.error('Stage 10 consumes the latest completed Stage 9 cohort; --since is unsupported')
        return _entities(args)
    if args.uae_relevance_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        if args.since is not None:
            ap.error('Stage 9 does not support --since; it consumes the latest completed Stage 8 run cohort')
        return _uae_relevance(args)
    if args.relevance_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error('source selection, rate-limit and concurrency options require --fetch-only')
        return _relevance(args)
    if args.dedupe_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error("source selection, rate-limit and concurrency options require --fetch-only")
        return _dedupe(args)
    if args.cleaning_version is not None:
        ap.error("--cleaning-version requires --dedupe-only, --relevance-only, --uae-relevance-only, --entities-only, --events-only or --metrics-only or --build-intelligence-only")
    if args.clean_only:
        if args.source or args.sources or args.ignore_rate_limit or args.concurrency is not None:
            ap.error("source selection, rate-limit and concurrency options require --fetch-only")
        return _clean(args)
    if args.since is not None:
        ap.error("--since requires --clean-only, --dedupe-only or --relevance-only")
    if not args.fetch_only:
        print("error: choose --fetch-only, --clean-only, --dedupe-only, --relevance-only, --uae-relevance-only, --entities-only, --events-only or --metrics-only or --build-intelligence-only.",
              file=sys.stderr)
        return 2

    sources = _select_sources(args)
    if not sources:
        print("No enabled sources match the selection. Nothing to do.", file=sys.stderr)
        return 0

    from intelligence.config import RSS_MAX_CONCURRENT
    from intelligence.pipeline.fetch import fetch
    max_concurrent = args.concurrency or RSS_MAX_CONCURRENT

    # For --source, we bypass the rate-limit guard: an explicit ID is a
    # controlled diagnostic invocation, not a scheduled bulk fetch.
    ignore_rl = args.ignore_rate_limit or (args.source is not None)

    report = fetch(sources, max_concurrent=max_concurrent, ignore_rate_limit=ignore_rl)

    if args.json:
        print(_json_report(report))
    else:
        _print_report(report)

    # Exit code: 0 unless EVERY source failed. Never fail because ONE source
    # is down — the pipeline is designed to isolate per-source failures.
    total_failed = (report.count("FAILED_UNAVAILABLE")
                    + report.count("FAILED_MALFORMED")
                    + report.count("FAILED_TIMEOUT")
                    + report.count("FAILED_OTHER"))
    if report.total > 0 and total_failed == report.total:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
