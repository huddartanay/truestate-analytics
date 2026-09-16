"""Build the runtime Abu Dhabi Parquet artifact from the immutable CSV source."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regions.abu_dhabi.config.settings import COLS, PARQUET_FILE, PREPARED_COLUMNS

SOURCE = ROOT / "regions" / "abu_dhabi" / "Abu_Dhabi_Sales_Cleaned (1).csv"
TARGET = SOURCE.parent / PARQUET_FILE


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the existing loader's deterministic preparation at build time."""
    df = df.drop_duplicates().reset_index(drop=True)
    date_col = COLS["date"]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["Year"] = df[date_col].dt.year
    df["Month_Num"] = df[date_col].dt.month
    df["Quarter"] = df[date_col].dt.quarter
    df["Month"] = df[date_col].dt.strftime("%B")
    df["YearMonth"] = df[date_col].dt.to_period("M").astype(str)
    df["YearQuarter"] = df["Year"].astype(str) + " Q" + df["Quarter"].astype(str)

    for col in [COLS["price"], COLS["area_sqm"], COLS["rate"], COLS["land_area"]]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        COLS["property_type"], COLS["asset_class"], COLS["layout"],
        COLS["district"], COLS["community"], COLS["project"],
        COLS["sale_type"], COLS["sale_sequence"],
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df.loc[:, list(PREPARED_COLUMNS)]


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    prepared = prepare(pd.read_csv(SOURCE, low_memory=False))
    prepared.to_parquet(TARGET, engine="pyarrow", compression="snappy", index=False)
    print(
        f"wrote {TARGET} rows={len(prepared):,} columns={len(prepared.columns)} "
        f"bytes={TARGET.stat().st_size:,}"
    )


if __name__ == "__main__":
    main()
