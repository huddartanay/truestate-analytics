"""Pure RSS text cleaning. No acquisition, extraction or market interpretation.

Rules are versioned by CLEANING_VERSION. Currency/unit spellings and numeric
values are retained; only NFC, digit glyphs and whitespace are normalized.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from html import unescape

from bs4 import BeautifulSoup
from dateutil import parser, tz

from intelligence.config import CLEANING_VERSION
from intelligence.schemas import CleanArticle, RawArticleRecord

_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789",
)
_BLOCK_TAGS = (
    "p", "div", "section", "article", "header", "footer", "blockquote",
    "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre",
)
# Deliberately narrow: only an isolated terminal navigation paragraph in these
# two BBC feeds, with exact case. No generic footer guessing or substring rule.
_TERMINAL_BOILERPLATE = {
    "bbc-business": frozenset({"Read more"}),
    "bbc-middle-east": frozenset({"Read more"}),
}


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(_DIGITS)


def clean_text(text: str, *, source_id: str = "", title: bool = False) -> str:
    """Remove RSS markup; retain paragraph breaks and inline text adjacency.

    HTML entities are decoded before parsing, so entity-escaped markup cannot
    leave an encoded script/style/noscript block in cleaned text. BeautifulSoup
    sees a string only: even URL-like input is never fetched.
    """
    soup = BeautifulSoup(unescape(normalize_unicode(text)), "lxml")
    for tag in soup.find_all(("script", "style", "noscript")):
        tag.decompose()
    for tag in soup.find_all("br"):
        tag.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before("\n\n")
        tag.insert_after("\n\n")
    # Cells are inline within a row, but must not run into their neighbours.
    for tag in soup.find_all(("td", "th")):
        tag.insert_after(" ")
    text = normalize_unicode(soup.get_text()).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if title:
        return " ".join(text.split())
    paragraphs = text.split("\n\n") if text else []
    removable = _TERMINAL_BOILERPLATE.get(source_id, ())
    while paragraphs and paragraphs[-1] in removable:
        paragraphs.pop()
    return "\n\n".join(paragraphs)


def _timezone(name: str | None, offset: int | None):
    """Only explicit numeric offsets and UTC/GMT; never host/source timezone."""
    if offset is not None:
        return tz.tzoffset(name, offset)
    if name in {"UTC", "GMT", "Z"}:
        return tz.UTC
    return None


class _ExplicitYearInfo(parser.parserinfo):
    def convertyear(self, year, century_specified=False):
        # dateutil's normal two-digit-year window depends on the current year.
        # Reject it instead of choosing a century that the RSS never supplied.
        if year < 100 and not century_specified:
            raise ValueError("Publication year must include its century")
        return year


def normalize_publication_date(value: str) -> tuple[datetime | None, bool]:
    """UTC date and parse-error flag, with no wall-clock/default-date invention.

    Missing/invalid/incomplete calendar dates -> (None, True). Two fixed
    defaults detect omitted calendar components rather than filling from today.
    Full dates without a known zone (including unknown abbreviations) ->
    (None, False). No source-specific timezone assumptions are configured.
    Two-digit years are rejected rather than expanded using today's century.
    Omitted clock components follow dateutil's zero-time defaults.
    """
    text = normalize_unicode(value).strip()
    if not text:
        return None, True
    try:
        info = _ExplicitYearInfo()
        first = parser.parse(text, parserinfo=info, default=datetime(2000, 1, 1), tzinfos=_timezone)
        second = parser.parse(text, parserinfo=info, default=datetime(2004, 7, 13), tzinfos=_timezone)
        if first != second:
            return None, True
        if first.utcoffset() is None:
            return None, False
        return first.astimezone(timezone.utc), False
    except (ValueError, OverflowError):
        return None, True


def detect_language(text: str) -> str:
    """Character heuristic, not linguistic identification.

    Count letters only. Latin letters in U+0041..U+024F with LATIN Unicode
    names proxy English; Arabic-script letters in U+0600..U+06FF,
    U+0750..U+077F, U+08A0..U+08FF and presentation forms proxy Arabic.
    Mixed requires >=2 letters from each script and >=20% each of all letters.
    Otherwise a script must comprise >=80% of all letters; else unknown.
    Digits, punctuation and combining marks do not vote.
    """
    latin = arabic = total = 0
    for char in text:
        if not char.isalpha():
            continue
        total += 1
        cp = ord(char)
        latin += 0x0041 <= cp <= 0x024F and "LATIN" in unicodedata.name(char, "")
        arabic += any(lo <= cp <= hi for lo, hi in (
            (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
        ))
    if not total:
        return "unknown"
    if min(latin, arabic) >= 2 and min(latin, arabic) * 5 >= total:
        return "mixed"
    if latin * 5 >= total * 4:
        return "en"
    if arabic * 5 >= total * 4:
        return "ar"
    return "unknown"


def count_words(body: str) -> int:
    """Body only: whitespace-delimited tokens containing any letter/number.

    Punctuation-only tokens do not count; hyphenated words and numeric strings
    remain single tokens. This is a reproducible count, not NLP tokenization.
    """
    return sum(any(char.isalnum() for char in token) for token in body.split())


def clean_article(raw: RawArticleRecord, *, cleaning_version: str = CLEANING_VERSION) -> CleanArticle:
    """Copy identity/provenance and derive text only, without mutating raw."""
    title = clean_text(raw.raw_title, title=True)
    body = clean_text(raw.raw_body, source_id=raw.source_id)
    published, error = normalize_publication_date(raw.raw_published_at)
    return CleanArticle(
        article_id=raw.article_id, raw_hash=raw.raw_hash,
        source_id=raw.source_id, source_name=raw.source_name, rss_url=raw.rss_url,
        retrieved_at=raw.retrieved_at, content_type=raw.content_type,
        clean_title=title, clean_body=body, normalized_published_at=published,
        detected_language=detect_language(title + "\n" + body),
        word_count=count_words(body), date_parse_error=error,
        cleaning_version=cleaning_version,
    )
