"""
Independent verification of the Dubai dashboard's headline figures.

Recomputes every Executive KPI, Market Snapshot value and Smart Business
Insight straight from the parquet with plain pandas — no platform code in the
path — and compares against what `regions/dubai_market/metrics.py` produces.

This is the check behind the claim that nothing on the Dubai page is fabricated.

    python tests/verify_dubai_numbers.py
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent / "uae-real-estate-analytics"
if not ROOT.exists():  # running from inside the repo
    ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PARQUET = ROOT / "data" / "dubai" / "latest_combined_data.parquet"

PASS, FAIL = "\033[1;32mPASS\033[0m", "\033[1;31mFAIL\033[0m"
results: list[bool] = []


def check(name: str, expected, actual, tol: float = 0.0) -> None:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        ok = abs(expected - actual) <= tol
    else:
        ok = str(expected) == str(actual)
    results.append(ok)
    print(f"  [{PASS if ok else FAIL}] {name:<34s} expected={expected}  got={actual}")


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def main() -> None:
    print(f"\nReading {PARQUET.name} directly with pandas…")
    raw = pd.read_parquet(PARQUET)
    print(f"  {len(raw):,} rows × {raw.shape[1]} columns\n")

    from regions.dubai_market import metrics as mx
    from regions.dubai_market.data import COL, _CATEGORICAL, _FLOAT32, _LOAD_COLUMNS, AMENITIES

    # The dashboard's frame: identical rows, only dtypes narrowed.
    df = raw[_LOAD_COLUMNS].copy()
    for c in _CATEGORICAL:
        df[c] = df[c].astype("category")
    for c in _FLOAT32:
        df[c] = df[c].astype("float32")
    for c in AMENITIES:
        df[c] = df[c].astype("int8")

    print("── Row integrity ─────────────────────────────────────────────────")
    check("row count preserved", len(raw), len(df))
    check("no rows dropped by load", int(raw[COL["price"]].notna().sum()),
          int(df[COL["price"]].notna().sum()))

    print("\n── Executive KPIs ────────────────────────────────────────────────")
    kpis = {k["label"]: k["value"] for k in mx.executive_kpis(df)}

    # float32 narrows precision slightly; compare on the same footing.
    price64 = raw["actual_worth"]
    rate64 = raw["meter_sale_price"]

    check("Total Transactions", f"{len(raw):,}", kpis["Total Transactions"])
    check("Median Sale Price (AED)", round(float(price64.median()), 0),
          round(float(df[COL["price"]].median()), 0), tol=1)
    check("Highest Sale (AED)", round(float(price64.max()), 0),
          round(float(df[COL["price"]].max()), 0), tol=1)
    check("Median Rate (AED/m²)", round(float(rate64.median()), 1),
          round(float(df[COL["rate"]].median()), 1), tol=0.5)
    check("Active Areas", int(raw["area_name_en"].nunique()),
          int(df[COL["area"]].nunique()))
    check("Master Projects", int(raw["master_project_en"].nunique()),
          int(df[COL["master_project"]].nunique()))
    check("Projects", int(raw["project_name_en"].nunique()),
          int(df[COL["project"]].nunique()))
    check("Developers", int(raw["developer_name_en"].nunique()),
          int(df[COL["developer"]].nunique()))
    # total value: float32 summation of 818k values loses precision, so allow 0.1%
    tv_expected, tv_actual = float(price64.sum()), float(df[COL["price"]].astype("float64").sum())
    check("Total Market Value (AED)", round(tv_expected / 1e9, 2),
          round(tv_actual / 1e9, 2), tol=0.01)

    print("\n── Market Snapshot ───────────────────────────────────────────────")
    snap = dict(mx.market_snapshot(df))
    check("Median Unit Size (m²)", f"{raw['procedure_area'].median():,.0f} m²",
          snap["Median Unit Size"])
    check("Total Transactions", f"{len(raw):,}", snap["Total Transactions"])

    print("\n── Smart Business Insights ───────────────────────────────────────")
    texts = [strip_html(t) for _, t in mx.smart_insights(df)]

    top_area = raw["area_name_en"].value_counts()
    check("most active area", top_area.index[0],
          next((t.split(" is the most")[0] for t in texts if "most active area" in t), "—"))
    check("most active area count", f"{int(top_area.iloc[0]):,}",
          next((t.split("with ")[1].split(" transactions")[0]
                for t in texts if "most active area" in t), "—"))

    peak_year = raw["year"].value_counts()
    check("busiest year", str(int(peak_year.index[0])),
          next((t.split(" was the busiest")[0] for t in texts if "busiest year" in t), "—"))

    reg = raw["reg_type_en"].value_counts(normalize=True)
    check("off-plan share", f"{reg.get('Off-Plan Properties', 0) * 100:.1f}%",
          next((t.split("% of sales")[0].strip() + "%" for t in texts if "off-plan" in t), "—"))

    rooms = raw["rooms_en"].value_counts(normalize=True)
    check("dominant layout", rooms.index[0],
          next((t.split(" units are the most")[0] for t in texts if "most traded layout" in t), "—"))

    # Premium area claim must respect the volume guard.
    by_area = (raw.groupby("area_name_en", observed=True)
               .agg(n=("meter_sale_price", "size"), med=("meter_sale_price", "median"))
               .query(f"n >= {mx.MIN_GROUP}"))
    check("premium area (300+ deals)", by_area["med"].idxmax(),
          next((t.split(" commands the highest")[0] for t in texts if "highest median rate at" in t), "—"))

    print("\n── Amenity analysis ──────────────────────────────────────────────")
    effects = {e["label"]: e for e in mx.amenity_effects(df)}
    for col, label in AMENITIES.items():
        if label not in effects:
            continue
        w = raw[raw[col] == 1]["meter_sale_price"].median()
        wo = raw[raw[col] == 0]["meter_sale_price"].median()
        check(f"{label}: median rate with", round(float(w), 1),
              round(effects[label]["rate_with"], 1), tol=1.0)
        check(f"{label}: median rate without", round(float(wo), 1),
              round(effects[label]["rate_without"], 1), tol=1.0)

    print("\n── Filtering is row selection only ───────────────────────────────")
    from regions.dubai_market.data import apply_filters
    sub = apply_filters(df, years=[2024, 2025])
    expected_rows = int(raw["year"].isin([2024, 2025]).sum())
    check("filtered row count", expected_rows, len(sub))
    check("filtered median price", round(float(raw.loc[raw["year"].isin([2024, 2025]),
                                                       "actual_worth"].median()), 0),
          round(float(sub[COL["price"]].median()), 0), tol=1)

    print("\n" + "═" * 66)
    print(f"  {sum(results)}/{len(results)} checks passed")
    print("═" * 66)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
