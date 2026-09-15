"""Conservative parsing helpers for RAK monthly report table extracts.

The supplied monthly PDFs are image-based. OCR output is therefore treated as
an intermediate input, not as trusted structured data: this module identifies
the six known table rows, takes the two period values in the documented column
order, and leaves a row absent when OCR cannot provide both values. The
resulting records can be reviewed before being added to ``sources.py``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .analytics import parse_numeric


TABLE_METRICS = (
    ("Real Estate Sales Volume", "sales_v"),
    ("Real Estate Mortgages Volume", "mort_v"),
    ("Waivers Market Value", "waiv_v"),
    ("Real Estate Sales Number", "sales_n"),
    ("Real Estate Mortgages Number", "mort_n"),
    ("Waivers Number", "waiv_n"),
)

_NUMBER = re.compile(r"(?<![A-Za-z])\(?\d[\d,]*(?:\.\d+)?\)?%?")


def _number_values(text: str) -> list[int | float]:
    """Return numeric tokens in order, excluding the row's change percent."""
    cleaned = re.sub(r"\s*,\s*", ",", text)
    values: list[int | float] = []
    for token in _NUMBER.findall(cleaned):
        parsed = parse_numeric(token.rstrip("%"))
        if parsed is not None:
            values.append(parsed)
    return values[:2]


def _metric_spans(text: str) -> list[tuple[str, str, int, int]]:
    folded = text.casefold()
    spans = []
    for label, key in TABLE_METRICS:
        start = 0
        needle = label.casefold()
        while True:
            position = folded.find(needle, start)
            if position < 0:
                break
            spans.append((label, key, position, position + len(needle)))
            start = position + len(needle)
    return sorted(spans, key=lambda item: item[2])


def parse_monthly_table_text(
    text: str,
    *,
    month: str,
    current_year: int,
    previous_year: int,
    source_note: str = "",
) -> tuple[dict[str, object], ...]:
    """Parse the six known transaction rows from OCR/table text.

    Monthly report columns are consistently ordered as current year followed
    by previous year. A result is returned only for a year whose complete six-
    cell table was found. This prevents a partial OCR pass from becoming a
    seemingly valid monthly report and, consequently, a false quarter.
    """
    spans = _metric_spans(text)
    if not spans:
        return ()

    values_by_key: dict[str, tuple[int | float, int | float]] = {}
    for index, (_, key, _, end) in enumerate(spans):
        next_start = spans[index + 1][2] if index + 1 < len(spans) else len(text)
        values = _number_values(text[end:next_start])
        if len(values) == 2:
            values_by_key[key] = (values[0], values[1])

    if set(values_by_key) != {key for _, key in TABLE_METRICS}:
        return ()

    rows = []
    for column, year in enumerate((current_year, previous_year)):
        row = {
            "year": year,
            "month": month,
            "source_note": source_note,
        }
        for _, key in TABLE_METRICS:
            row[key] = values_by_key[key][column]
        rows.append(row)
    return tuple(rows)


def rows_are_complete(rows: Iterable[dict[str, object]]) -> bool:
    """Return whether every parsed monthly row contains all six metrics."""
    keys = {key for _, key in TABLE_METRICS}
    return all(keys.issubset(row) and all(row[key] is not None for key in keys) for row in rows)
