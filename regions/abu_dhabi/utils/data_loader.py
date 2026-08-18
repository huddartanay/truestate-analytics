"""
Data loading and preprocessing utilities.
Mirrors the logic from the original notebook exactly.
"""
import pandas as pd
import numpy as np
import streamlit as st
from pathlib import Path
import sys
import os

# Ensure parent path is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DATA_FILE, COLS


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Load and clean the Abu Dhabi Real Estate dataset.
    Mirrors notebook Steps 1 & 2 exactly.
    """
    # Locate the CSV relative to this file's parent directory
    data_path = Path(__file__).parent.parent / DATA_FILE
    if not data_path.exists():
        # Try current working directory
        data_path = Path(DATA_FILE)

    df = pd.read_csv(data_path, low_memory=False)

    # ── 1. Drop duplicates ────────────────────────────────────────────────────
    df = df.drop_duplicates().reset_index(drop=True)

    # ── 2. Parse date column ──────────────────────────────────────────────────
    date_col = COLS["date"]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # ── 3. Feature Engineering (Temporal) ────────────────────────────────────
    df["Year"] = df[date_col].dt.year
    df["Month_Num"] = df[date_col].dt.month
    df["Quarter"] = df[date_col].dt.quarter
    df["Month"] = df[date_col].dt.strftime("%B")
    df["YearMonth"] = df[date_col].dt.to_period("M").astype(str)
    df["YearQuarter"] = (
        df["Year"].astype(str) + " Q" + df["Quarter"].astype(str)
    )

    # ── 4. Numeric coercion ───────────────────────────────────────────────────
    for col in [COLS["price"], COLS["area_sqm"], COLS["rate"], COLS["land_area"]]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 5. Strip string columns ───────────────────────────────────────────────
    str_cols = [
        COLS["property_type"], COLS["asset_class"], COLS["layout"],
        COLS["district"], COLS["community"], COLS["project"],
        COLS["sale_type"], COLS["sale_sequence"],
    ]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df


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
