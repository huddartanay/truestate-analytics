"""
Build Dubai_Analytics_Chart_Reference_Guide.docx.

Two inputs, both authoritative:

  1. `regions/dubai_market/chart_info.py` — the SAME registry the dashboard's ⓘ
     controls read, so the document can never drift from the application.
  2. The Dubai datasets — every table in the document is computed here, at build
     time, from `data/dubai/*.parquet`. No figure is typed in by hand.

Usage:

    python tools/build_chart_reference_docx.py

Writes the payload to `build/chart_reference_payload.json` and then renders the
document with `tools/build_chart_reference_docx.js` (docx-js).
"""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)
OUT_DOCX = ROOT / "docs" / "Dubai_Analytics_Chart_Reference_Guide.docx"

CLEAN = ROOT / "data" / "dubai" / "latest_combined_data.parquet"
RAW = ROOT / "data" / "dubai" / "transactions.parquet"


# ─────────────────────────────────────────────────────────────────────────────
# MEASURED FACTS — computed here, never typed in
# ─────────────────────────────────────────────────────────────────────────────


def measure() -> dict:
    from regions.dubai_market.data import AMENITIES, COL

    print("  reading cleaned dataset…")
    cln = pd.read_parquet(CLEAN, columns=[
        "year", "month", "actual_worth", "meter_sale_price", "procedure_area",
        "rooms_en", "area_name_en", "reg_type_en", "has_parking", "swimming_pool",
        "balcony", "elevator", "metro", "instance_date",
        # Needed by the off-plan investigation in Appendix C.
        "building_name_en", "project_name_en", "master_project_en",
        "completion_date", "Grade", "Price Tier",
    ])

    print("  reading raw registry…")
    raw = pd.read_parquet(RAW, columns=[
        "trans_group_en", "property_type_en", "property_usage_en", "reg_type_en",
        "has_parking", "actual_worth", "meter_sale_price", "procedure_area",
        "rooms_en", "transaction_id",
    ])
    raw_sales = raw[raw.trans_group_en == "Sales"]
    raw_units = raw_sales[(raw_sales.property_type_en == "Unit")
                          & (raw_sales.property_usage_en == "Residential")]

    out: dict = {}

    # ── Year over year ───────────────────────────────────────────────────────
    t = cln.groupby("year").agg(
        transactions=("actual_worth", "size"),
        median_price=("actual_worth", "median"),
        median_rate=("meter_sale_price", "median"))
    t["volume_yoy"] = t.transactions.pct_change() * 100
    t["price_yoy"] = t.median_price.pct_change() * 100
    t["rate_yoy"] = t.median_rate.pct_change() * 100
    out["yoy"] = [
        {"year": int(y), "transactions": int(r.transactions),
         "median_price": round(float(r.median_price)),
         "median_rate": round(float(r.median_rate)),
         "volume_yoy": None if pd.isna(r.volume_yoy) else round(float(r.volume_yoy), 1),
         "rate_yoy": None if pd.isna(r.rate_yoy) else round(float(r.rate_yoy), 1)}
        for y, r in t.iterrows()
    ]
    years = sorted(int(y) for y in t.index)
    out["yoy_meta"] = {
        "years": [years[0], years[-1]],
        "gaps": [y for y in range(years[0], years[-1] + 1) if y not in years],
        "negative_volume_years": [int(y) for y, r in t.iterrows()
                                  if pd.notna(r.volume_yoy) and r.volume_yoy < 0],
        "negative_rate_years": [int(y) for y, r in t.iterrows()
                                if pd.notna(r.rate_yoy) and r.rate_yoy < 0],
    }

    latest, prev = years[-1], years[-2]
    last_month = int(cln.loc[cln.year == latest, "month"].max())
    cur = cln[cln.year == latest]
    base_ytd = cln[(cln.year == prev) & (cln.month <= last_month)]
    base_full = cln[cln.year == prev]
    out["partial_year"] = {
        "year": latest, "months": last_month,
        "last_date": str(cln.instance_date.max().date()),
        "volume_current": int(len(cur)), "volume_base_ytd": int(len(base_ytd)),
        "volume_base_full": int(len(base_full)),
        "volume_pct_fullyear": round((len(cur) / len(base_full) - 1) * 100, 1),
        "volume_pct_ytd": round((len(cur) / len(base_ytd) - 1) * 100, 1),
        "rate_pct_fullyear": round((cur.meter_sale_price.median()
                                    / base_full.meter_sale_price.median() - 1) * 100, 2),
        "rate_pct_ytd": round((cur.meter_sale_price.median()
                               / base_ytd.meter_sale_price.median() - 1) * 100, 2),
    }

    # ── Monthly series (smoothing justification) ─────────────────────────────
    mm = cln.groupby(cln.instance_date.dt.to_period("M")).agg(
        n=("actual_worth", "size"), med_rate=("meter_sale_price", "median"))
    smooth = mm.med_rate.rolling(3, center=True, min_periods=1).median()
    out["monthly"] = {
        "months": int(len(mm)),
        "min_count": int(mm.n.min()), "min_month": str(mm.n.idxmin()),
        "median_count": int(mm.n.median()),
        "last_month": str(mm.index[-1]), "last_count": int(mm.n.iloc[-1]),
        "prev_count": int(mm.n.iloc[-2]),
        "vol_raw": round(float(mm.med_rate.pct_change().std() * 100), 1),
        "vol_smoothed": round(float(smooth.pct_change().std() * 100), 1),
    }

    # ── Layouts ──────────────────────────────────────────────────────────────
    g = cln.groupby("rooms_en", observed=True)["meter_sale_price"]
    lay = pd.DataFrame({"n": g.size(), "q1": g.quantile(.25), "median": g.median(),
                        "q3": g.quantile(.75)})
    lay["median_size"] = cln.groupby("rooms_en", observed=True)["procedure_area"].median()
    order = ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R", "5 B/R", "6 B/R", "7 B/R", "PENTHOUSE"]
    lay = lay.reindex([o for o in order if o in lay.index])
    out["layouts"] = [
        {"layout": str(i), "n": int(r.n), "q1": round(float(r.q1)),
         "median": round(float(r["median"])), "q3": round(float(r.q3)),
         "median_size": round(float(r.median_size), 1)}
        for i, r in lay.iterrows()
    ]

    # ── Off-plan premium ─────────────────────────────────────────────────────
    med = cln.pivot_table(index="year", columns="reg_type_en",
                          values="meter_sale_price", aggfunc="median")
    cnt = cln.pivot_table(index="year", columns="reg_type_en",
                          values="meter_sale_price", aggfunc="size")
    off, exi = "Off-Plan Properties", "Existing Properties"
    out["offplan"] = [
        {"year": int(y), "offplan": round(float(med.loc[y, off])),
         "existing": round(float(med.loc[y, exi])),
         "n_off": int(cnt.loc[y, off]), "n_exi": int(cnt.loc[y, exi]),
         "premium": round(float(med.loc[y, off] / med.loc[y, exi] - 1) * 100, 1)}
        for y in med.index if pd.notna(med.loc[y, off]) and pd.notna(med.loc[y, exi])
    ]
    out["offplan_meta"] = {
        "years": len(out["offplan"]),
        "positive": sum(1 for r in out["offplan"] if r["premium"] > 0),
        "reg_values_raw": {k: int(v) for k, v in raw.reg_type_en.value_counts().items()},
        "reg_nulls_raw": int(raw.reg_type_en.isna().sum()),
    }

    # ── Why the off-plan premium exists: the control ladder + the stock test ──
    #
    # The single most counter-intuitive number in the dashboard. Computed here
    # with the same function the app uses, so the document cannot disagree.
    from regions.dubai_market import metrics as _mx  # noqa: E402

    ladder = _mx.offplan_control_ladder(cln)
    out["offplan_ladder"] = [
        {"comparison": str(r["Comparison"]), "gap": round(float(r["Gap (%)"]), 1),
         "groups": int(r["Groups"]), "deals": int(r["Deals"])}
        for _, r in ladder.iterrows()
    ]

    per_b = cln.groupby("building_name_en", observed=True)["meter_sale_price"].median()
    cnt_b = (cln.groupby(["building_name_en", "reg_type_en"], observed=True)
                .size().unstack(fill_value=0))
    cnt_b = cnt_b[cnt_b.sum(axis=1) >= 30]
    rate_b = per_b.reindex(cnt_b.index)
    wo = float((rate_b * cnt_b[off]).sum() / cnt_b[off].sum())
    we = float((rate_b * cnt_b[exi]).sum() / cnt_b[exi].sum())
    shared = cnt_b[(cnt_b[off] >= 30) & (cnt_b[exi] >= 30)]
    pooled = _mx.paired_gap(cln, "reg_type_en", off, exi, ["building_name_en"], 30)

    sold = pd.to_datetime(cln["instance_date"], errors="coerce")
    done = pd.to_datetime(cln["completion_date"], errors="coerce")
    yrs = (sold - done).dt.days / 365.25
    timing = {}
    for lbl in (off, exi):
        s = yrs[cln.reg_type_en == lbl].dropna()
        timing[lbl] = {"n": int(len(s)), "median_years": round(float(s.median()), 1),
                       "before_completion_pct": round(float((s < 0).mean() * 100), 1)}

    def mixdiff(col, top=5):
        a = cln.loc[cln.reg_type_en == off, col].value_counts(normalize=True).mul(100)
        b = cln.loc[cln.reg_type_en == exi, col].value_counts(normalize=True).mul(100)
        t = pd.DataFrame({"o": a, "e": b}).fillna(0)
        t["d"] = t["o"] - t["e"]
        t = t.sort_values("d", key=abs, ascending=False).head(top)
        return [{"label": str(i), "offplan": round(float(r.o), 1),
                 "existing": round(float(r.e), 1), "diff": round(float(r.d), 1)}
                for i, r in t.iterrows()]

    out["offplan_why"] = {
        "stock_rate_offplan": round(wo), "stock_rate_existing": round(we),
        "stock_gap_pct": round((wo / we - 1) * 100, 1),
        "buildings_considered": int(len(cnt_b)),
        "buildings_both_sides": int(len(shared)),
        "deals_in_shared": int(shared.sum().sum()),
        "shared_share_pct": round(float(shared.sum().sum()) / len(cln) * 100, 1),
        "pooled_gap": round(float(pooled["gap"]), 1) if pooled else None,
        "pooled_groups": int(pooled["groups"]) if pooled else 0,
        "pooled_deals": int(pooled["deals"]) if pooled else 0,
        "pooled_positive_pct": round(float(pooled["positive_pct"]), 0) if pooled else None,
        "completion_date_pct": round(float(done.notna().mean() * 100), 1),
        "timing": timing,
        "price_tier": mixdiff("Price Tier"),
        "grade": mixdiff("Grade"),
    }

    # ── Amenities: headline, 3-way and 4-way like-for-like ───────────────────
    def lfl(df, col, keys, minc=30):
        gr = df.groupby(keys + [col], observed=True)["meter_sale_price"].agg(["median", "size"]).unstack()
        if ("median", 0) not in gr.columns or ("median", 1) not in gr.columns:
            return None
        c = pd.DataFrame({"m0": gr[("median", 0)], "m1": gr[("median", 1)],
                          "n0": gr[("size", 0)], "n1": gr[("size", 1)]}).dropna()
        c = c[(c.n0 >= minc) & (c.n1 >= minc)]
        if c.empty:
            return None
        wt = c.n0 + c.n1
        dl = (c.m1 - c.m0) / c.m0 * 100
        return {"cells": int(len(c)), "txns": int(wt.sum()),
                "weighted": round(float((dl * wt).sum() / wt.sum()), 1),
                "pos": round(float((dl > 0).mean() * 100))}

    amen = []
    for col, label in AMENITIES.items():
        w, wo = cln[cln[col] == 1], cln[cln[col] == 0]
        a = lfl(cln, col, ["area_name_en", "rooms_en", "year"])
        b = lfl(cln, col, ["area_name_en", "rooms_en", "year", "reg_type_en"])
        amen.append({
            "amenity": label, "column": col,
            "n_with": int(len(w)), "n_without": int(len(wo)),
            "nulls": int(cln[col].isna().sum()),
            "median_with": round(float(w.meter_sale_price.median()), 1),
            "median_without": round(float(wo.meter_sale_price.median()), 1),
            "headline": round(float(w.meter_sale_price.median()
                                    / wo.meter_sale_price.median() - 1) * 100, 1),
            "lfl3": None if not a else a["weighted"],
            "lfl4": None if not b else b["weighted"],
            "cells4": None if not b else b["cells"],
            "txns4": None if not b else b["txns"],
            "pos4": None if not b else b["pos"],
            "in_raw": col in raw.columns,
        })
    out["amenities"] = amen

    # Recording completeness — the mechanism behind the negative headlines
    out["recording"] = {
        "balcony_by_reg": (pd.crosstab(cln.reg_type_en, cln.balcony, normalize="index")
                           .mul(100).round(1).to_dict()),
        "median_rate_by_reg": {k: round(float(v)) for k, v in
                               cln.groupby("reg_type_en").meter_sale_price.median().items()},
        "balcony_within_reg": [
            {"reg": rt,
             "with": round(float(sub.loc[sub.balcony == 1, "meter_sale_price"].median())),
             "without": round(float(sub.loc[sub.balcony == 0, "meter_sale_price"].median())),
             "n_with": int((sub.balcony == 1).sum()), "n_without": int((sub.balcony == 0).sum()),
             "diff": round(float(sub.loc[sub.balcony == 1, "meter_sale_price"].median()
                                 / sub.loc[sub.balcony == 0, "meter_sale_price"].median() - 1) * 100, 1)}
            for rt, sub in cln.groupby("reg_type_en", observed=True)
        ],
    }

    # ── Parking on the raw registry ──────────────────────────────────────────
    pt = pd.crosstab(raw_sales.property_type_en, raw_sales.has_parking)
    uw = raw_units[raw_units.has_parking == 1]
    uwo = raw_units[raw_units.has_parking == 0]
    out["parking_raw"] = {
        "sales_rows": int(len(raw_sales)),
        "unit_rows": int(len(raw_units)),
        "by_property_type": {str(k): {str(c): int(v) for c, v in row.items()}
                             for k, row in pt.iterrows()},
        "unit_with": int(len(uw)), "unit_without": int(len(uwo)),
        "unit_median_with": round(float(uw.meter_sale_price.median()), 1),
        "unit_median_without": round(float(uwo.meter_sale_price.median()), 1),
        "unit_gap": round(float(uw.meter_sale_price.median()
                                / uwo.meter_sale_price.median() - 1) * 100, 1),
        "size_with": round(float(uw.procedure_area.median()), 1),
        "size_without": round(float(uwo.procedure_area.median()), 1),
    }
    # composition of the no-parking cohort in the cleaned data
    cw, cwo = cln[cln.has_parking == 1], cln[cln.has_parking == 0]
    out["parking_clean"] = {
        "n_with": int(len(cw)), "n_without": int(len(cwo)),
        "studio_share_with": round(float((cw.rooms_en == "Studio").mean() * 100), 1),
        "studio_share_without": round(float((cwo.rooms_en == "Studio").mean() * 100), 1),
        "existing_share_with": round(float((cw.reg_type_en == "Existing Properties").mean() * 100), 1),
        "existing_share_without": round(float((cwo.reg_type_en == "Existing Properties").mean() * 100), 1),
        "top_area_without": str(cwo.area_name_en.value_counts().index[0]),
        "top_area_without_share": round(float(cwo.area_name_en.value_counts(normalize=True).iloc[0] * 100), 1),
    }

    # ── Price bands ──────────────────────────────────────────────────────────
    edges = [0, 500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000, float("inf")]
    labels = ["< 500K", "500K – 1M", "1M – 2M", "2M – 3M", "3M – 5M", "5M – 10M", "> 10M"]

    def band_table(frame, col="actual_worth"):
        b = pd.cut(frame[col], bins=edges, labels=labels, right=False)
        t = b.value_counts().reindex(labels).fillna(0).astype(int)
        return [{"band": l, "n": int(t[l]), "share": round(float(t[l] / len(frame) * 100), 1)}
                for l in labels], int(t.sum()), int(len(frame))

    bands_clean, a1, t1 = band_table(cln)
    bands_rawunit, a2, t2 = band_table(raw_units)
    bands_rawall, a3, t3 = band_table(raw_sales)
    out["bands"] = {
        "clean": bands_clean, "raw_unit": bands_rawunit, "raw_all": bands_rawall,
        "coverage": {"clean": [a1, t1], "raw_unit": [a2, t2], "raw_all": [a3, t3]},
        "validity": {
            "raw_sales_rows": int(len(raw_sales)),
            "raw_null_price": int(raw_sales.actual_worth.isna().sum()),
            "raw_zero_or_negative": int((raw_sales.actual_worth <= 0).sum()),
            "raw_below_1000": int((raw_sales.actual_worth < 1000).sum()),
            "raw_duplicate_ids": int(raw_sales.transaction_id.duplicated().sum()),
            "clean_min": round(float(cln.actual_worth.min())),
            "clean_max": round(float(cln.actual_worth.max())),
            # Bands are left-closed (right=False), so the top band is >= 10M. Use the
            # same test here or the audit line contradicts the table above it.
            "clean_above_10m": int((cln.actual_worth >= 10_000_000).sum()),
        },
    }

    # ── Dataset headline ─────────────────────────────────────────────────────
    prov = json.loads((ROOT / "data" / "dubai" / "provenance.json").read_text())
    out["provenance"] = prov
    return out


# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    from regions.dubai_market import chart_info as ci

    print("Building chart reference guide…")
    facts = measure()

    charts = []
    for c in ci.CHARTS:
        charts.append({
            "key": c.key, "title": c.title, "section": c.section, "icon": c.icon,
            "subtitle": c.subtitle, "what": c.what, "why": c.why,
            "source_label": c.source_label, "source_file": c.source_file,
            "source_desc": c.source_desc, "columns": c.columns,
            "preparation": c.preparation, "calculation": c.calculation,
            "x_axis": c.x_axis, "y_axis": c.y_axis, "y2_axis": c.y2_axis,
            "legend": c.legend, "filters": c.filters,
            "how_to_read": c.how_to_read, "tells_us": c.tells_us,
            "does_not_tell": c.does_not_tell, "limitations": c.limitations,
            "validation": c.validation, "client_explanation": c.client_explanation,
            # Plain-English layer — the same words the ⓘ shows on screen.
            "one_liner": c.one_liner, "steps": c.steps,
            "terms": [(t.capitalize(), ci.GLOSSARY[t.lower()])
                      for t in c.terms if t.lower() in ci.GLOSSARY],
        })

    payload = {"charts": charts, "sections": ci.SECTIONS, "facts": facts,
               "glossary": sorted((k.capitalize(), v) for k, v in ci.GLOSSARY.items()),
               "generated_from": "regions/dubai_market/chart_info.py"}

    payload_path = BUILD / "chart_reference_payload.json"
    payload_path.write_text(json.dumps(payload, indent=1))
    print(f"  payload: {payload_path}  ({payload_path.stat().st_size/1024:.0f} KB, "
          f"{len(charts)} charts)")

    script = ROOT / "tools" / "build_chart_reference_docx.js"
    subprocess.run(["node", str(script), str(payload_path), str(OUT_DOCX)],
                   check=True, cwd=str(ROOT))
    print(f"  document: {OUT_DOCX}")


if __name__ == "__main__":
    main()
