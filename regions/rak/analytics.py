"""Reusable, report-backed RAK yearly and quarterly analytics.

The source registry is populated from the RAK Statistics Office reports. This
module is deliberately a transformation layer: it normalises extracted table
values, selects one annual report at a time, and aggregates complete monthly
triplets into quarters. It never fills missing values or creates a period that
the reports do not support.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
import re

from . import sources as S


ANNUAL_YEAR_OPTIONS = (2022, 2023, 2024)
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
MONTH_NUMBER = {month: i for i, month in enumerate(MONTHS, start=1)}
MONTH_ALIASES = {
    month[:3].casefold(): month for month in MONTHS
}
QUARTER_MONTHS = {
    "Q1": (1, 2, 3),
    "Q2": (4, 5, 6),
    "Q3": (7, 8, 9),
    "Q4": (10, 11, 12),
}

VALUE_METRICS = (
    ("Real Estate Sales Volume", "sales_v", "AED"),
    ("Real Estate Mortgages Volume", "mort_v", "AED"),
    ("Waiver Market Value", "waiv_v", "AED"),
    ("Total Transactions Value", "total_v", "AED"),
)
COUNT_METRICS = (
    ("Real Estate Sales Number", "sales_n", "transactions"),
    ("Real Estate Mortgages Number", "mort_n", "transactions"),
    ("Waivers Number", "waiv_n", "transactions"),
    ("Total Number of Transactions", "total_n", "transactions"),
)
ALL_METRICS = VALUE_METRICS + COUNT_METRICS
CHART_VALUE_METRICS = VALUE_METRICS[:3]
CHART_COUNT_METRICS = COUNT_METRICS[:3]


@dataclass(frozen=True)
class AnnualSnapshot:
    year: int
    source: Mapping[str, object]
    metrics: Mapping[str, float | int | None]


@dataclass(frozen=True)
class QuarterlySnapshot:
    year: int
    quarter: str
    months: tuple[str, ...]
    metrics: Mapping[str, float | int | None]
    source_notes: tuple[str, ...]


_ANNUAL_TABLES = (
    (
        S.RAK_ANNUAL_2022,
        S.RAK_ANNUAL_2021_2022_VALUE,
        S.RAK_ANNUAL_2021_2022_COUNT,
    ),
    (
        S.RAK_ANNUAL_2025,
        S.RAK_ANNUAL_2024_2025_VALUE,
        S.RAK_ANNUAL_2024_2025_COUNT,
    ),
    (
        S.RAK_ANNUAL_2021,
        S.RAK_ANNUAL_2020_2021_VALUE,
        S.RAK_ANNUAL_2020_2021_COUNT,
    ),
)


def parse_numeric(value: object) -> float | int | None:
    """Parse a PDF/OCR table cell without guessing missing values.

    Handles commas, currency text, parenthesised negatives, non-breaking
    spaces and em-dash cells. Multiple numeric tokens are rejected because a
    merged OCR cell is ambiguous and must not become fabricated data.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    text = str(value).replace("\u00a0", " ").strip()
    if not text or text in {"—", "–", "-", "N/A", "NA", "null"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace(",", "").replace("AED", "").replace("aed", "")
    tokens = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    if len(tokens) != 1:
        return None
    number = float(tokens[0])
    if negative:
        number = -number
    return int(number) if number.is_integer() else number


def _year_value(row: Mapping[str, object], year: int, suffix: str) -> float | int | None:
    field = f"y{year}_{suffix}" if suffix else f"y{year}"
    return parse_numeric(row.get(field))


def _row_by_category(rows: Iterable[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    return {str(row.get("category", "")): row for row in rows}


def _annual_snapshot_from_tables(
    year: int,
    source: Mapping[str, object],
    value_rows: Iterable[Mapping[str, object]],
    count_rows: Iterable[Mapping[str, object]],
) -> AnnualSnapshot | None:
    values = _row_by_category(value_rows)
    counts = _row_by_category(count_rows)
    required = (
        ("Real Estate Sales Volume", "sales_v", "aed", values),
        ("Real Estate Mortgages Volume", "mort_v", "aed", values),
        ("Waiver Market Value", "waiv_v", "aed", values),
        ("Total Transactions Value", "total_v", "aed", values),
        ("Real Estate Sales Number", "sales_n", "", counts),
        ("Real Estate Mortgages Number", "mort_n", "", counts),
        ("Waivers Number", "waiv_n", "", counts),
        ("Total Number of Transactions", "total_n", "", counts),
    )
    metrics: dict[str, float | int | None] = {}
    for label, key, suffix, rows in required:
        source_label = "Total Transactions" if label == "Total Transactions Value" else label
        if label == "Total Number of Transactions":
            source_label = "Total Number of Transactions"
        row = rows.get(source_label)
        if row is None:
            return None
        metrics[key] = _year_value(row, year, suffix)
        if metrics[key] is None:
            return None
    return AnnualSnapshot(year=year, source=source, metrics=metrics)


def annual_snapshot(year: int) -> AnnualSnapshot | None:
    """Load only the annual report containing ``year``.

    A missing report returns ``None``. In particular, 2023 is intentionally
    unavailable in the current report registry rather than being reconstructed
    from monthly observations.
    """
    for source, value_rows, count_rows in _ANNUAL_TABLES:
        snapshot = _annual_snapshot_from_tables(year, source, value_rows, count_rows)
        if snapshot is not None:
            return snapshot
    return None


def available_annual_years() -> tuple[int, ...]:
    return tuple(year for year in ANNUAL_YEAR_OPTIONS if annual_snapshot(year))


def latest_available_annual_year() -> int | None:
    years = available_annual_years()
    return max(years) if years else None


def normalise_monthly_record(row: Mapping[str, object]) -> dict[str, object] | None:
    """Normalise one extracted monthly report row.

    The function accepts typed registry values or OCR strings and leaves an
    absent cell as ``None``. It is intentionally conservative around merged or
    malformed cells so downstream aggregation cannot silently invent totals.
    """
    try:
        year = int(parse_numeric(row.get("year")))
    except (TypeError, ValueError):
        return None
    raw_month = str(row.get("month", "")).strip()
    month = next(
        (candidate for candidate in MONTHS if candidate.casefold() == raw_month.casefold()),
        MONTH_ALIASES.get(raw_month[:3].casefold()),
    )
    if month is None:
        return None
    normalised = {
        "year": year,
        "month": month,
        "month_number": MONTH_NUMBER[month],
        "source_note": str(row.get("source_note", "")).strip(),
    }
    for _, key, _ in VALUE_METRICS[:3] + COUNT_METRICS[:3]:
        normalised[key] = parse_numeric(row.get(key))
    normalised["total_v"] = (
        sum(normalised[key] for _, key, _ in VALUE_METRICS[:3])
        if all(normalised[key] is not None for _, key, _ in VALUE_METRICS[:3])
        else None
    )
    normalised["total_n"] = (
        sum(normalised[key] for _, key, _ in COUNT_METRICS[:3])
        if all(normalised[key] is not None for _, key, _ in COUNT_METRICS[:3])
        else None
    )
    return normalised


def monthly_records(rows: Iterable[Mapping[str, object]] | None = None) -> tuple[dict[str, object], ...]:
    """Return normalised, de-duplicated monthly report observations."""
    selected = rows if rows is not None else S.RAK_MONTHLY_TIMESERIES
    by_period: dict[tuple[int, int], dict[str, object]] = {}
    keys = tuple(key for _, key, _ in VALUE_METRICS[:3] + COUNT_METRICS[:3])
    for row in selected:
        normalised = normalise_monthly_record(row)
        if normalised is None:
            continue
        period = (normalised["year"], normalised["month_number"])
        current = by_period.get(period)
        if current is None:
            by_period[period] = normalised
            continue
        current_score = sum(current[key] is not None for key in keys)
        new_score = sum(normalised[key] is not None for key in keys)
        if new_score > current_score:
            by_period[period] = normalised
    return tuple(by_period[key] for key in sorted(by_period))


def _monthly_row_complete(row: Mapping[str, object]) -> bool:
    keys = tuple(key for _, key, _ in VALUE_METRICS[:3] + COUNT_METRICS[:3])
    return all(row.get(key) is not None for key in keys)


def available_quarters(year: int, rows: Iterable[Mapping[str, object]] | None = None) -> tuple[str, ...]:
    """Return only quarters with three complete monthly report rows."""
    records = {(row["year"], row["month_number"]): row for row in monthly_records(rows)}
    return tuple(
        quarter for quarter, months in QUARTER_MONTHS.items()
        if all(
            (year, month) in records and _monthly_row_complete(records[(year, month)])
            for month in months
        )
    )


def quarterly_snapshot(
    year: int,
    quarter: str,
    rows: Iterable[Mapping[str, object]] | None = None,
) -> QuarterlySnapshot | None:
    """Aggregate a complete monthly triplet; return ``None`` if incomplete."""
    quarter = str(quarter).upper()
    months = QUARTER_MONTHS.get(quarter)
    if months is None:
        return None
    records = {(row["year"], row["month_number"]): row for row in monthly_records(rows)}
    monthly = [records.get((year, month)) for month in months]
    if any(row is None or not _monthly_row_complete(row) for row in monthly):
        return None

    metrics: dict[str, float | int | None] = {}
    for _, key, _ in VALUE_METRICS[:3] + COUNT_METRICS[:3]:
        values = [row[key] for row in monthly]
        metrics[key] = sum(values)
    metrics["total_v"] = (
        sum(metrics[key] for _, key, _ in VALUE_METRICS[:3])
    )
    metrics["total_n"] = (
        sum(metrics[key] for _, key, _ in COUNT_METRICS[:3])
    )
    return QuarterlySnapshot(
        year=year,
        quarter=quarter,
        months=tuple(MONTHS[month - 1] for month in months),
        metrics=metrics,
        source_notes=tuple(row["source_note"] for row in monthly if row["source_note"]),
    )


def latest_completed_quarter(years: Iterable[int] = ANNUAL_YEAR_OPTIONS) -> tuple[int, str] | None:
    for year in sorted(years, reverse=True):
        quarters = available_quarters(year)
        if quarters:
            return year, quarters[-1]
    return None


def metric_rows(snapshot: AnnualSnapshot | QuarterlySnapshot) -> list[dict[str, object]]:
    """Return all six requested source metrics plus computed totals for tables."""
    rows = []
    for label, key, unit in ALL_METRICS:
        rows.append({"Metric": label, "Value": snapshot.metrics.get(key), "Unit": unit})
    return rows
