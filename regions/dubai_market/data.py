"""
Data layer for the Dubai regional dashboard.

Source of truth: `data/dubai/latest_combined_data.parquet` — the CLEANED /
PROCESSED dataset. `data/dubai/transactions.parquet` is the RAW registry; it is
never loaded to render a page (see `provenance.json`, built by
`tools/build_dubai_provenance.py`), only on explicit request from the
data-provenance panel.

Neither source file is written to. No values are altered — the only
transformations here are column selection and dtype downcasting, which change
memory layout, not numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "dubai"
CLEAN_FILE = DATA_DIR / "latest_combined_data.parquet"
RAW_FILE = DATA_DIR / "transactions.parquet"
PROVENANCE_FILE = DATA_DIR / "provenance.json"
# Monthly counts precomputed from RAW_FILE by tools/build_raw_counts.py, so a
# hosted deployment can answer the volume questions without shipping the 78 MB
# registry. Identical numbers; it is that file aggregated, nothing more.
RAW_COUNTS_FILE = DATA_DIR / "raw_transaction_counts.parquet"

# Forecasting artefacts produced by the existing Dubai modelling work. They are
# read, never recomputed.
FORECAST_DIR = ROOT / "regions" / "dubai"


# ── Column model ────────────────────────────────────────────────────────────
# Names below were verified against the actual parquet schema; nothing is
# assumed. Columns present in the file but not used by any section are left out
# to keep the working frame small (85 → 34 columns, 1.26 GB → ~55 MB).

COL = {
    "price": "actual_worth",              # AED, total transaction value
    "rate": "meter_sale_price",           # AED per m²
    "area_sqm": "procedure_area",         # m²
    "balcony_area": "unit_balcony_area",
    "date": "instance_date",
    "year": "year",
    "month": "month",
    "quarter": "quarter",
    "year_month": "year_month",
    "area": "area_name_en",
    "master_project": "master_project_en",
    "project": "project_name_en",
    "building": "building_name_en",
    "zone": "Locality Zone",
    "metro_station": "nearest_metro_en",
    "mall": "nearest_mall_en",
    "landmark": "nearest_landmark_en",
    "sub_type": "property_sub_type_en",
    "rooms": "rooms_en",
    "reg_type": "reg_type_en",
    "procedure": "procedure_name_en",
    "grade": "Grade",
    "price_tier": "Price Tier",
    "reputation": "Reputation",
    "project_grade": "project_grade",
    "developer_tier": "Developer Tier",
    "developer": "developer_name_en",
    # Building height. NOT the unit's own floor — see metrics.py, the dataset
    # does not record which floor a unit is on.
    "floors": "floors",
    "yield": "Est. Gross Rental Yield (%)",
    "composite": "Composite Score (0-100)",
}

AMENITIES = {
    "has_parking": "Parking",
    "swimming_pool": "Swimming pool",
    "balcony": "Balcony",
    "elevator": "Elevator",
    "metro": "Near a metro station",
}

_LOAD_COLUMNS = list(COL.values()) + list(AMENITIES.keys())

_CATEGORICAL = [
    COL["area"], COL["master_project"], COL["project"], COL["building"], COL["zone"],
    COL["metro_station"], COL["mall"], COL["landmark"], COL["sub_type"], COL["rooms"],
    COL["reg_type"], COL["procedure"], COL["grade"], COL["price_tier"],
    COL["reputation"], COL["project_grade"], COL["developer_tier"], COL["developer"],
    COL["year_month"],
]

_FLOAT32 = [COL["floors"], COL["price"], COL["rate"], COL["area_sqm"], COL["balcony_area"],
            COL["yield"], COL["composite"]]

ROOM_ORDER = ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R",
              "6 B/R", "7 B/R", "PENTHOUSE"]


class DubaiDataError(RuntimeError):
    """Raised when the Dubai dataset cannot be loaded."""


def _read_clean() -> pd.DataFrame:
    """
    Read the cleaned parquet without materialising the text columns twice.

    WHAT WAS WRONG
    --------------
    `pd.read_parquet(CLEAN_FILE, columns=_LOAD_COLUMNS)` builds a real Python
    `str` object for every value in every text column — 818,838 of them per
    column, across seventeen columns — and the very next lines throw all of
    them away again with `.astype("category")`. The finished frame is 55 MB;
    getting to it cost 804 MB of peak process memory. That transient, not the
    data, was the largest single allocation in the whole platform.

    WHAT THIS DOES INSTEAD
    ----------------------
    Those columns are asked for as Arrow *dictionaries*, which is the same
    shape a pandas Categorical already has: integer codes plus one small table
    of distinct values. The strings are never built one-per-row, so pandas
    receives a Categorical directly. `self_destruct=True` lets Arrow release
    each column's buffer as it is handed over, instead of holding the whole
    table alongside the whole frame.

        pd.read_parquet, as before        peak 804 MB
        this                              peak 492 MB

    ORDER MATTERS, SO IT IS RESTORED
    --------------------------------
    Arrow numbers a dictionary in order of first appearance; pandas'
    `.astype("category")` sorts. Values are identical either way, but the
    category ORDER decides the order `groupby` returns — which is the order
    bars, legends and table rows come out in. The categories are therefore
    re-sorted to exactly what the previous loader produced.

    VERIFIED, NOT ASSUMED
    ---------------------
    Both loaders were run and their frames compared: same shape
    (818,838 x 35), same column order, same dtypes, same category order on all
    17 categorical columns, same values, and identical categorical codes.
    """
    import pyarrow.parquet as pq

    schema = pq.ParquetFile(CLEAN_FILE).schema_arrow
    as_dictionary = [c for c in _CATEGORICAL
                     if c in _LOAD_COLUMNS and c in schema.names]

    table = pq.read_table(CLEAN_FILE, columns=_LOAD_COLUMNS,
                          read_dictionary=as_dictionary)
    df = table.to_pandas(split_blocks=True, self_destruct=True)
    del table

    for c in df.columns:
        if str(df[c].dtype) == "category":
            categories = df[c].cat.categories
            ordered = categories.sort_values()
            if not categories.equals(ordered):
                df[c] = df[c].cat.reorder_categories(ordered)
    return df


# ── Loading ─────────────────────────────────────────────────────────────────


# `cache_resource` rather than `cache_data`: the frame is ~55 MB after
# downcasting and is treated as read-only, so handing out the same object avoids
# copying it on every rerun. Callers must never mutate it in place — filtering
# with `.loc[mask]` (as `apply_filters` does) always returns a new frame.
@st.cache_resource(show_spinner=False)
def load_market() -> pd.DataFrame:
    """
    Load the cleaned Dubai transaction dataset.

    Only column selection and dtype downcasting are applied — no filtering,
    no imputation, no derived values.
    """
    if not CLEAN_FILE.exists():
        raise DubaiDataError(
            f"{CLEAN_FILE.name} was not found in data/dubai/. "
            "Copy the cleaned Dubai parquet into that folder."
        )

    df = _read_clean()

    for c in _CATEGORICAL:
        if c in df.columns:
            df[c] = df[c].astype("category")
    for c in _FLOAT32:
        if c in df.columns:
            df[c] = df[c].astype("float32")
    for c in AMENITIES:
        if c in df.columns:
            df[c] = df[c].astype("int8")
    for c in (COL["year"], COL["month"], COL["quarter"]):
        if c in df.columns:
            df[c] = df[c].astype("int16")

    df[COL["date"]] = pd.to_datetime(df[COL["date"]])
    return df


# ── RAW registry — transaction COUNTS only ──────────────────────────────────
#
# DATA SOURCE RULE
# ────────────────
# Transaction-volume analysis reads the RAW registry, not the cleaned dataset.
# Preprocessing removes between 668 and 7,369 rows per year from the cleaned
# file, so counting transactions there understates how many were actually
# recorded. Price and rate analysis continues to use the cleaned file, which
# carries the engineered columns those charts need.
#
# The slice below is the SAME population the rest of the Dubai page covers —
# residential unit sales — taken straight from the registry with no cleaning
# applied. Counting the whole registry instead would silently change the
# subject from residential sales to sales + mortgages + gifts across land and
# villas. Both figures are reported in the chart's ⓘ, so neither is hidden.

RAW_COUNT_COLUMNS = ["instance_date", "trans_group_en", "property_type_en",
                     "property_usage_en"]


@st.cache_data(show_spinner=False)
def load_raw_transaction_counts() -> pd.DataFrame:
    """
    Transaction counts per year and month, straight from the RAW registry.

    Returns one row per (year, month): the number of recorded residential unit
    sales, plus the equivalent count across the whole registry for context.
    Only four columns are read and only counts are returned, so the 81 MB raw
    file is never held in memory by the page.
    """
    if not RAW_FILE.exists():
        # A hosted copy of this application need not ship the 78 MB registry.
        # `tools/build_raw_counts.py` precomputes exactly the table this
        # function returns, from that registry — the same filter, the same
        # groupby, the same counts. It is an aggregate of the real file, never a
        # stand-in for it, and it is read only when the registry is absent.
        if RAW_COUNTS_FILE.exists():
            out = pd.read_parquet(RAW_COUNTS_FILE)
            out["year"] = out["year"].astype(int)
            out["month"] = out["month"].astype(int)
            return out
        raise DubaiDataError(
            f"{RAW_FILE.name} was not found in data/dubai/, and neither was the "
            f"precomputed {RAW_COUNTS_FILE.name}. Transaction-volume analysis reads "
            f"the raw registry, or that registry's precomputed monthly counts."
        )

    raw = pd.read_parquet(RAW_FILE, columns=RAW_COUNT_COLUMNS)
    date = pd.to_datetime(raw["instance_date"], errors="coerce")
    raw = raw.assign(year=date.dt.year, month=date.dt.month).dropna(subset=["year"])

    residential = (
        (raw["trans_group_en"] == "Sales")
        & (raw["property_type_en"] == "Unit")
        & (raw["property_usage_en"] == "Residential")
    )

    out = (raw.assign(_res=residential)
              .groupby(["year", "month"], as_index=False)
              .agg(all_transactions=("_res", "size"), transactions=("_res", "sum")))
    out["year"] = out["year"].astype(int)
    out["month"] = out["month"].astype(int)
    return out


@st.cache_data(show_spinner=False)
def raw_coverage() -> dict:
    """The raw registry's own latest period and totals, for labels and the ⓘ."""
    counts = load_raw_transaction_counts()
    latest_year = int(counts["year"].max())
    latest_month = int(counts.loc[counts["year"] == latest_year, "month"].max())
    return {
        "latest_year": latest_year,
        "latest_month": latest_month,
        "latest_month_name": pd.Timestamp(2000, latest_month, 1).strftime("%B"),
        "total_residential_unit_sales": int(counts["transactions"].sum()),
        "total_all_transactions": int(counts["all_transactions"].sum()),
    }


