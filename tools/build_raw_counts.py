#!/usr/bin/env python3
"""
Precompute the RAW registry's monthly transaction counts.

    python tools/build_raw_counts.py

Reads `data/dubai/transactions.parquet` and writes
`data/dubai/raw_transaction_counts.parquet` — one row per (year, month) with the
residential-unit sale count and the all-transactions count.

This exists so a hosted deployment can answer the transaction-volume questions
without carrying the 78 MB registry. The output is that registry aggregated:
the same filter, the same groupby, the same numbers. It is not a sample, an
estimate or a substitute dataset, and the application only reads it when the
registry itself is absent.

Re-run this whenever `transactions.parquet` is replaced, or the hosted copy will
describe an older registry than the local one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "dubai" / "transactions.parquet"
OUT = ROOT / "data" / "dubai" / "raw_transaction_counts.parquet"

COLUMNS = ["instance_date", "trans_group_en", "property_type_en", "property_usage_en"]


def main() -> int:
    if not RAW.exists():
        print(f"error: {RAW} not found — nothing to aggregate.", file=sys.stderr)
        return 1

    raw = pd.read_parquet(RAW, columns=COLUMNS)
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)

    print(f"{RAW.name}  {RAW.stat().st_size / 1e6:>7.1f} MB  "
          f"->  {OUT.name}  {OUT.stat().st_size / 1e3:>7.1f} KB")
    print(f"rows: {len(out):,}   "
          f"residential unit sales: {int(out['transactions'].sum()):,}   "
          f"all transactions: {int(out['all_transactions'].sum()):,}")
    print(f"period: {int(out['year'].min())} – {int(out['year'].max())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
