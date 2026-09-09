"""Precision-oriented content comparison and deterministic candidate blocking.

Stage 4 sightings identify repeated ingestion. Here source and article IDs do
not influence similarity: republishing, syndication and updates need content
evidence. No event/topic inference or token-set containment scoring.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Iterator, Literal

from rapidfuzz import fuzz

from intelligence import config as cfg
from intelligence.deduplication.normalize import PreparedArticle
from intelligence.errors import DuplicateDetectionError


@dataclass(frozen=True)
class Comparison:
    duplicate_type: Literal["EXACT_DUPLICATE", "NEAR_DUPLICATE", "NOT_DUPLICATE"]
    title_similarity: float = 0.0
    body_similarity: float = 0.0
    overall_similarity: float = 0.0
    exact_fingerprint: str | None = None
    fuzzy_compared: bool = False


def scores_pass(title: float, body: float, length_ratio: float) -> bool:
    """Inclusive boundaries on unrounded RapidFuzz scores."""
    overall = (1 - cfg.DEDUP_BODY_WEIGHT) * title + cfg.DEDUP_BODY_WEIGHT * body
    return (title >= cfg.DEDUP_TITLE_MIN and body >= cfg.DEDUP_BODY_MIN
            and overall >= cfg.DEDUP_OVERALL_MIN
            and length_ratio >= cfg.DEDUP_LENGTH_RATIO_MIN)


def near_candidate(a: PreparedArticle, b: PreparedArticle) -> bool:
    if not a.near_eligible or not b.near_eligible:
        return False
    if min(len(a.body), len(b.body)) / max(len(a.body), len(b.body)) < cfg.DEDUP_LENGTH_RATIO_MIN:
        return False
    # Publication first, aware retrieval fallback. Unknown dates bypass the
    # window rather than inventing a zone. Exact matches bypass it entirely.
    return (a.timestamp is None or b.timestamp is None
            or abs(a.timestamp - b.timestamp) <= timedelta(days=cfg.DEDUP_WINDOW_DAYS))


def compare(a: PreparedArticle, b: PreparedArticle) -> Comparison:
    if a.article.cleaning_version != b.article.cleaning_version:
        raise DuplicateDetectionError("Compare only within one cleaning version")
    if a.identity == b.identity:
        return Comparison("NOT_DUPLICATE")
    if (a.exact_eligible and b.exact_eligible and a.fingerprint == b.fingerprint
            and (a.title, a.body) == (b.title, b.body)):
        return Comparison("EXACT_DUPLICATE", 100.0, 100.0, 100.0, a.fingerprint)
    if not near_candidate(a, b) or a.guard != b.guard:
        return Comparison("NOT_DUPLICATE")
    title, body = fuzz.ratio(a.title, b.title), fuzz.ratio(a.body, b.body)
    overall = (1 - cfg.DEDUP_BODY_WEIGHT) * title + cfg.DEDUP_BODY_WEIGHT * body
    label = "NEAR_DUPLICATE" if scores_pass(
        title, body, min(len(a.body), len(b.body)) / max(len(a.body), len(b.body))
    ) else "NOT_DUPLICATE"
    return Comparison(label, title, body, overall, fuzzy_compared=True)


def candidate_pairs(records: Iterable[PreparedArticle]) -> Iterator[tuple[PreparedArticle, PreparedArticle]]:
    """Inverted exact/title/5-word-shingle indexes, not corpus all-pairs.

    Each body contributes its eight lexically smallest SHA-256 shingle hashes.
    A shared sketch hash OR exact title admits a near candidate, subject to
    minimum content, length and time gates. No per-bucket truncation. Dense
    repetitive corpora can still be quadratic; true exact groups necessarily
    have quadratic pair output. Keys and pair order never depend on input order.
    """
    exact, near = defaultdict(list), defaultdict(list)
    ordered = sorted(records, key=lambda r: r.identity)
    if len({r.identity for r in ordered}) != len(ordered):
        raise DuplicateDetectionError("Repeated cleaned identity in candidate input")
    if len({r.article.cleaning_version for r in ordered}) > 1:
        raise DuplicateDetectionError("Candidate input mixes cleaning versions")
    for current in ordered:
        candidates = {}
        if current.exact_eligible:
            candidates.update((r.identity, r) for r in exact[current.fingerprint])
        if current.near_eligible:
            for key in current.keys:
                candidates.update((r.identity, r) for r in near[key] if near_candidate(r, current))
        for identity in sorted(candidates):
            yield candidates[identity], current
        if current.exact_eligible:
            exact[current.fingerprint].append(current)
        if current.near_eligible:
            for key in current.keys:
                near[key].append(current)
