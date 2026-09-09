"""
RSS health probe.

Runs offline (not in the Streamlit request path). Fetches every registered
`rss_url`, parses with feedparser, and reports a fresh ProbeResult per source.
This is what determines whether a registry entry is truly AVAILABLE_RSS on
the current network.

Usage:
    python -m intelligence.sources.health
    python -m intelligence.sources.health --json
    python -m intelligence.sources.health --only khaleejtimes-uae
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi
import feedparser

from intelligence.config import RSS_MAX_BYTES, RSS_TIMEOUT_SECONDS, RSS_USER_AGENT
from intelligence.enums import RSSStatus
from intelligence.schemas import ProbeResult, Source
from intelligence.sources.registry import REGISTRY


def _ssl_ctx() -> ssl.SSLContext:
    """SSL context using certifi's CA bundle — works on macOS / Linux / CI."""
    return ssl.create_default_context(cafile=certifi.where())


def probe(source: Source) -> ProbeResult:
    """
    Live-verify one source's RSS URL.

    Returns AVAILABLE_RSS only when: the URL exists (< 400 status), the
    response parses as a real feed (feedparser gives a version), and at least
    one entry is present.
    """
    now = datetime.now(timezone.utc)

    if source.rss_url is None:
        return ProbeResult(
            source_id=source.source_id,
            url=None,
            status=RSSStatus.RSS_UNAVAILABLE,
            note="No RSS URL registered (source retained for documentation).",
            probed_at=now,
        )

    url = str(source.rss_url)
    socket.setdefaulttimeout(RSS_TIMEOUT_SECONDS)
    try:
        req = Request(
            url,
            headers={
                "User-Agent": RSS_USER_AGENT,
                "Accept": (
                    "application/rss+xml, application/atom+xml, "
                    "application/xml, text/xml, */*"
                ),
            },
        )
        with urlopen(req, timeout=RSS_TIMEOUT_SECONDS, context=_ssl_ctx()) as resp:
            http_code = resp.status
            body = resp.read(RSS_MAX_BYTES)
    except HTTPError as e:
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.RSS_UNAVAILABLE, http_code=e.code,
            note=f"HTTP {e.code}", probed_at=now,
        )
    except (URLError, ssl.SSLError) as e:
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.RSS_UNAVAILABLE,
            note=f"URL error: {str(getattr(e, 'reason', e))[:100]}",
            probed_at=now,
        )
    except socket.timeout:
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.RSS_UNVERIFIED,
            note=f"Timeout after {RSS_TIMEOUT_SECONDS}s",
            probed_at=now,
        )
    except Exception as e:  # pragma: no cover — defensive
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.RSS_UNVERIFIED,
            note=f"{type(e).__name__}: {str(e)[:120]}",
            probed_at=now,
        )

    parsed = feedparser.parse(body)
    n_entries = len(parsed.entries)
    version = parsed.get("version") or ""
    feed_title = (parsed.feed.get("title") or "")[:120] if parsed.feed else ""
    bozo = getattr(parsed, "bozo", 0)

    if n_entries >= 1 and (version or not bozo):
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.AVAILABLE_RSS, http_code=http_code,
            n_entries=n_entries, feed_version=version, feed_title=feed_title,
            note=f"OK — {version or 'unversioned'}, {n_entries} entries",
            probed_at=now,
        )
    if bozo:
        return ProbeResult(
            source_id=source.source_id, url=source.rss_url,
            status=RSSStatus.RSS_UNAVAILABLE, http_code=http_code,
            n_entries=n_entries,
            note=f"Parse failed: {str(parsed.get('bozo_exception', ''))[:120]}",
            probed_at=now,
        )
    return ProbeResult(
        source_id=source.source_id, url=source.rss_url,
        status=RSSStatus.RSS_UNAVAILABLE, http_code=http_code,
        n_entries=n_entries, note="No entries parsed", probed_at=now,
    )


def probe_all(only: str | None = None) -> list[ProbeResult]:
    """
    Probe every source, or a single one when `only` is given.

    The registry state (what is enabled) is NOT modified by this function.
    Registry changes are code changes, made after reviewing the probe report.
    """
    targets = [s for s in REGISTRY if only is None or s.source_id == only]
    return [probe(s) for s in targets]


def _print_report(results: list[ProbeResult]) -> None:
    by_status = {s.value: 0 for s in RSSStatus}
    for r in results:
        by_status[r.status.value] += 1

    print(f"{'STATUS':<16}  {'HTTP':>4}  {'N':>4}  {'SOURCE ID':<32}  NOTE")
    print("-" * 110)
    for r in results:
        code = "—" if r.http_code is None else str(r.http_code)
        print(f"{r.status.value:<16}  {code:>4}  {r.n_entries:>4}  "
              f"{r.source_id:<32}  {r.note[:60]}")
    print("-" * 110)
    total = len(results)
    print(f"Total probed: {total}   "
          + "   ".join(f"{k}: {v}" for k, v in by_status.items()))


def main() -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Verify RSS availability for every registered source.")
    ap.add_argument("--only", help="Probe a single source_id.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = ap.parse_args()

    results = probe_all(only=args.only)
    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
    else:
        _print_report(results)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["probe", "probe_all"]