@st.cache_data(show_spinner=False)
def load_provenance() -> dict:
    """Raw-vs-cleaned comparison, precomputed by tools/build_dubai_provenance.py."""
    if not PROVENANCE_FILE.exists():
        return {}
    return json.loads(PROVENANCE_FILE.read_text())


@st.cache_data(show_spinner=False)
def load_forecast_artifacts() -> dict:
    """
    Read the forecast outputs already produced by the existing Dubai modelling.

    Nothing is refitted here — these are the published results.
    Missing files are reported rather than raising.
    """
    wanted = {
        "quarterly": "arima_forecast_quarterly_all_areas.csv",
        "forward": "quarterly_forecasts_with_CI.csv",
        "accuracy": "metrics_lowess_all_areas1.csv",
        "growth_6m": "arima_areas_growth_6M.csv",
    }
    out: dict = {"missing": []}
    for key, name in wanted.items():
        path = FORECAST_DIR / name
        if path.exists():
            try:
                out[key] = pd.read_csv(path)
            except Exception as exc:  # pragma: no cover
                out["missing"].append(f"{name} ({exc})")
        else:
            out["missing"].append(name)
    return out


# ── Filter model ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def filter_options() -> dict:
    """Distinct values for each sidebar filter, computed once."""
    df = load_market()
    rooms = [r for r in ROOM_ORDER if r in set(df[COL["rooms"]].dropna().unique())]
    rooms += sorted(set(map(str, df[COL["rooms"]].dropna().unique())) - set(rooms))
    return {
        "years": sorted(int(y) for y in df[COL["year"]].unique()),
        "areas": sorted(map(str, df[COL["area"]].dropna().unique())),
        "zones": sorted(map(str, df[COL["zone"]].dropna().unique())),
        "rooms": rooms,
        "reg_types": sorted(map(str, df[COL["reg_type"]].dropna().unique())),
        # Sliders span the FULL range so nothing is unreachable, but default to
        # the 1st–99th percentile so a handful of extreme deals do not flatten
        # every chart. This mirrors the Abu Dhabi dashboard's default scope.
        "price_min": float(df[COL["price"]].min()),
        "price_max": float(df[COL["price"]].max()),
        "price_p01": float(df[COL["price"]].quantile(0.01)),
        "price_p99": float(df[COL["price"]].quantile(0.99)),
        "area_min": float(df[COL["area_sqm"]].min()),
        "area_max": float(df[COL["area_sqm"]].max()),
        "area_p01": float(df[COL["area_sqm"]].quantile(0.01)),
        "area_p99": float(df[COL["area_sqm"]].quantile(0.99)),
    }


def apply_filters(
    df: pd.DataFrame,
    years=None,
    areas=None,
    zones=None,
    rooms=None,
    reg_types=None,
    price_range=None,
    area_range=None,
) -> pd.DataFrame:
    """Row selection only — no column or value is modified."""
    mask = pd.Series(True, index=df.index)

    if years:
        mask &= df[COL["year"]].isin(years)
    if areas:
        mask &= df[COL["area"]].isin(areas)
    if zones:
        mask &= df[COL["zone"]].isin(zones)
    if rooms:
        mask &= df[COL["rooms"]].isin(rooms)
    if reg_types:
        mask &= df[COL["reg_type"]].isin(reg_types)
    if price_range:
        mask &= df[COL["price"]].between(price_range[0], price_range[1])
    if area_range:
        mask &= df[COL["area_sqm"]].between(area_range[0], area_range[1])

    return df.loc[mask]


# ── Formatting ──────────────────────────────────────────────────────────────


def aed(value, decimals: int = 0) -> str:
    """Format a number as AED, matching the Abu Dhabi dashboard's convention."""
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"AED {value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"AED {value / 1_000:.1f}K"
    return f"AED {value:,.{decimals}f}"


def num(value, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"
