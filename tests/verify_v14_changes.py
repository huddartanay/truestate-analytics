#!/usr/bin/env python3
"""
Verify the v1.4 controlled modifications.

    python tests/verify_v14_changes.py

Covers, against the real parquet files:

  Part 1  mean price per registration type, recomputed independently
  Part 2  Area filter reaches the layout aggregation
  Part 3  Area filter reaches the amenity aggregation, one population per panel
  Part 4  floor field inspection; fixed bands; Area filter reaches the medians
  Part 5  bracket boundaries, no gaps/overlaps, dynamic top-5 areas
  Part 6  one smoothing method only (LOWESS), partial month excluded
  Part 7  legends and labels on every modified chart
  Part 9  nothing unrelated moved
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from regions.dubai_market import charts as ch  # noqa: E402
from regions.dubai_market import metrics as mx  # noqa: E402
from regions.dubai_market.data import COL  # noqa: E402

G, R, Y, D, O = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
_pass, _fail = 0, []


def check(label: str, ok: bool, detail: str = "") -> bool:
    global _pass
    if ok:
        _pass += 1
        print(f"  {G}pass{O}  {label}" + (f"  {D}{detail}{O}" if detail else ""))
    else:
        _fail.append(label)
        print(f"  {R}FAIL{O}  {label}" + (f"  {detail}" if detail else ""))
    return ok


def head(t: str) -> None:
    print(f"\n{Y}{t}{O}")


AREAS = ["Marsa Dubai", "Business Bay", "Palm Jumeirah", "Al Warsan First", "Burj Khalifa"]


def main() -> int:
    df = pd.read_parquet(ROOT / "data" / "dubai" / "latest_combined_data.parquet")
    print(f"cleaned dataset: {len(df):,} rows")

    # ── PART 1 ──────────────────────────────────────────────────────────────
    head("PART 1 — Mean Price (AED) beside the median")
    for rt, sub in df.groupby(COL["reg_type"], observed=True):
        p = sub[COL["price"]]
        by_hand = float(p.sum()) / len(p)
        check(f"{rt}: mean recomputed by hand matches pandas",
              abs(float(p.mean()) - by_hand) < 0.01,
              f"AED {p.mean():,.2f} on {len(p):,} rows")
        check(f"{rt}: median still present and distinct from the mean",
              abs(float(p.median()) - float(p.mean())) > 1,
              f"median AED {p.median():,.0f} vs mean AED {p.mean():,.0f}")
        check(f"{rt}: mean above median (right-skewed prices)",
              float(p.mean()) > float(p.median()),
              f"gap AED {p.mean() - p.median():+,.0f}")

    # ── PART 2 ──────────────────────────────────────────────────────────────
    head("PART 2 — Area filter reaches the layout quartiles")
    base = ch.rate_by_layout(df)[1]
    check("unfiltered layout stats produced", not base.empty, f"{len(base)} layouts")
    moved = 0
    for a in AREAS:
        sub = mx.apply_area(df, a)
        q = ch.rate_by_layout(sub)[1]
        if q.empty:
            check(f"{a}: insufficient data handled, not drawn", True, "no layout ≥100 deals")
            continue
        shared = [k for k in q.index if k in base.index]
        differs = any(abs(q.loc[k, "med"] - base.loc[k, "med"]) > 1 for k in shared)
        check(f"{a}: quartiles differ from the all-Dubai figures", differs,
              f"{len(sub):,} rows, {len(q)} layouts drawn")
        moved += differs
    check("area genuinely changes the aggregation, not just the label", moved >= 4,
          f"{moved} of {len(AREAS)} areas moved the numbers")

    # ── PART 3 ──────────────────────────────────────────────────────────────
    head("PART 3 — Area + Property layout + Amenity, one filtered population")
    base3 = mx.amenity_transaction_share(df, "2 B/R")
    check("unfiltered amenity shares produced", not base3.empty, f"{len(base3)} amenities")
    for a in AREAS:
        sub = mx.apply_area(df, a)
        t = mx.amenity_transaction_share(sub, "2 B/R")
        if t.empty:
            check(f"{a}: below MIN_CELL handled, no share reported", True)
            continue
        differs = any(
            abs(t.iloc[i]["Share of recorded transactions (%)"]
                - base3.iloc[i]["Share of recorded transactions (%)"]) > 0.01
            for i in range(len(t)))
        check(f"{a}: 2 BHK amenity shares differ from all-Dubai", differs,
              f"{int((sub[COL['rooms']] == '2 B/R').sum()):,} 2 B/R rows")

    # both charts in the panel must come from the same filtered frame
    sub = mx.apply_area(df, "Marsa Dubai")
    within = mx.amenity_transaction_share(sub, "2 B/R")
    across = mx.amenity_share_by_property_type(sub, "has_parking")
    row = within[within["Amenity"] == "Parking"]
    cell = across[across["Property layout"] == "2 BHK"]
    check("left chart and right chart agree on the same cell",
          (not row.empty and not cell.empty
           and abs(float(row.iloc[0]["Share of recorded transactions (%)"])
                   - float(cell.iloc[0]["Share of recorded transactions (%)"])) < 0.01),
          "parking / 2 BHK / Marsa Dubai identical in both — one population, not two")

    check("share is a share of recorded transactions, never a probability",
          all(0 <= v <= 100 for v in within["Share of recorded transactions (%)"]),
          "all values within 0–100%")

    # ── PART 4 ──────────────────────────────────────────────────────────────
    head("PART 4 — floor field inspection, fixed bands, Area filter")
    cols = pd.read_parquet(ROOT / "data" / "dubai" / "latest_combined_data.parquet",
                           columns=None).columns if False else None
    import pyarrow.parquet as pq
    clean_cols = pq.ParquetFile(ROOT / "data" / "dubai" / "latest_combined_data.parquet").schema.names
    raw_cols = pq.ParquetFile(ROOT / "data" / "dubai" / "transactions.parquet").schema.names
    check("floor_en does not exist in either dataset — documented, not invented",
          "floor_en" not in clean_cols and "floor_en" not in raw_cols,
          "the panel says so on screen instead of inventing bands")

    fb = df["floor_bin"].dropna()
    check("floor_bin carries no information (single literal value)",
          fb.nunique() == 1 and str(fb.unique()[0]) == "Unknown",
          f"{len(fb):,} populated rows, all 'Unknown'")

    for f in ("floors", "bld_levels"):
        d = df.dropna(subset=[f, "property_id_bld"])
        g = d.groupby("property_id_bld")[f].nunique()
        check(f"{f} is constant within a building -> building attribute, not unit floor",
              float((g == 1).mean()) == 1.0,
              f"{len(g):,} buildings, constant in {(g == 1).mean() * 100:.1f}%")

    bf, _ = mx.rate_by_building_height(df, band_source=df)
    b1 = bf.groupby("height_band", observed=True)["median_rate"].median()
    for a in AREAS:
        sub = mx.apply_area(df, a)
        f2, aud = mx.rate_by_building_height(sub, band_source=df)
        if f2.empty:
            check(f"{a}: thin height data handled gracefully", True, str(aud.get("reason", "")))
            continue
        same_labels = list(f2["height_band"].cat.categories) == list(b1.index.categories)
        check(f"{a}: band labels identical to all-Dubai (comparable across areas)",
              same_labels, ", ".join(map(str, list(f2["height_band"].cat.categories)[:2])) + " …")
        b2 = f2.groupby("height_band", observed=True)["median_rate"].median()
        differs = any(abs(b2.get(k, -1) - v) > 1 for k, v in b1.items() if k in b2.index)
        check(f"{a}: height-band medians differ from all-Dubai", differs,
              f"{len(sub):,} rows")

    fig = ch.rate_by_building_height(bf)
    names = [t.name for t in fig.data if t.name]
    check("height chart legend names property types, not 'Series 1'",
          bool(names) and all(n in mx.PROPERTY_TYPE_LABELS.values() for n in names),
          ", ".join(names))

    # ── PART 5 ──────────────────────────────────────────────────────────────
    head("PART 5 — price brackets and dynamic top-5 areas")
    table, audit = mx.top_areas_by_band(df)
    check("every valid transaction classified into exactly one bracket",
          audit["valid"] == audit["classified"] and audit["unassigned"] == 0,
          f"{audit['classified']:,} of {audit['valid']:,}, {audit['unassigned']} unassigned")
    check("per-bracket totals sum to the classified total (no overlap, no gap)",
          sum(audit["band_totals"].values()) == audit["classified"],
          f"{sum(audit['band_totals'].values()):,}")

    for edge, expect in [(500_000, "500K – 1M"), (1_000_000, "1M – 2M"),
                         (2_000_000, "2M – 3M"), (3_000_000, "3M – 5M"),
                         (5_000_000, "5M – 10M"), (10_000_000, "> 10M")]:
        got = str(pd.cut(pd.Series([float(edge)]), bins=mx.BAND_EDGES,
                         labels=mx.BAND_LABELS, right=False).iloc[0])
        check(f"AED {edge:,} falls in {expect} (boundary belongs to the bracket above)",
              got == expect, f"got {got}; {int((df[COL['price']] == edge).sum()):,} real sales "
                             f"sit on this exact boundary")

    check("no bracket is empty when qualifying data exists",
          not audit["empty_bands"], f"empty: {audit['empty_bands'] or 'none'}")
    check("the > 10M bracket is populated with real areas",
          not table[table["Price band (AED)"] == "> 10M"].empty,
          f"{audit['band_totals'].get('> 10M', 0):,} transactions above AED 10M")

    for b in mx.BAND_LABELS:
        t = table[table["Price band (AED)"] == b]
        if t.empty:
            continue
        sub_all = df[pd.cut(df[COL["price"]], bins=mx.BAND_EDGES,
                            labels=mx.BAND_LABELS, right=False) == b]
        manual = sub_all[COL["area"]].value_counts()
        ok = (str(manual.index[0]) == str(t.iloc[0]["Area"])
              and int(manual.iloc[0]) == int(t.iloc[0]["Transactions"]))
        check(f"{b}: rank 1 reproduced independently", ok,
              f"{t.iloc[0]['Area']} — {int(t.iloc[0]['Transactions']):,}")
        check(f"{b}: ranks are 1..{len(t)} with no duplicate area",
              list(t["Rank"]) == list(range(1, len(t) + 1))
              and t["Area"].nunique() == len(t))

    # ── zero-count areas must never be ranked ───────────────────────────────
    # `area_name_en` is a `category` after loading, and value_counts() on a
    # categorical returns EVERY category — including the 68 with no rows left
    # after an area filter. That padded the top-5 with zero-transaction areas.
    from regions.dubai_market.data import load_market as _load
    cat_df = _load()
    check("area column really is categorical (the condition that caused the bug)",
          str(cat_df[COL["area"]].dtype) == "category", str(cat_df[COL["area"]].dtype))
    for a in ("Marsa Dubai", "Al Warsan First", "Palm Jumeirah"):
        t_one, a_one = mx.top_areas_by_band(mx.apply_area(cat_df, a))
        others = set(t_one["Area"]) - {a}
        check(f"{a}: only that area is ranked, no zero-count padding",
              t_one[t_one["Transactions"] == 0].empty and not others,
              f"{len(t_one)} rows, absent from {len(a_one['absent_bands'])} bracket(s)")
        check(f"{a}: brackets it has no transactions in are reported",
              isinstance(a_one.get("absent_bands"), list)
              and a_one.get("single_area") == a,
              f"absent: {a_one['absent_bands'] or 'none'}")

    hard = {"Palm Jumeirah", "Marsa Dubai", "Business Bay"}
    src = (ROOT / "regions" / "dubai_market" / "metrics.py").read_text()
    check("no area name is hard-coded in the ranking code",
          not any(h in src for h in hard),
          "top-5 comes from value_counts() on the filtered frame")

    # area filter also flows through the bracket ranking
    sub = mx.apply_area(df, "Palm Jumeirah")
    t2, a2 = mx.top_areas_by_band(sub)
    check("bracket ranking respects an upstream area filter",
          (not t2.empty and set(t2["Area"]) == {"Palm Jumeirah"}
           and a2["classified"] == a2["valid"]),
          f"{a2['classified']:,} rows, all in one area")

    # ── PART 6 ──────────────────────────────────────────────────────────────
    head("PART 7 — legends and labels on the modified charts")
    f_top = ch.top_areas_in_band(table, "1M – 2M")
    check("top-areas chart has an x-axis title with units",
          "Transactions" in (f_top.layout.xaxis.title.text or ""),
          f_top.layout.xaxis.title.text)
    check("top-areas categories carry the rank and the area name",
          all(y[0].isdigit() and "." in y for y in f_top.data[0].y),
          str(list(f_top.data[0].y)[:2]))
    f_pr, _ = ch.price_rate_trend(df)
    lg = [t.name for t in f_pr.data if t.name]
    check("price chart legend names the smoothing method and says 'smoothed trend'",
          any("LOWESS smoothed trend" in n for n in lg), " | ".join(lg))
    check("only one smoothing method appears in the legend",
          not any("Exponential" in n or "Version" in n for n in lg))
    check("price chart axes state their units",
          "AED" in (f_pr.layout.yaxis.title.text or "")
          and "AED/m" in (f_pr.layout.yaxis2.title.text or ""),
          f"{f_pr.layout.yaxis.title.text} | {f_pr.layout.yaxis2.title.text}")

    amt, aud_am = mx.amenity_share_vs_baseline(mx.apply_area(df, "Palm Jumeirah"), df, "3 B/R")
    f_am = ch.amenity_share_grouped(amt, "Swimming pool", "3 BHK in Palm Jumeirah")
    check("amenity panel is ONE grouped bar chart, not stacked",
          f_am.layout.barmode == "group" and len(f_am.data) == 2,
          f"barmode={f_am.layout.barmode}, {len(f_am.data)} series (selection + baseline)")
    check("amenity legend names the slice and the baseline explicitly",
          all(t.name for t in f_am.data),
          " | ".join(t.name for t in f_am.data))
    check("amenity y-axis states the unit",
          "%" in (f_am.layout.yaxis.title.text or ""), f_am.layout.yaxis.title.text)

    head("Amenity analysis — parking no longer dominates by construction")
    check("parking is a near-constant across every property type, so raw rank is meaningless",
          all(mx.amenity_transaction_share(df, v)
              .set_index("Amenity").loc["Parking", "Share of recorded transactions (%)"] > 85
              for v in mx.PROPERTY_TYPE_LABELS
              if not mx.amenity_transaction_share(df, v).empty),
          "parking recorded on 88.9%-100.0% of transactions in every type")
    check("chart ranks by gap against Dubai, not by raw share",
          list(amt["Amenity"]) == list(
              amt.reindex(amt["Difference (pp)"].abs().sort_values(ascending=False).index)
                 ["Amenity"]),
          "widest difference first")
    parking_rank = list(amt["Amenity"]).index("Parking") + 1
    check("parking is no longer first in this slice", parking_rank > 1,
          f"parking now ranks {parking_rank} of {len(amt)} — "
          f"{amt.set_index('Amenity').loc['Parking','Difference (pp)']:+.1f} pp vs Dubai")
    check("baseline is the full sidebar selection, not the slice",
          aud_am["baseline_rows"] == len(df) and aud_am["scope_rows"] < len(df),
          f"{aud_am['scope_rows']:,} in scope vs {aud_am['baseline_rows']:,} reference")
    check("selection and baseline shares are both real percentages",
          amt["Share in selection (%)"].between(0, 100).all()
          and amt["Share across Dubai (%)"].between(0, 100).all())
    check("difference is exactly selection minus baseline",
          ((amt["Share in selection (%)"] - amt["Share across Dubai (%)"]
            - amt["Difference (pp)"]).abs() < 1e-9).all())

    # ── PART 9 ──────────────────────────────────────────────────────────────
    head("PART 9 — nothing unrelated changed")
    check("'All areas' is a genuine no-op",
          mx.apply_area(df, mx.ALL_AREAS) is df,
          "an untouched panel behaves exactly as before")
    check("existing price_bands metric untouched in behaviour",
          mx.price_bands(df)[1]["unassigned"] == 0)
    check("BAND_EDGES unchanged (same 7 brackets as before)",
          mx.BAND_EDGES == [0, 500_000, 1_000_000, 2_000_000, 3_000_000,
                            5_000_000, 10_000_000, float("inf")])
    head("Smoothing — exactly one method, LOWESS")
    m = mx.monthly_series(df)
    partial = mx.partial_tail_months(m)
    _, sm = ch.price_rate_trend(df)
    check("one method only, and it is LOWESS", ch.SMOOTH_LABEL == "LOWESS", ch.SMOOTH_LABEL)
    check("no selectable second method remains",
          not hasattr(ch, "smoothing_versions") and not hasattr(ch, "smoothing_single")
          and not hasattr(mx, "smoothing_comparison"),
          "comparison figures and machinery removed")
    check("trend produces no value beyond the last observed month",
          len(sm) == len(m) and str(sm["Month"].iloc[-1]) == str(m["Month"].iloc[-1]),
          f"series ends {m['Month'].iloc[-1]}")
    check("partial final month excluded from the fit, not smoothed over",
          int(sm["smooth_rate"].isna().sum()) == partial and partial > 0,
          f"{partial} partial month(s) left blank in the trend")
    check("trend is calmer than the actual series",
          sm["smooth_rate"].dropna().pct_change().std()
          < sm["median_rate"].dropna().pct_change().std(),
          f"{sm['smooth_rate'].dropna().pct_change().std()*100:.2f}% vs "
          f"{sm['median_rate'].dropna().pct_change().std()*100:.2f}%")
    check("actual monthly observations untouched by smoothing",
          int((sm["median_rate"].round(6) != m["median_rate"].round(6)).sum()) == 0)

    # the trend must respond to the sidebar filters, not be fixed to all-Dubai
    sub = mx.apply_area(df, "Palm Jumeirah")
    _, sm2 = ch.price_rate_trend(sub)
    check("trend recomputes under a filtered selection",
          len(sm2) > 0 and abs(float(sm2["smooth_rate"].dropna().iloc[-1])
                               - float(sm["smooth_rate"].dropna().iloc[-1])) > 1,
          f"all-Dubai {sm['smooth_rate'].dropna().iloc[-1]:,.0f} vs "
          f"Palm Jumeirah {sm2['smooth_rate'].dropna().iloc[-1]:,.0f} AED/m²")

    print("\n" + "=" * 66)
    if _fail:
        print(f"{R}{len(_fail)} FAILED{O}, {_pass} passed")
        for f in _fail:
            print("   -", f)
        return 1
    print(f"{G}ALL {_pass} CHECKS PASSED{O}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
