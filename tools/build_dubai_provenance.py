"""
Build data/dubai/provenance.json — a small, reproducible record of how the
CLEANED Dubai dataset relates to the RAW transaction registry.

Run it whenever either parquet is replaced:

    python tools/build_dubai_provenance.py

The app reads only the resulting JSON at runtime, so the 81 MB raw file is
never loaded to render a page. Neither source file is modified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "dubai"
RAW = DATA / "transactions.parquet"
CLEAN = DATA / "latest_combined_data.parquet"
OUT = DATA / "provenance.json"


def main() -> None:
    raw = pd.read_parquet(
        RAW,
        columns=["trans_group_en", "property_type_en", "property_usage_en",
                 "reg_type_en", "instance_date", "area_name_en", "transaction_id"],
    )
    raw_dates = pd.to_datetime(raw["instance_date"], errors="coerce")

    clean = pd.read_parquet(
        CLEAN,
        columns=["trans_group_en", "property_type_en", "property_usage_en",
                 "instance_date", "area_name_en", "transaction_id"],
    )

    # The cleaned set is the residential-unit sales slice of the registry.
    slice_mask = (
        (raw["trans_group_en"] == "Sales")
        & (raw["property_type_en"] == "Unit")
        & (raw["property_usage_en"] == "Residential")
    )

    payload = {
        "raw": {
            "file": RAW.name,
            "rows": int(len(raw)),
            "columns": int(pd.read_parquet(RAW, columns=["transaction_id"]).shape[1]) or None,
            "date_min": str(raw_dates.min().date()),
            "date_max": str(raw_dates.max().date()),
            "areas": int(raw["area_name_en"].nunique()),
            "transaction_groups": {k: int(v) for k, v in raw["trans_group_en"].value_counts().items()},
            "property_types": {k: int(v) for k, v in raw["property_type_en"].value_counts().items()},
            "property_usage": {k: int(v) for k, v in raw["property_usage_en"].value_counts().head(6).items()},
            "registration_types": {k: int(v) for k, v in raw["reg_type_en"].value_counts().items()},
            "residential_unit_sales": int(slice_mask.sum()),
        },
        "clean": {
            "file": CLEAN.name,
            "rows": int(len(clean)),
            "date_min": str(pd.to_datetime(clean["instance_date"]).min().date()),
            "date_max": str(pd.to_datetime(clean["instance_date"]).max().date()),
            "areas": int(clean["area_name_en"].nunique()),
            "scope": {
                "trans_group_en": sorted(map(str, clean["trans_group_en"].dropna().unique())),
                "property_type_en": sorted(map(str, clean["property_type_en"].dropna().unique())),
                "property_usage_en": sorted(map(str, clean["property_usage_en"].dropna().unique())),
            },
        },
    }

    # Column counts, read from the schemas rather than materialising the frames.
    import pyarrow.parquet as pq

    payload["raw"]["columns"] = pq.ParquetFile(RAW).metadata.num_columns
    payload["clean"]["columns"] = pq.ParquetFile(CLEAN).metadata.num_columns

    payload["relationship"] = {
        "note": (
            "The cleaned file is the residential-unit SALES slice of the raw registry, "
            "restricted to 2010 onwards and enriched with engineered time parts, unit "
            "attributes, amenity flags and building / developer scoring."
        ),
        "raw_matching_slice": int(slice_mask.sum()),
        "clean_rows": int(len(clean)),
        "coverage_pct": round(100 * len(clean) / max(int(slice_mask.sum()), 1), 1),
        "added_columns": payload["clean"]["columns"] - payload["raw"]["columns"],
    }

    # ── Does the off-plan / existing label behave the way the words claim? ──
    #
    # This is a validation fact, not a live metric: it does not move with the
    # sidebar filters, and measuring it needs the completion-date columns the
    # dashboard deliberately does not load. So it is computed once, here.
    timing = pd.read_parquet(
        CLEAN,
        columns=["reg_type_en", "instance_date", "completion_date",
                 "meter_sale_price", "building_name_en"],
    )
    sold = pd.to_datetime(timing["instance_date"], errors="coerce")
    done = pd.to_datetime(timing["completion_date"], errors="coerce")
    years_after = (sold - done).dt.days / 365.25

    reg_timing = {}
    for lbl in sorted(timing["reg_type_en"].dropna().unique()):
        s = years_after[timing["reg_type_en"] == lbl].dropna()
        if len(s) < 100:
            continue
        reg_timing[str(lbl)] = {
            "rows_with_completion_date": int(len(s)),
            "median_years_vs_completion": round(float(s.median()), 1),
            "sold_before_completion_pct": round(float((s < 0).mean() * 100), 1),
        }

    # Which buildings each side actually transacts in, valued at the building's
    # own median rate. If these differ, the headline gap is about the stock.
    per_building = timing.groupby("building_name_en", observed=True)["meter_sale_price"].median()
    counts = (timing.groupby(["building_name_en", "reg_type_en"], observed=True)
                    .size().unstack(fill_value=0))
    counts = counts[counts.sum(axis=1) >= 50]
    rates = per_building.reindex(counts.index)
    stock = {str(lbl): round(float((rates * counts[lbl]).sum() / counts[lbl].sum()))
             for lbl in counts.columns if counts[lbl].sum()}

    both = {"Off-Plan Properties", "Existing Properties"}
    payload["registration_type"] = {
        "note": ("Evidence that the off-plan / existing label means what it says, and "
                 "that the two labels are attached to different stock."),
        "completion_date_populated_pct": round(float(done.notna().mean() * 100), 1),
        "timing": reg_timing,
        "building_rate_weighted_by_side": stock,
        "building_rate_gap_pct": (
            round((stock["Off-Plan Properties"] / stock["Existing Properties"] - 1) * 100, 1)
            if both <= set(stock) else None),
    }

    OUT.write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
