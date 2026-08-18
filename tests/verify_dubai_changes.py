"""
Independent verification of the six reworked Dubai analyses.

Every figure below is recomputed from `data/dubai/latest_combined_data.parquet`
(and, where the claim is about the registry, from `data/dubai/transactions.parquet`)
with plain pandas, then compared against what `regions/dubai_market/metrics.py`
and `regions/dubai_market/charts.py` actually produce.

    python tests/verify_dubai_changes.py

This is the evidence behind the change report: the dashboard is not trusted to
check itself, and no figure in the reference guide is typed in by hand.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import warnings
from pathlib import Path

import pandas as pd

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from regions.dubai_market import charts, metrics  # noqa: E402
from regions.dubai_market.data import load_market  # noqa: E402

RAW = ROOT / "data" / "dubai" / "transactions.parquet"
CLEANED_PATH = ROOT / "data" / "dubai" / "latest_combined_data.parquet"

GREEN, RED, DIM, OFF = "\033[1;32m", "\033[1;31m", "\033[2m", "\033[0m"
_results: list[bool] = []


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * max(1, 64 - len(title)))


def check(name: str, expected, got, tol: float = 0.0) -> None:
    if isinstance(expected, bool) or isinstance(got, bool):
        ok = bool(expected) == bool(got)
    elif isinstance(expected, (int, float)) and isinstance(got, (int, float)):
        ok = abs(float(expected) - float(got)) <= tol
    else:
        ok = str(expected) == str(got)
    _results.append(ok)
    tag = f"{GREEN}PASS{OFF}" if ok else f"{RED}FAIL{OFF}"
    print(f"  [{tag}] {name:<46} expected={expected}  got={got}")


def note(text: str) -> None:
    print(f"         {DIM}{text}{OFF}")


# ═══════════════════════════════════════════════════════════════════════════
df = load_market()
raw = pd.read_parquet(RAW, columns=["trans_group_en", "property_type_en", "actual_worth",
                                    "has_parking", "reg_type_en", "transaction_id",
                                    "procedure_area"])
raw_sales = raw[raw.trans_group_en == "Sales"]
raw_units = raw_sales[raw_sales.property_type_en == "Unit"]

print(f"\nCleaned dataset: {len(df):,} rows   ·   Raw registry: {len(raw):,} rows")

# ── 1. Year-over-year ───────────────────────────────────────────────────────
section("1. Year-over-year growth compares with the PREVIOUS year")

ref = (df.groupby("year")
         .agg(n=("actual_worth", "size"), rate=("meter_sale_price", "median"))
         .sort_index())
ref["vol_yoy"] = ref["n"].pct_change() * 100
ref["rate_yoy"] = ref["rate"].pct_change() * 100

got = metrics.yoy_table(df).set_index("Year")
for y in (2011, 2015, 2018, 2020, 2024, 2026):
    check(f"{y} volume vs prior year (%)",
          round(float(ref.loc[y, "vol_yoy"]), 3),
          round(float(got.loc[y, "Volume YoY (%)"]), 3), tol=0.001)
    check(f"{y} rate vs prior year (%)",
          round(float(ref.loc[y, "rate_yoy"]), 3),
          round(float(got.loc[y, "Rate YoY (%)"]), 3), tol=0.001)

# The defining property: growth[y] = n[y]/n[y-1] - 1, never n[y]/n[first] - 1.
# The second year is the same under both definitions, so the test starts at the third.
fixed_baseline = (ref["n"] / ref["n"].iloc[0] - 1) * 100
differs = int((fixed_baseline.iloc[2:].round(3) != ref["vol_yoy"].iloc[2:].round(3)).sum())
check("chained, not fixed-baseline (years that differ)", len(ref) - 2, differs)
check("first year has no growth figure", True, bool(pd.isna(got["Volume YoY (%)"].iloc[0])))

val = metrics.yoy_validation(df)
check("gaps in the year sequence", 0, len(val["gaps"]))
last = int(ref.index.max())
last_month = int(df.loc[df.year == last, "month"].max())
check(f"{last} flagged as a partial year", True, bool(val["partial"]))
check(f"{last} months of data present", last_month, int(val["months_available"]))

cur = df[df.year == last]
base = df[(df.year == last - 1) & (df.month <= last_month)]
lfl_vol = (len(cur) / len(base) - 1) * 100
lfl_rate = (cur.meter_sale_price.median() / base.meter_sale_price.median() - 1) * 100
check("like-for-like volume, same months (%)", round(lfl_vol, 3),
      round(float(val["ytd_volume_pct"]), 3), tol=0.001)
check("like-for-like rate, same months (%)", round(lfl_rate, 3),
      round(float(val["ytd_rate_pct"]), 3), tol=0.001)
note(f"the full-year bar reads {ref.loc[last, 'vol_yoy']:+.1f}%; like-for-like is "
     f"{lfl_vol:+.1f}% volume and {lfl_rate:+.2f}% rate")

neg = [int(y) for y in ref.index[1:] if ref.loc[y, "vol_yoy"] < 0]
check("negative years retained, not deleted", neg, [int(y) for y in got.index
                                                    if pd.notna(got.loc[y, "Volume YoY (%)"])
                                                    and got.loc[y, "Volume YoY (%)"] < 0])

# ── 2. Rate per m² by layout ────────────────────────────────────────────────
section("2. Rate per m² by layout: one panel per layout, real quartiles")

fig, stats, excluded = charts.rate_by_layout(df)
boxes = [t for t in fig.data if t.type == "box"]
check("one box trace per retained layout", len(stats), len(boxes))
check("each box at its own x position", len(boxes), len({tuple(t.x) for t in boxes}))

for layout in ("Studio", "1 B/R", "2 B/R", "4 B/R"):
    # The rate column is float32 on load, so allow a cent of drift, not zero.
    sub = df.loc[df.rooms_en == layout, "meter_sale_price"].dropna()
    check(f"{layout} median (AED/m²)", round(float(sub.median()), 2),
          round(float(stats.loc[layout, "med"]), 2), tol=0.05)
    check(f"{layout} 25th percentile", round(float(sub.quantile(0.25)), 2),
          round(float(stats.loc[layout, "q1"]), 2), tol=0.05)
    check(f"{layout} transactions", int(len(sub)), int(stats.loc[layout, "n"]))

kept_n = int(stats["n"].sum())
dropped_n = int(excluded["Transactions"].sum()) if len(excluded) else 0
check("no layout silently dropped", int(df.rooms_en.notna().sum()), kept_n + dropped_n)
note(f"{len(excluded)} layout(s) under the {100}-deal threshold are listed in a table, not deleted")

ladder = ["Studio", "1 B/R", "2 B/R", "3 B/R", "4 B/R"]
med = [round(float(df.loc[df.rooms_en == r, "meter_sale_price"].median()), 1) for r in ladder]
check("median rate RISES with layout size", med, sorted(med))
note(f"{med} — so the removed caption 'smaller units cost more per m²' was false")

# ── 3. Smoothing ────────────────────────────────────────────────────────────
section("3. Smoothing is a centred LOWESS fit of the real series")

m = metrics.monthly_series(df)
partial = metrics.partial_tail_months(m)
manual = metrics.lowess_trend(m["median_rate"], exclude_tail=partial)
_, smoothed = charts.price_rate_trend(df)
check("smoothed rate equals the LOWESS fit", 0,
      int((smoothed["smooth_rate"].round(6).fillna(-1)
           != manual.round(6).fillna(-1)).sum()))
check("only one smoothing method is exposed", "LOWESS", charts.SMOOTH_LABEL)
# Exponential smoothing DOES still exist in metrics.py — it powers the method
# comparison in the Experimental Analysis environment. What must be true is
# that the LIVE Dubai price chart offers no choice of method: the dashboard
# never renders a second trend, and price_rate_trend fits LOWESS only.
_charts_src = (ROOT / "regions/dubai_market/charts.py").read_text()
_dash_src = (ROOT / "regions/dubai_market/dashboard.py").read_text()
_trend_fn = _charts_src[_charts_src.index("def price_rate_trend("):
                        _charts_src.index("def yoy_growth(")]
check("the live price chart fits LOWESS and nothing else", True,
      "lowess_trend" in _trend_fn and "Exponential" not in _trend_fn)
check("the Dubai dashboard offers no smoothing-method choice", 0,
      _dash_src.count("ExponentialSmoothing") + _dash_src.count("smoothing_experiment"))
check("the partial final month is excluded from the fit", partial,
      int(smoothed["smooth_rate"].isna().sum()))
check("the trend never extends past the last observed month",
      str(m["Month"].iloc[-1]), str(smoothed["Month"].iloc[-1]))
check("no month removed by smoothing", len(m), len(smoothed))
check("actual monthly medians left untouched", 0,
      int((smoothed["median_rate"].round(6) != m["median_rate"].round(6)).sum()))

# The dashboard and the reference guide both quote the standard deviation of
# month-on-month change, so that is the statistic checked here.
raw_sd = float(m["median_rate"].pct_change().std() * 100)
sm_sd = float(smoothed["smooth_rate"].dropna().pct_change().std() * 100)
check("quoted variation before smoothing (sd, %)", 7.6, round(raw_sd, 1), tol=0.05)
check("quoted variation after smoothing (sd, %)", 1.4, round(sm_sd, 1), tol=0.05)
check("smoothing reduces month-on-month variation", True, sm_sd < raw_sd)
note(f"sd of month-on-month change: {raw_sd:.2f}% actual → {sm_sd:.2f}% smoothed; "
     f"median |change| {m['median_rate'].pct_change().abs().median() * 100:.2f}% → "
     f"{smoothed['smooth_rate'].pct_change().abs().median() * 100:.2f}%")

check("thinnest month is still a large sample", True, int(m["Transactions"].min()) >= 500)
note(f"smallest month = {int(m['Transactions'].min()):,} deals, median month = "
     f"{int(m['Transactions'].median()):,} — the jaggedness is real, not thin data")

# ── 4. Off-plan vs existing ─────────────────────────────────────────────────
section("4. Off-plan classification comes from the data")

check("registration values in the raw registry", 2, int(raw_sales.reg_type_en.nunique()))
check("missing registration values (raw sales)", 0, int(raw_sales.reg_type_en.isna().sum()))
check("missing registration values (cleaned)", 0, int(df.reg_type_en.isna().sum()))
check("no third category invented", ["Existing Properties", "Off-Plan Properties"],
      sorted(str(v) for v in df.reg_type_en.unique()))

prem = metrics.offplan_premium_table(df).set_index("Year")
for y in (2011, 2019, 2022, 2026):
    sub = df[df.year == y]
    o = float(sub.loc[sub.reg_type_en == "Off-Plan Properties", "meter_sale_price"].median())
    e = float(sub.loc[sub.reg_type_en == "Existing Properties", "meter_sale_price"].median())
    check(f"{y} premium (%)", round((o / e - 1) * 100, 2),
          round(float(prem.loc[y, "Premium (%)"]), 2), tol=0.01)
check("years reported", int(len(prem)), int(prem["Premium (%)"].notna().sum()))
check("years where off-plan is dearer", len(prem), int((prem["Premium (%)"] > 0).sum()))
note("stated as a premium of one product over another — no causal claim about timing")

# ── 4b. Why off-plan looks dearer ───────────────────────────────────────────
section("4b. The off-plan premium is about the building, not about being unbuilt")

OFFPLAN, EXISTING = "Off-Plan Properties", "Existing Properties"
oladder = metrics.offplan_control_ladder(df)
check("ladder has every control level", len(metrics.OFFPLAN_LEVELS), len(oladder))

o_all = df[df.reg_type_en == OFFPLAN]["meter_sale_price"]
e_all = df[df.reg_type_en == EXISTING]["meter_sale_price"]
check("top rung is the straight comparison (%)",
      round((float(o_all.median()) / float(e_all.median()) - 1) * 100, 2),
      round(float(oladder.iloc[0]["Gap (%)"]), 2), tol=0.01)

# The bottom rung recomputed by hand: same building, same year, 30 each side.
g = (df.groupby(["building_name_en", "year", "reg_type_en"], observed=True)["meter_sale_price"]
       .agg(["median", "size"]).unstack(level=-1))
cells = pd.DataFrame({"ro": g[("median", OFFPLAN)], "re": g[("median", EXISTING)],
                      "no": g[("size", OFFPLAN)], "ne": g[("size", EXISTING)]}).dropna()
cells = cells[(cells["no"] >= 30) & (cells["ne"] >= 30)]
w = cells["no"] + cells["ne"]
manual = float((((cells["ro"] - cells["re"]) / cells["re"] * 100) * w).sum() / w.sum())
check("same-building rung recomputed by hand (%)", round(manual, 2),
      round(float(oladder.iloc[-1]["Gap (%)"]), 2), tol=0.01)
check("same-building rung sample", int(len(cells)), int(oladder.iloc[-1]["Groups"]))

check("the premium survives at area level", True, float(oladder.iloc[2]["Gap (%)"]) > 20)
check("the premium is gone at building level", True,
      abs(float(oladder.iloc[-1]["Gap (%)"])) < 10)
note(" → ".join(f"{r['Gap (%)']:+.1f}%" for _, r in oladder.iterrows())
     + "   (raw → same building)")

ocomp = metrics.offplan_composition(df)
# The decisive number: value each building at its own median rate, then ask what
# the average building is worth on each side.
per_b = df.groupby("building_name_en", observed=True)["meter_sale_price"].median()
cnt = df.groupby(["building_name_en", "reg_type_en"], observed=True).size().unstack(fill_value=0)
cnt = cnt[cnt.sum(axis=1) >= 30]
r_ = per_b.reindex(cnt.index)
wo = float((r_ * cnt[OFFPLAN]).sum() / cnt[OFFPLAN].sum())
we = float((r_ * cnt[EXISTING]).sum() / cnt[EXISTING].sum())
check("stock rate, off-plan side (AED/m²)", round(wo, 1),
      round(float(ocomp["stock_rate_offplan"]), 1), tol=0.05)
check("stock rate, existing side (AED/m²)", round(we, 1),
      round(float(ocomp["stock_rate_existing"]), 1), tol=0.05)
check("the stock gap explains the headline", True,
      abs(float(ocomp["stock_gap_pct"]) - float(ocomp["headline_pct"])) < 8)
note(f"headline {ocomp['headline_pct']:+.1f}% vs stock-quality gap "
     f"{ocomp['stock_gap_pct']:+.1f}% — the buildings, not the timing")

pooled = ocomp["same_building_pooled"]
check("pooled same-building check agrees in direction", True,
      pooled["gap"] < 0 and float(oladder.iloc[-1]["Gap (%)"]) < 0)
note(f"pooled across years: {pooled['gap']:+.1f}% over {pooled['groups']:,} buildings / "
     f"{pooled['deals']:,} deals; off-plan dearer in only {pooled['positive_pct']:.0f}% of them")

# The label itself: does off-plan actually mean "before completion"?
prov = json.loads((ROOT / "data" / "dubai" / "provenance.json").read_text())
rt = prov.get("registration_type", {})
tim = rt.get("timing", {})
check("off-plan sales happen before completion (%)", True,
      float(tim[OFFPLAN]["sold_before_completion_pct"]) > 80)
check("existing sales happen after completion", True,
      float(tim[EXISTING]["median_years_vs_completion"]) > 0)
note(f"off-plan: {tim[OFFPLAN]['sold_before_completion_pct']:.0f}% sold before completion, "
     f"median {tim[OFFPLAN]['median_years_vs_completion']:+.1f} yrs; "
     f"existing: median {tim[EXISTING]['median_years_vs_completion']:+.1f} yrs")

# The shared implementation must give the amenity path identical answers.
check("paired_gap reproduces the amenity like-for-like figure",
      round(float(metrics._like_for_like_one(df, "has_parking", metrics.LFL_KEYS, 30)["gap"]), 6),
      round(float(metrics.paired_gap(df, "has_parking", 1, 0, metrics.LFL_KEYS, 30)["gap"]), 6),
      tol=1e-6)

# ── 5. Amenities ────────────────────────────────────────────────────────────
section("5. Amenity effects collapse when comparing like with like")

head = {r["label"]: r for r in metrics.amenity_effects(df)}
lfl = metrics.amenity_effects_like_for_like(df).set_index("Amenity")

for col, amenity in metrics.AMENITIES.items():
    if col not in df.columns:
        continue
    with_ = float(df.loc[df[col] == 1, "meter_sale_price"].median())
    without = float(df.loc[df[col] == 0, "meter_sale_price"].median())
    check(f"{amenity}: headline gap (%)", round((with_ / without - 1) * 100, 2),
          round(float(head[amenity]["rate_delta_pct"]), 2), tol=0.01)

    # Independent like-for-like: size-weighted mean of per-cell differences,
    # same keys and same 30-deal floor as the dashboard.
    keys = metrics.LFL_KEYS
    g = (df.groupby(keys + [col], observed=True)["meter_sale_price"]
           .agg(["median", "size"]).unstack(level=-1))
    cells = pd.DataFrame({"r0": g[("median", 0)], "r1": g[("median", 1)],
                          "n0": g[("size", 0)], "n1": g[("size", 1)]}).dropna()
    cells = cells[(cells.n0 >= 30) & (cells.n1 >= 30)]
    w = cells.n0 + cells.n1
    manual_lfl = float((((cells.r1 - cells.r0) / cells.r0 * 100) * w).sum() / w.sum())
    check(f"{amenity}: like-for-like gap (%)", round(manual_lfl, 2),
          round(float(lfl.loc[amenity, "Median rate difference (%)"]), 2), tol=0.01)
    check(f"{amenity}: comparable groups", int(len(cells)),
          int(lfl.loc[amenity, "Groups"]))
    note(f"{amenity}: {head[amenity]['rate_delta_pct']:+.1f}% headline → "
         f"{lfl.loc[amenity, 'Median rate difference (%)']:+.1f}% like-for-like across "
         f"{int(lfl.loc[amenity, 'Groups']):,} groups / {int(lfl.loc[amenity, 'Deals']):,} deals")

# ── 5b. The control ladder ──────────────────────────────────────────────────
section("5b. The control ladder melts the headline, and each rung is real")

_moves: list[tuple[str, float, float]] = []
for col, amenity in metrics.AMENITIES.items():
    if col not in df.columns:
        continue
    ladder = metrics.amenity_control_ladder(df, col)
    check(f"{amenity}: ladder has every control level", len(metrics.CONTROL_LEVELS),
          len(ladder))
    check(f"{amenity}: top rung equals the headline (%)",
          round(float(head[amenity]["rate_delta_pct"]), 2),
          round(float(ladder.iloc[0]["Gap (%)"]), 2), tol=0.01)
    check(f"{amenity}: bottom rung equals the like-for-like figure (%)",
          round(float(lfl.loc[amenity, "Median rate difference (%)"]), 2),
          round(float(ladder.iloc[-1]["Gap (%)"]), 2), tol=0.01)
    _moves.append((amenity, float(ladder.iloc[0]["Gap (%)"]),
                   float(ladder.iloc[-1]["Gap (%)"])))

# Controlling for the property mix does not have to change every amenity — the
# claim is that it changes MOST of them, which is what makes the raw chart unsafe
# to quote. The exceptions are worth naming rather than hiding.
moved = [m for m in _moves if abs(m[2] - m[1]) > 5.0]
check("amenities materially changed by controlling for the mix", True, len(moved) >= 3)
for amenity, raw_g, fair_g in _moves:
    note(f"{amenity}: {raw_g:+.1f}% raw → {fair_g:+.1f}% fair "
         f"({fair_g - raw_g:+.1f} pts)"
         + ("" if abs(fair_g - raw_g) > 5.0 else "   ← barely moves; the raw number "
                                                 "was already about right here"))

# One rung recomputed by hand, end to end.
manual_keys = [metrics.COL["area"], metrics.COL["rooms"]]
g = (df.groupby(manual_keys + ["has_parking"], observed=True)["meter_sale_price"]
       .agg(["median", "size"]).unstack(level=-1))
cells = pd.DataFrame({"r0": g[("median", 0)], "r1": g[("median", 1)],
                      "n0": g[("size", 0)], "n1": g[("size", 1)]}).dropna()
cells = cells[(cells.n0 >= 30) & (cells.n1 >= 30)]
w = cells.n0 + cells.n1
manual_rung = float((((cells.r1 - cells.r0) / cells.r0 * 100) * w).sum() / w.sum())
pl = metrics.amenity_control_ladder(df, "has_parking")
check("Parking: 'same area and layout' rung recomputed by hand (%)",
      round(manual_rung, 2), round(float(pl.iloc[2]["Gap (%)"]), 2), tol=0.01)
check("Parking: the raw magnitude collapses under the fair comparison",
      True, abs(float(pl.iloc[-1]["Gap (%)"])) < 0.2 * abs(float(pl.iloc[0]["Gap (%)"])))
note(" → ".join(f"{r['Gap (%)']:+.1f}%" for _, r in pl.iterrows())
     + "  (raw → fair, parking)")

reason = metrics.amenity_plain_reason(df, "has_parking")
check("plain-language reason quotes the same headline",
      round(float(head["Parking"]["rate_delta_pct"]), 2), round(reason["headline"], 2), tol=0.01)
check("plain-language reason quotes the same fair figure",
      round(float(lfl.loc["Parking", "Median rate difference (%)"]), 2),
      round(reason["fair"], 2), tol=0.01)
check("plain-language sizes match the data (m², with)",
      round(float(df.loc[df.has_parking == 1, "procedure_area"].median()), 1),
      round(reason["size_with"], 1), tol=0.05)
check("passing a precomputed fair figure changes nothing",
      round(reason["fair"], 4),
      round(metrics.amenity_plain_reason(
          df, "has_parking",
          fair={"gap": reason["fair"], "groups": 0, "deals": 0, "positive_pct": 0})["fair"], 4),
      tol=0.0001)

# The balcony sign flip is the whole argument — verify it directly.
comp = metrics.amenity_composition(df, "balcony")
wr = comp["within_reg"].set_index("Registration type")["Difference (%)"]
within = {k: float(v) for k, v in wr.items()}
for reg in ("Existing Properties", "Off-Plan Properties"):
    sub = df[df.reg_type_en == reg]
    manual = (sub.loc[sub.balcony == 1, "meter_sale_price"].median()
              / sub.loc[sub.balcony == 0, "meter_sale_price"].median() - 1) * 100
    check(f"balcony gap within {reg} (%)", round(float(manual), 2),
          round(within[reg], 2), tol=0.01)
check("balcony gap POSITIVE within existing property", True,
      within["Existing Properties"] > 0)
check("balcony gap NEGATIVE within off-plan property", True,
      within["Off-Plan Properties"] < 0)
check("balcony headline NEGATIVE overall", True, head["Balcony"]["rate_delta_pct"] < 0)
note(f"existing {within['Existing Properties']:+.1f}% · off-plan "
     f"{within['Off-Plan Properties']:+.1f}% · headline "
     f"{head['Balcony']['rate_delta_pct']:+.1f}% — a reversal inside every subgroup is a "
     f"composition effect, not a property of balconies")

# Parking is the only flag that exists in the raw registry — verify that claim.
check("has_parking present in the raw registry", True, "has_parking" in raw.columns)
non_unit = raw[raw.property_type_en != "Unit"]
check("parking flag is zero on every non-unit row", 0, int(non_unit.has_parking.sum()))
note("so on the raw file the headline compares apartments against land and villas")

pk_with = float(raw_units.loc[raw_units.has_parking == 1, "actual_worth"].div(
    raw_units.loc[raw_units.has_parking == 1, "procedure_area"]).median())
pk_without = float(raw_units.loc[raw_units.has_parking == 0, "actual_worth"].div(
    raw_units.loc[raw_units.has_parking == 0, "procedure_area"]).median())
check("parking gap survives on the raw registry too", True, pk_with > pk_without)
note(f"raw residential units: {pk_with:,.0f} with vs {pk_without:,.0f} without (AED/m²) — "
     f"direction confirmed independently of the cleaned file")

# ── 6. Price bands ──────────────────────────────────────────────────────────
section("6. Price bands are exhaustive and mutually exclusive")

for label, frame in (("cleaned dataset", df),
                     ("raw unit sales", raw_units),
                     ("raw, all sales", raw_sales)):
    cut = pd.cut(frame["actual_worth"], bins=metrics.BAND_EDGES,
                 labels=metrics.BAND_LABELS, right=False)
    check(f"{label}: every row lands in exactly one band", len(frame), int(cut.notna().sum()))

table, audit = metrics.price_bands(df)
check("chart total equals dataset row count", len(df), int(table["Transactions"].sum()))
check("unassigned rows", 0, int(audit["unassigned"]))
check("shares sum to 100%", 100.0, round(float(audit["share_sum"]), 2), tol=0.01)
check("duplicate transaction ids (raw sales)", 0, int(raw_sales.transaction_id.duplicated().sum()))
check("null sale prices (raw sales)", 0, int(raw_sales.actual_worth.isna().sum()))
check("zero or negative sale prices (raw sales)", 0, int((raw_sales.actual_worth <= 0).sum()))

top = int((df.actual_worth >= 10_000_000).sum())
check("top band equals a direct '>= 10M' count", top,
      int(table.loc[table["Price band (AED)"] == "> 10M", "Transactions"].iloc[0]))
note(f"the top band reads zero on screen only because the default price slider stops "
     f"near AED 8M — the data holds {top:,} such sales")

# ── 7. Chart documentation ──────────────────────────────────────────────────
section("7. Every chart is documented, in plain English as well as technically")

from regions.dubai_market import chart_info as ci  # noqa: E402

# The Dubai page is rendered by dashboard.py plus the subsection modules it
# delegates to (the Forecast subsection lives in forecast_ui.py). Scanning only
# dashboard.py would report a documented, rendered chart as unused.
_PAGE_MODULES = ("dashboard.py", "forecast_ui.py")
dash_src = "\n".join(
    (ROOT / "regions" / "dubai_market" / name).read_text() for name in _PAGE_MODULES)
used = set(re.findall(r'ci\.header\("([^"]+)"\)', dash_src))

check("registry entries", len(ci.CHARTS), len({c.key for c in ci.CHARTS}))
check("every chart on the page has a registry entry", set(), used - set(ci.CHART_BY_KEY))
check("every registry entry is used on the page", set(), set(ci.CHART_BY_KEY) - used)

for field_name in ("one_liner", "what", "why", "calculation", "validation",
                   "client_explanation"):
    missing = [c.key for c in ci.CHARTS if not getattr(c, field_name)]
    check(f"entries missing `{field_name}`", [], missing)

for field_name in ("steps", "how_to_read", "tells_us", "does_not_tell",
                   "limitations", "columns"):
    missing = [c.key for c in ci.CHARTS if not getattr(c, field_name)]
    check(f"entries with an empty `{field_name}` list", [], missing)

unknown = sorted({t for c in ci.CHARTS for t in c.terms if t.lower() not in ci.GLOSSARY})
check("glossary terms referenced but not defined", [], unknown)
check("every section is represented", set(ci.SECTIONS), {c.section for c in ci.CHARTS})
note(f"{len(ci.CHARTS)} charts · {len(ci.GLOSSARY)} glossary entries · "
     f"{sum(len(c.steps) for c in ci.CHARTS)} plain-English steps")

# ── 8. v1.3 — RAW transaction volume and the incomplete-year rule ────────────
section("8. Transaction volume is counted on RAW data, and 2026 is handled correctly")

from regions.dubai_market.data import load_raw_transaction_counts, raw_coverage  # noqa: E402

counts = counts_v14 = load_raw_transaction_counts()
years = metrics.raw_transaction_years(counts)
partial = metrics.partial_year_growth(counts)
cover = raw_coverage()

# The raw slice must be the residential-unit sales population, counted without cleaning.
raw_full = pd.read_parquet(RAW, columns=["instance_date", "trans_group_en",
                                         "property_type_en", "property_usage_en"])
rd = pd.to_datetime(raw_full["instance_date"], errors="coerce")
raw_full = raw_full.assign(year=rd.dt.year, month=rd.dt.month).dropna(subset=["year"])
res = res_v14 = raw_full[(raw_full.trans_group_en == "Sales")
               & (raw_full.property_type_en == "Unit")
               & (raw_full.property_usage_en == "Residential")]

check("raw residential unit sales total", int(len(res)),
      int(cover["total_residential_unit_sales"]))
check("raw registry total", int(len(raw_full)), int(cover["total_all_transactions"]))

for y in (2011, 2015, 2020, 2025, 2026):
    check(f"{y} transactions counted from RAW", int((res.year == y).sum()),
          int(years.loc[years.year == y, "transactions"].iloc[0]))

# The whole point of using raw: it is larger than the cleaned count in every year.
cleaned_by_year = df.groupby("year").size()
raw_by_year = years.set_index("year")["transactions"]
shortfall = (raw_by_year - cleaned_by_year.reindex(raw_by_year.index)).dropna()
check("raw exceeds cleaned in every year", True, bool((shortfall > 0).all()))
note(f"cleaning removes {int(shortfall.min()):,}–{int(shortfall.max()):,} transactions per "
     f"year — the reason volume is counted on the raw registry")

# Growth is chained across completed years, base year excluded.
complete = years[years["complete"]].reset_index(drop=True)
check("base year carries no growth figure", True, bool(pd.isna(years["yoy_pct"].iloc[0])))
manual = (complete["transactions"] / complete["transactions"].shift() - 1) * 100
check("completed-year growth recomputed by hand", 0,
      int((manual.iloc[1:].round(4) != complete["yoy_pct"].iloc[1:].round(4)).sum()))
check("every completed year 2012 onwards has a growth figure", 0,
      int(complete["yoy_pct"].iloc[1:].isna().sum()))

# The latest year: period identified from the data, never hard-coded.
latest = int(years["year"].max())
months = sorted(int(m) for m in res.loc[res.year == latest, "month"].dropna().unique())
check("latest year detected from the data", latest, int(partial["year"]))
check("latest month detected from the data", max(months), int(partial["last_month"]))
check("months available detected from the data", len(months), int(partial["months_available"]))
check("latest year flagged incomplete", True, not partial["complete"])
note(f"registry covers {partial['period_label']} {latest} — "
     f"{partial['months_available']} of 12 months, nothing hard-coded")

base_n = int(((res.year == latest - 1) & (res.month <= max(months))).sum())
cur_n = int((res.year == latest).sum())
check("like-for-like basis is the same months of the previous year", base_n,
      int(partial["basis_transactions"]))
check("latest-year count", cur_n, int(partial["transactions"]))
check("like-for-like growth recomputed by hand",
      round((cur_n / base_n - 1) * 100, 4), round(float(partial["growth_pct"]), 4), tol=1e-4)

# THE RULE: a percentage is shown only when growth is strictly positive.
strictly_positive = partial["growth_pct"] > 0
check("percentage shown only if strictly positive", strictly_positive,
      partial["display_growth"] is not None)
check("no negative growth figure is ever displayed for the partial year", True,
      partial["display_growth"] is None or partial["display_growth"] > 0)
check("the chart's growth line omits the incomplete year", True,
      bool(pd.isna(years.loc[years.year == latest, "yoy_pct"].iloc[0])))
note(f"{latest} like-for-like is {partial['growth_pct']:+.1f}% → "
     f"{'shown' if partial['display_growth'] is not None else 'suppressed, count only'}")

# The figure actually handed to Plotly must contain no negative point for that year.
fig_raw = charts.raw_transaction_volume(years, partial)
growth_traces = [t for t in fig_raw.data if t.type == "scatter"]
plotted_years = {str(int(x)) for t in growth_traces
                 for x in (list(t.x) if t.x is not None else [])}
check("incomplete year absent from the growth series", partial["display_growth"] is not None,
      str(latest) in plotted_years)

# ── 9. v1.3 — year-by-year summary table ────────────────────────────────────
section("9. The summary table mixes RAW counts with CLEANED rates, correctly")

summary = metrics.yearly_summary(counts, df)
check("first year is the base year", metrics.BASE_YEAR, int(summary["year"].min()))
for y in (2013, 2022, 2025):
    row = summary[summary.year == y].iloc[0]
    check(f"{y} transactions come from RAW", int((res.year == y).sum()), int(row["transactions"]))
    sub = df[df.year == y]["meter_sale_price"]
    check(f"{y} mean rate comes from CLEANED", round(float(sub.mean()), 2),
          round(float(row["mean_rate"]), 2), tol=0.01)
    check(f"{y} median rate comes from CLEANED", round(float(sub.median()), 2),
          round(float(row["median_rate"]), 2), tol=0.01)
check("the two sources are reported separately", True,
      bool((summary["transactions"] > summary["priced_rows"]).all()))

# ── 10. v1.4 — amenity ASSOCIATION with recorded transactions ───────────────
section("10. Amenity shares are shares of recorded transactions, not probabilities")

import pyarrow.parquet as pq  # noqa: E402

raw_cols = pq.ParquetFile(RAW).schema_arrow.names
cln_cols = pq.ParquetFile(CLEANED_PATH).schema_arrow.names
outcome_kw = ("purchase", "buy", "bought", "outcome", "lead", "enquir", "inquir",
              "visit", "prospect", "convert", "target", "churn")
outcome_cols = sorted({c for c in list(raw_cols) + list(cln_cols)
                       if any(k in c.lower() for k in outcome_kw)})
check("no purchase / non-purchase outcome column exists", [], outcome_cols)
note("every row in both files is a completed, recorded transaction — so no purchase "
     "probability can be estimated, and the dashboard does not claim one")

for ptype, label in (("1 B/R", "1 BHK"), ("Studio", "Studio")):
    share = metrics.amenity_transaction_share(df, ptype).set_index("Amenity")
    sub = df[df.rooms_en == ptype]
    for col, amenity in metrics.AMENITIES.items():
        manual = float((sub[col] == 1).mean() * 100)
        check(f"{label} × {amenity}: share recomputed (%)", round(manual, 3),
              round(float(share.loc[amenity, "Share of recorded transactions (%)"]), 3),
              tol=0.001)
    check(f"{label}: with + without equals the group size", int(len(sub)),
          int(share["Transactions with amenity recorded"].iloc[0]
              + share["Transactions without"].iloc[0]))
    check(f"{label}: every share lies between 0 and 100", True,
          bool(share["Share of recorded transactions (%)"].between(0, 100).all()))

across = metrics.amenity_share_by_property_type(df, "has_parking")
for _, r in across.iterrows():
    ptype = metrics.LABEL_TO_PROPERTY_TYPE[r["Property type"]]
    sub = df[df.rooms_en == ptype]
    check(f"{r['Property type']}: parking share across types (%)",
          round(float((sub.has_parking == 1).mean() * 100), 3),
          round(float(r["Share of recorded transactions (%)"]), 3), tol=0.001)
check("thin property types are excluded", True,
      bool((across["Transactions"] >= metrics.MIN_CELL).all()))
note(f"parking is recorded on {across['Share of recorded transactions (%)'].min():.1f}–"
     f"{across['Share of recorded transactions (%)'].max():.1f}% of transactions "
     f"depending on property type")

# ── 10b. v1.4 — volume against price uses the MEAN, by design ───────────────
section("10b. Volume vs price uses RAW volume and the MEAN rate")

vp = metrics.volume_vs_mean_rate(counts_v14, df)
for y in (2013, 2021, 2025):
    sub = df[df.year == y]["meter_sale_price"]
    row = vp[vp.year == y].iloc[0]
    check(f"{y} volume comes from RAW", int((res_v14.year == y).sum()),
          int(row["transactions"]))
    check(f"{y} MEAN rate comes from CLEANED", round(float(sub.mean()), 2),
          round(float(row["mean_rate"]), 2), tol=0.01)
    check(f"{y} mean differs from median (so the choice matters)", True,
          abs(float(row["mean_rate"]) - float(row["median_rate"])) > 1.0)
check("mean sits above median in every year", True,
      bool((vp.dropna(subset=["mean_rate"])["mean_rate"]
            > vp.dropna(subset=["mean_rate"])["median_rate"]).all()))

# ── 11. v1.3 — building height, and the floor-level limitation ──────────────
section("11. Height bands are data-driven, and the floor limitation is real")

raw_floor = pd.read_parquet(CLEANED_PATH, columns=["floor_bin", "floors", "property_id_bld"])
check("floor_bin carries no usable floor level", {"Unknown"},
      set(raw_floor["floor_bin"].dropna().unique()))
per_bld = raw_floor.dropna(subset=["floors", "property_id_bld"]).groupby("property_id_bld")["floors"].nunique()
check("`floors` is constant within a building (so it is building height)", 100.0,
      round(float((per_bld == 1).mean() * 100), 1), tol=0.01)
note("the dataset does not record a unit's own floor — the panel is labelled as building "
     "height, not floor level")

labels, edges = metrics.building_height_bands(df)
# Bands are now FIXED thresholds on round numbers, not quantiles of the
# selection, so a band denotes the same building in every area.
check("band edges are the fixed floor thresholds", [0, 10, 25, 40], edges[:4])
check("four bands produced", 4, len(labels))
check("band labels name their floor range", True,
      all(any(ch.isdigit() for ch in b) for b in labels))
check("edges do not move with the selection", edges,
      metrics.building_height_bands(df[df.area_name_en == "Marsa Dubai"])[1])

frame, audit = metrics.rate_by_building_height(df)
check("no cell below the minimum is plotted", True,
      bool((frame["transactions"] >= audit["min_cell"]).all()))
check("dropped cells are reported, not hidden", True, isinstance(audit["dropped"], list))
check("every band is populated, none is a rump", True,
      all(audit["band_counts"][b] > 1000 for b in labels))
check("zero-floor readings are excluded, not counted as low-rise", True,
      audit["invalid_floor"] == int((df["floors"] == 0).sum()) and audit["invalid_floor"] > 0)

for band in labels[:2]:
    for ptype in ["1 BHK", "Studio"]:
        row = frame[(frame["height_band"].astype(str) == band)
                    & (frame["Property type"] == ptype)]
        if row.empty:
            continue
        lo = edges[labels.index(band)]
        hi = edges[labels.index(band) + 1]
        # Recompute with the SAME rules the metric uses: floors >= 1, and the
        # band interval left-open / right-closed.
        sel = df[(df.rooms_en == metrics.LABEL_TO_PROPERTY_TYPE[ptype])
                 & (df.floors >= 1) & (df.floors > lo) & (df.floors <= hi)]
        val = sel["meter_sale_price"].median()
        check(f"{ptype} in {band}: median recomputed", round(float(val), 1),
              round(float(row["median_rate"].iloc[0]), 1), tol=0.5)

note(f"fixed bands {labels}")
note(f"populations: " + " · ".join(f"{b.split(' (')[0]} {audit['band_counts'][b]:,}"
                                   for b in labels)
     + f"; {audit['invalid_floor']:,} zero-floor rows excluded; "
       f"{len(audit['dropped'])} thin cell(s) named on screen")

# ── 12. v1.3 — the price-distribution chart was reviewed, not replaced ──────
section("12. The price-distribution methodology holds up under review")

sample = df.sample(45_000, random_state=42)
err = []
for y, grp in df.groupby("year"):
    s = sample[sample.year == y]["meter_sale_price"]
    if len(s) < 100:
        continue
    err.append(abs(s.median() / grp["meter_sale_price"].median() - 1) * 100)
check("sampled year medians track the population within 3%", True, max(err) < 3.0)
check("every year keeps a usable sample", True,
      int(sample.groupby("year").size().min()) >= 500)
note(f"worst per-year median error from sampling: {max(err):.2f}% — the existing "
     f"methodology is sound and was kept")

# ═══════════════════════════════════════════════════════════════════════════
passed, total = sum(_results), len(_results)
bar = "═" * 66
colour = GREEN if passed == total else RED
print(f"\n{bar}\n  {colour}{passed}/{total} checks passed{OFF}\n{bar}\n")
sys.exit(0 if passed == total else 1)
