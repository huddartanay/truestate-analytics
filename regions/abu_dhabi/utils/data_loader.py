"""
Data loading and preprocessing utilities.
The runtime reads the build-time-prepared Abu Dhabi Parquet artifact.
"""
import pandas as pd
import streamlit as st
from pathlib import Path
import sys

# Ensure parent path is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import COLS, PARQUET_FILE, PREPARED_COLUMNS


def _data_path() -> Path:
    """Resolve the prepared Abu Dhabi artifact without a runtime conversion."""
    path = Path(__file__).parent.parent / PARQUET_FILE
    if path.exists():
        return path
    fallback = Path(PARQUET_FILE)
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"The prepared Abu Dhabi data artifact was not found: {PARQUET_FILE}"
    )


def data_source_signature() -> tuple[str, int, int]:
    """Return a cheap cache identity that changes when the artifact changes."""
    path = _data_path()
    stat = path.stat()
    return str(path.resolve()), int(stat.st_size), int(stat.st_mtime_ns)


@st.cache_data(show_spinner=False, max_entries=2)
def _read_prepared_parquet(path: str, size: int, modified_ns: int) -> pd.DataFrame:
    """Read one validated, build-time-prepared Abu Dhabi artifact."""
    del size, modified_ns  # They are cache keys, not read parameters.
    df = pd.read_parquet(path)
    missing = [column for column in PREPARED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "The prepared Abu Dhabi data artifact is missing required columns: "
            + ", ".join(missing)
        )
    return df.loc[:, list(PREPARED_COLUMNS)]


def load_data() -> pd.DataFrame:
    """
    Load the prepared Abu Dhabi Real Estate dataset.

    Cleaning, feature engineering and schema preparation happen once in
    ``tools/build_abu_dhabi_parquet.py``. Runtime never converts the CSV or
    rebuilds those deterministic columns during a user rerun.
    """
    path, size, modified_ns = data_source_signature()
    return _read_prepared_parquet(path, size, modified_ns)


@st.cache_data(show_spinner=False)
def get_apartments_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for residential apartments only.
    Mirrors notebook Step 3.3.
    """
    mask = (
        (df[COLS["asset_class"]] == "residential")
        & (df[COLS["property_type"]] == "apartment")
    )
    df_apt = df[mask].copy()
    # Drop rows missing both target variables (mirrors notebook)
    df_apt = df_apt.dropna(
        subset=[COLS["rate"], COLS["area_sqm"]]
    ).reset_index(drop=True)
    return df_apt


@st.cache_data(show_spinner=False)
def get_cleaned_apartments_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Notebook-accurate df_cleaned for apartments.
    Mirrors Steps 5 & 11: filter apartments → drop nulls →
    apply sequential 1st-99th percentile treatment on Rate, Price, Area.
    This is the SOURCE OF TRUTH for all apartment-specific visualizations.
    """
    df_cleaned = get_apartments_df(df)
    for col in [COLS["rate"], COLS["price"], COLS["area_sqm"]]:
        p1  = df_cleaned[col].quantile(0.01)
        p99 = df_cleaned[col].quantile(0.99)
        df_cleaned = df_cleaned[
            (df_cleaned[col] >= p1) & (df_cleaned[col] <= p99)
        ].copy()
    return df_cleaned.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def get_full_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return the full dataset (all property types)."""
    return df.copy()


def apply_filters(
    df: pd.DataFrame,
    years=None,
    property_types=None,
    districts=None,
    layouts=None,
    sale_types=None,
    sale_sequences=None,
    price_range=None,
    area_range=None,
) -> pd.DataFrame:
    """Apply sidebar filters to any dataframe."""
    filtered = df.copy()

    if years:
        filtered = filtered[filtered["Year"].isin(years)]

    if property_types:
        filtered = filtered[filtered[COLS["property_type"]].isin(property_types)]

    if districts:
        filtered = filtered[filtered[COLS["district"]].isin(districts)]

    if layouts:
        filtered = filtered[filtered[COLS["layout"]].isin(layouts)]

    if sale_types:
        filtered = filtered[filtered[COLS["sale_type"]].isin(sale_types)]

    if sale_sequences:
        filtered = filtered[filtered[COLS["sale_sequence"]].isin(sale_sequences)]

    if price_range:
        filtered = filtered[
            (filtered[COLS["price"]] >= price_range[0])
            & (filtered[COLS["price"]] <= price_range[1])
        ]

    if area_range:
        filtered = filtered[
            (filtered[COLS["area_sqm"]] >= area_range[0])
            & (filtered[COLS["area_sqm"]] <= area_range[1])
        ]

    return filtered


def format_currency(value: float, decimals: int = 0) -> str:
    """Format a value as AED currency."""
    if pd.isna(value):
        return "N/A"
    if value >= 1_000_000_000:
        return f"AED {value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"AED {value / 1_000:.1f}K"
    else:
        return f"AED {value:,.{decimals}f}"


def format_number(value: float, decimals: int = 0) -> str:
    """Format a number with thousands separator."""
    if pd.isna(value):
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:,.{decimals}f}"
