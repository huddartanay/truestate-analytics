"""Comparison representation only; never edits or re-cleans CleanArticle."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from intelligence import config as cfg
from intelligence.schemas import CleanArticle

Identity = tuple[str, str]  # article_id, raw_hash; cleaning version scopes a run
_GLYPHS = str.maketrans({
    **dict(zip("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")),
    **{c: "'" for c in "‘’"}, **{c: '"' for c in "“”"},
    **{c: "-" for c in "‐‑‒–—"},
})
# A lexical veto, not a semantic classifier. Equality of these counters does
# not prove equivalent meaning. Keep all tokens in the comparison text.
_NEGATION = frozenset({"no", "not", "never", "neither", "nor", "without",
                       "لا", "لم", "لن", "ليس", "ليست", "غير", "بدون"})
_TOKENS = re.compile(r"\w+(?:'\w+)*", re.UNICODE)


def normalize(text: str) -> str:
    """NFC, casefold, NFC, explicit glyph map, whitespace -> single spaces.

    Paragraphs collapse for comparison only. Other punctuation (including
    mathematical minus), words and word order remain. No stemming/stopwords.
    """
    return " ".join(unicodedata.normalize("NFC", unicodedata.normalize(
        "NFC", text).casefold()).translate(_GLYPHS).split())


def stable_hash(value) -> str:
    """SHA-256 of compact JSON, ensure_ascii=False, UTF-8, no trailing newline.

    JSON array framing/escaping makes embedded separators unambiguous.
    """
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def lexical_guard(text: str) -> tuple:
    tokens = _TOKENS.findall(text)
    negations = Counter(t for t in tokens if t in _NEGATION or t.endswith("n't"))
    # Preserve numeric-bearing tokens in order; no values/units are extracted
    # or interpreted, and this signature is not a structured observation.
    numbers = tuple(t for t in tokens if any(c.isdigit() for c in t))
    return tuple(sorted(negations.items())), numbers


@dataclass(frozen=True)
class PreparedArticle:
    article: CleanArticle
    identity: Identity
    title: str
    body: str
    fingerprint: str
    body_words: int
    timestamp: datetime | None
    guard: tuple
    keys: tuple[str, ...]

    @property
    def exact_eligible(self) -> bool:
        return self.body_words >= cfg.DEDUP_EXACT_MIN_WORDS and len(self.body) >= cfg.DEDUP_EXACT_MIN_CHARS

    @property
    def near_eligible(self) -> bool:
        return (self.body_words >= cfg.DEDUP_NEAR_MIN_WORDS
                and len(self.body) >= cfg.DEDUP_NEAR_MIN_CHARS
                and len(self.title.split()) >= cfg.DEDUP_TITLE_MIN_WORDS)


def prepare(article: CleanArticle) -> PreparedArticle:
    title, body = normalize(article.clean_title), normalize(article.clean_body)
    words = body.split()
    shingles = {stable_hash(words[i:i + cfg.DEDUP_SHINGLE_WORDS])
                for i in range(len(words) - cfg.DEDUP_SHINGLE_WORDS + 1)}
    keys = tuple(["t:" + stable_hash(title)] + ["b:" + h for h in sorted(shingles)[:cfg.DEDUP_SKETCH_SIZE]])
    timestamp = article.normalized_published_at
    if timestamp is None and article.retrieved_at.utcoffset() is not None:
        timestamp = article.retrieved_at
    return PreparedArticle(
        article, (article.article_id, article.raw_hash), title, body,
        stable_hash([title, body]), sum(any(c.isalnum() for c in w) for w in words),
        timestamp, (lexical_guard(title), lexical_guard(body)), keys,
    )
