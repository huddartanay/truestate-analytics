"""
The Dubai regional dashboard.

Page structure — deliberately the same shape as the Abu Dhabi dashboard:

    Executive KPIs
    Smart Business Insights
    Market Snapshot
    ────────────── ANALYTICS ──────────────
    Insights · Trends · Geography · Property · Price · Distribution

Everything on the page is computed from `data/dubai/latest_combined_data.parquet`
at render time. No value is copied from Abu Dhabi and none is hard-coded.

Every chart carries an ⓘ control documenting its source, columns, calculation,
interpretation and limitations — see `chart_info.py`, which is also the source
for the company-facing DOCX reference guide.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from platform_core.chart_theme import PLOTLY_CONFIG

from . import chart_info as ci
from . import charts as ch
from . import metrics as mx
from .data import (
    AMENITIES,
    COL,
    DubaiDataError,
    aed,
    apply_filters,
    filter_options,
    load_market,
    load_raw_transaction_counts,
    load_provenance,
)

PC = PLOTLY_CONFIG


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────────────────────


def _sidebar_filters(opts: dict) -> dict:
    """Dubai's own filter stack, rendered under the platform's rail."""
    sb = st.sidebar

    sb.markdown('<p class="uae-navgroup" style="margin-left:0">📅 Time period</p>',
                unsafe_allow_html=True)
    years = sb.multiselect("Year(s)", opts["years"], default=[], key="dxb_years",
                           help="Leave empty to include every year (2010–2026).")

    sb.markdown('<p class="uae-navgroup" style="margin-left:0">📍 Location</p>',
                unsafe_allow_html=True)
    zones = sb.multiselect("Locality zone", opts["zones"], default=[], key="dxb_zones")
    areas = sb.multiselect("Area", opts["areas"], default=[], key="dxb_areas")

    sb.markdown('<p class="uae-navgroup" style="margin-left:0">🏠 Property</p>',
                unsafe_allow_html=True)
    rooms = sb.multiselect("Layout", opts["rooms"], default=[], key="dxb_rooms")
    reg_types = sb.multiselect("Registration type", opts["reg_types"], default=[],
                               key="dxb_reg",
                               help="Off-plan = bought before completion. "
                                    "Existing = already built.")

    sb.markdown('<p class="uae-navgroup" style="margin-left:0">💰 Ranges</p>',
                unsafe_allow_html=True)
    price_range = sb.slider(
        "Sale price (AED)",
        min_value=float(opts["price_min"]), max_value=float(opts["price_max"]),
        value=(float(opts["price_p01"]), float(opts["price_p99"])),
        format="%.0f", key="dxb_price",
        help="Starts at the 1st–99th percentile so a handful of extreme deals do "
             "not flatten every chart. Drag the ends out to include them.",
    )
    area_range = sb.slider(
        "Unit size (m²)",
        min_value=float(opts["area_min"]), max_value=float(opts["area_max"]),
        value=(float(opts["area_p01"]), float(opts["area_p99"])),
        format="%.0f", key="dxb_area",
        help="Starts at the 1st–99th percentile. Drag the ends out for the full range.",
    )

    if sb.button("🔄  Reset Dubai filters", use_container_width=True, key="dxb_reset"):
        for k in ["dxb_years", "dxb_zones", "dxb_areas", "dxb_rooms", "dxb_reg",
                  "dxb_price", "dxb_area"]:
            st.session_state.pop(k, None)
        st.rerun()

    return dict(years=years, zones=zones, areas=areas, rooms=rooms,
                reg_types=reg_types, price_range=price_range, area_range=area_range)


def _fmt(df: pd.DataFrame, fmt: dict, **kwargs) -> None:
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True,
                 hide_index=True, **kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────


def _section_insights(df: pd.DataFrame, dark: bool) -> None:
    ci.header("concentration_pareto")
    st.plotly_chart(ch.pareto(df, COL["area"], dark=dark), use_container_width=True, config=PC)

    value_by_area = df.groupby(COL["area"], observed=True)[COL["price"]].sum().sort_values(ascending=False)
    share = value_by_area.cumsum() / value_by_area.sum()
    n_for_80 = int((share < 0.8).sum() + 1)
    ui.chart_note(
        "Bars are total transaction value per area, tallest first; the line is the running "
        f"share of the whole market. <b>{n_for_80} of {len(value_by_area)} areas account for "
        "80% of all transaction value</b> in the current selection."
    )

    _fmt(mx.concentration(df, COL["area"], top_n=12), {
        "Total value (AED)": "{:,.0f}", "Median price (AED)": "{:,.0f}",
        "Median rate (AED/m²)": "{:,.0f}", "Transactions": "{:,}",
        "Share of transactions (%)": "{:.1f}", "Share of value (%)": "{:.1f}"})

    ui.block("The biggest master developments", "Ranked by total transaction value. "
             "Same calculation as the table above, grouped by master project.", "🏙️")
    _fmt(mx.concentration(df, COL["master_project"], top_n=10), {
        "Total value (AED)": "{:,.0f}", "Median price (AED)": "{:,.0f}",
        "Median rate (AED/m²)": "{:,.0f}", "Transactions": "{:,}",
        "Share of transactions (%)": "{:.1f}", "Share of value (%)": "{:.1f}"})

    c1, c2 = st.columns(2, gap="large")
    with c1:
        ci.header("tier_price")
        st.plotly_chart(ch.tier_rate_bar(df, COL["price_tier"], dark=dark),
                        use_container_width=True, config=PC)
        ui.chart_note("Price tier is a label already present in the dataset. The bars are the "
                      "check that the tiers separate on realised rate per m².")
    with c2:
        ci.header("grade_price")
        st.plotly_chart(ch.tier_rate_bar(df, COL["grade"], dark=dark),
                        use_container_width=True, config=PC)
        ui.chart_note("Building grade (A+ to D) against realised rate — does the grading line "
                      "up with what buyers actually pay?")

    if COL["yield"] in df.columns:
        ui.block("Estimated gross rental yield", "A dataset field, shown as the median across "
                 "each locality zone. Source: cleaned dataset, `Est. Gross Rental Yield (%)`.",
                 "📈")
        y = (df[df[COL["zone"]] != "Unknown"]
             .groupby(COL["zone"], observed=True)
             .agg(**{"Median yield (%)": (COL["yield"], "median"),
                     "Median rate (AED/m²)": (COL["rate"], "median"),
                     "Transactions": (COL["price"], "size")})
             .sort_values("Median yield (%)", ascending=False).reset_index())
        _fmt(y, {"Median yield (%)": "{:.2f}", "Median rate (AED/m²)": "{:,.0f}",
                 "Transactions": "{:,}"})
        ui.chart_note("Yield and rate usually move in opposite directions: the most expensive "
                      "zones tend to show the lowest gross yield. The yield figure is carried "
                      "in the dataset per building — it is not recomputed here.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — TRENDS
# ─────────────────────────────────────────────────────────────────────────────


def _section_trends(df: pd.DataFrame, dark: bool) -> None:
    ci.header("monthly_activity")
    st.plotly_chart(ch.monthly_volume_value(df, dark=dark), use_container_width=True, config=PC)
    ui.chart_note("Blue area = number of transactions. Dotted amber = 3-month average, which "
                  "smooths month-to-month noise. Teal bars = total value transacted.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        ci.header("annual_volume")
        st.plotly_chart(ch.annual_volume(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Taller bar = more deals closed that year.")
    with c2:
        ci.header("quarterly_heatmap")
        st.plotly_chart(ch.quarterly_heatmap(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Darker cell = busier quarter. Shows both the long-run growth and any "
                      "recurring within-year rhythm.")

    # ── Year-over-year, with the partial-year check beside it ────────────────
    # ── Year-over-year transaction volume ────────────────────────────────────
    #
    # DATA SOURCE: RAW registry, not the filtered cleaned frame. Transaction
    # counts must reflect what was actually recorded, and this chart therefore
    # deliberately ignores the sidebar filters — it answers "how many sales
    # were registered", not "how many sales match my selection". That is
    # stated on screen so the two can never be confused.
    _raw_volume_panel(dark)

    ci.header("seasonality")
    st.plotly_chart(ch.seasonality(df, dark=dark), use_container_width=True, config=PC)
    ui.chart_note("Transactions in each calendar month, pooled across every year in the "
                  "selection. Recent, busier years carry more weight in this pooling.")


def _raw_volume_panel(dark: bool) -> None:
    """
    Year-over-year transaction volume, computed from the RAW registry.

    Two rules govern this panel:

      1. Counts come from the raw registry, because preprocessing removes rows
         from the cleaned file and would understate recorded activity.
      2. The latest year is incomplete. It is shown as a count, and a growth
         percentage is displayed ONLY if the like-for-like comparison against
         the same months of the previous year is strictly positive. A shorter
         year is not a decline.
    """
    counts = load_raw_transaction_counts()
    years = mx.raw_transaction_years(counts)
    partial = mx.partial_year_growth(counts)

    ci.header("raw_yoy_volume")
    st.plotly_chart(ch.raw_transaction_volume(years, partial, dark=dark),
                    use_container_width=True, config=PC)

    complete = years[years["complete"]]
    first, last_complete = int(complete["year"].min()), int(complete["year"].max())
    ui.chart_note(
        f"Blue bars = transactions recorded each year, straight from the raw registry. "
        f"The dotted line is the change against the immediately preceding year, shown for "
        f"{first + 1}–{last_complete}; <b>{first} is the base year</b> and has nothing before "
        f"it to compare with. This panel is not affected by the sidebar filters — it reports "
        f"what was registered, not what matches your selection."
    )

    if not partial["complete"]:
        p = partial
        msg = (
            f"**{p['year']} is still in progress.** The registry covers "
            f"**{p['period_label']} {p['year']}** ({p['months_available']} of 12 months), "
            f"with **{p['transactions']:,}** transactions recorded so far against "
            f"**{p['basis_transactions']:,}** in the same months of {p['basis_year']}."
        )
        if p["display_growth"] is not None:
            st.success(msg + f" That is **{p['display_growth']:+.1f}%** like for like, so the "
                             f"growth figure is shown on the chart.", icon="📅")
        else:
            st.info(msg + " Because that is not an increase, **no growth percentage is shown "
                          "for this year** — a part-year count compared against a full year "
                          "would read as a decline that the data does not support.", icon="📅")

    # KPI cards replacing the removed like-for-like metric row.
    peak = complete.loc[complete["transactions"].idxmax()]
    fastest = complete.dropna(subset=["yoy_pct"])
    k1, k2, k3 = st.columns(3)
    k1.metric("Busiest completed year", f"{int(peak['year'])}",
              f"{int(peak['transactions']):,} transactions", delta_color="off")
    if not fastest.empty:
        top = fastest.loc[fastest["yoy_pct"].idxmax()]
        k2.metric("Strongest growth year", f"{int(top['year'])}",
                  f"{top['yoy_pct']:+.1f}% vs {int(top['year']) - 1}", delta_color="off")
    k3.metric(f"{partial['year']} so far ({partial['period_label']})",
              f"{partial['transactions']:,}",
              "no annual growth figure — part year"
              if partial["display_growth"] is None
              else f"{partial['display_growth']:+.1f}% like for like",
              delta_color="off")

    with st.expander("🔎  Year-by-year transaction counts, from the raw registry"):
        t = years.copy()
        t["Year"] = t["year"].astype(str)
        t.loc[~t["complete"], "Year"] = (
            t.loc[~t["complete"], "Year"] + f" ({partial['period_label']})")
        show = t[["Year", "transactions", "all_transactions", "yoy_pct"]].rename(columns={
            "transactions": "Residential unit sales (raw)",
            "all_transactions": "All registry transactions (raw)",
            "yoy_pct": "Growth vs previous year (%)"})
        _fmt(show, {"Residential unit sales (raw)": "{:,}",
                    "All registry transactions (raw)": "{:,}",
                    "Growth vs previous year (%)": "{:+.1f}"})
        st.caption(
            "Counted from `data/dubai/transactions.parquet`. The first column is the same "
            "population every other Dubai chart uses — residential unit sales — with no "
            "cleaning applied. The second is every transaction in the registry, including "
            "mortgages, gifts, land and villas, given for context. The incomplete year "
            "carries no growth figure."
        )

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — GEOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────


def _section_geography(df: pd.DataFrame, dark: bool) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        ci.header("top_areas_volume")
        st.plotly_chart(ch.top_areas_volume(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Where the most deals happen — not necessarily where the most money is.")
    with c2:
        ci.header("top_areas_rate")
        st.plotly_chart(ch.top_areas_rate(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Rate per m² strips out unit size, so a studio and a penthouse can be "
                      "compared fairly. Areas with fewer than 300 deals are excluded so a "
                      "single sale cannot top the chart.")

    ci.header("area_treemap")
    st.plotly_chart(ch.area_treemap(df, dark=dark), use_container_width=True, config=PC)
    ui.chart_note("Large and dark = a lot of money changing hands at a high price per m². "
                  "Large and pale = high volume at accessible prices.")

    ci.header("area_bubble")
    st.plotly_chart(ch.area_bubble(df, dark=dark), use_container_width=True, config=PC)
    ui.chart_note("Right = busy. Up = expensive. Bigger bubble = more total value. "
                  "The top-right corner is where both activity and price are high.")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        ci.header("zone_comparison")
        st.plotly_chart(ch.zone_comparison(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Zone labels come with the dataset. Bars = median rate; dotted line = "
                      "how many transactions sit behind each bar.")
    with c4:
        ci.header("metro_effect")
        st.plotly_chart(ch.metro_effect(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Median rate for units whose nearest station is each of these. This "
                      "reflects the neighbourhoods those stations serve at least as much as "
                      "the stations themselves.")

    with st.expander("📋  Area detail table"):
        tbl = (df.groupby(COL["area"], observed=True)
               .agg(Transactions=(COL["price"], "size"),
                    **{"Median price (AED)": (COL["price"], "median"),
                       "Median rate (AED/m²)": (COL["rate"], "median"),
                       "Median size (m²)": (COL["area_sqm"], "median"),
                       "Total value (AED)": (COL["price"], "sum")})
               .sort_values("Transactions", ascending=False).reset_index()
               .rename(columns={COL["area"]: "Area"}))
        _fmt(tbl, {"Transactions": "{:,}", "Median price (AED)": "{:,.0f}",
                   "Median rate (AED/m²)": "{:,.0f}", "Median size (m²)": "{:,.0f}",
                   "Total value (AED)": "{:,.0f}"}, height=420)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — PROPERTY
# ─────────────────────────────────────────────────────────────────────────────


def _section_property(df: pd.DataFrame, dark: bool) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        ci.header("layout_mix")
        st.plotly_chart(ch.layout_mix(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Number of transactions per bedroom configuration.")
    with c2:
        ci.header("size_by_layout")
        st.plotly_chart(ch.size_by_layout(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Median floor area for each layout — the denominator behind every "
                      "rate-per-m² figure on this page.")

    # ── Rate by layout: one panel per layout ─────────────────────────────────
    # PART 2 — the Area selector slices the frame BEFORE the quartiles are
    # computed, so "Downtown" really means Downtown transactions only.
    ci.header("rate_by_layout")
    # No area control here on purpose — the area comes from the global 📍 Area
    # section and has already been applied to `df` before this panel runs.
    layout_df, layout_area = df, nav.area()

    if layout_df.empty:
        st.info(f"No transactions recorded in {layout_area} within the current sidebar "
                f"selection. Choose another area or widen the sidebar filters.", icon="ℹ️")
        return

    fig, stats, excluded = ch.rate_by_layout(layout_df, dark=dark)

    if stats.empty:
        counts = layout_df[COL["rooms"]].value_counts()
        detail = (", ".join(f"{k} ({v:,})" for k, v in counts.head(7).items())
                  if not counts.empty else "none")
        st.warning(
            f"**Not enough data to draw a distribution for {layout_area}.** A box plot needs "
            f"at least 100 transactions in a layout before its quartiles mean anything, and "
            f"no layout here reaches that. Transactions available by layout: {detail}. "
            f"The data is not missing — it is simply too thin to summarise as a "
            f"distribution without misleading you.", icon="⚠️")
        return

    st.plotly_chart(fig, use_container_width=True, config=PC)

    if not stats.empty:
        lo = stats["med"].idxmin()
        hi = stats["med"].idxmax()
        ui.chart_note(
            "Each panel is one layout on a shared scale. Box = the middle 50% of "
            "transactions, line = median, whiskers = the furthest transaction within the "
            f"typical range. In this selection <b>{hi}</b> carries the highest median rate "
            f"(AED {stats.loc[hi, 'med']:,.0f}/m²) and <b>{lo}</b> the lowest "
            f"(AED {stats.loc[lo, 'med']:,.0f}/m²) — so in Dubai the larger layouts are "
            "generally <b>more</b> expensive per square metre, not less."
        )

    if not excluded.empty:
        names = ", ".join(
            f"{row['Layout']} ({int(row['Transactions']):,} deals, "
            f"median AED {row['Median rate (AED/m²)']:,.0f}/m²)"
            for _, row in excluded.iterrows())
        where = f" in {layout_area}" if layout_area != C.ALL_AREAS else ""
        st.caption(f"Not drawn as a distribution because fewer than 100 transactions "
                   f"support them{where}: {names}. Their medians are stated here rather "
                   f"than hidden — they are excluded from the panels, not from the data.")

    with st.expander("📋  Layout distribution table — every quartile behind the panels"):
        _fmt(ch.layout_stats_table(stats),
             {"Transactions": "{:,}", "Lower whisker": "{:,.0f}", "25th pct": "{:,.0f}",
              "Median": "{:,.0f}", "75th pct": "{:,.0f}", "Upper whisker": "{:,.0f}",
              "IQR": "{:,.0f}"})
        st.caption("Whiskers reach the furthest transaction within 1.5 × the interquartile "
                   "range. Transactions beyond them are genuine and remain in every "
                   "calculation on this page — they are simply not drawn as individual "
                   "points, which would put hundreds of thousands of marks on screen.")

    c3, c4 = st.columns(2, gap="large")
    with c3:
        ci.header("reg_type_split")
        st.plotly_chart(ch.reg_type_split(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("Off-plan = purchased before completion. Existing = already built.")
    with c4:
        ci.header("procedure_split")
        st.plotly_chart(ch.procedure_split(df, dark=dark), use_container_width=True, config=PC)
        ui.chart_note("The registration procedure recorded against each sale.")

    ci.header("size_vs_price")
    st.plotly_chart(ch.size_vs_price(df, dark=dark), use_container_width=True, config=PC)
    n = min(len(df), ch.SCATTER_SAMPLE)
    ui.chart_note(f"Showing a random sample of {n:,} of {len(df):,} transactions so the chart "
                  "stays responsive; the shape of the relationship is unchanged. Colour = "
                  "layout. Points high above the cloud are premium deals for their size.")

    with st.expander("📋  Layout detail table"):
        tbl = (df.groupby(COL["rooms"], observed=True)
               .agg(Transactions=(COL["price"], "size"),
                    **{"Median price (AED)": (COL["price"], "median"),
                       "Median rate (AED/m²)": (COL["rate"], "median"),
                       "Median size (m²)": (COL["area_sqm"], "median")})
               .sort_values("Transactions", ascending=False).reset_index()
               .rename(columns={COL["rooms"]: "Layout"}))
        _fmt(tbl, {"Transactions": "{:,}", "Median price (AED)": "{:,.0f}",
                   "Median rate (AED/m²)": "{:,.0f}", "Median size (m²)": "{:,.0f}"})


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — PRICE
# ─────────────────────────────────────────────────────────────────────────────


def _section_price(df: pd.DataFrame, dark: bool) -> None:
    # ── How prices are moving ────────────────────────────────────────────────
    ci.header("price_rate_trend")

    mode = st.radio("View", ["Both", "Smoothed trend", "Actual monthly"],
                    horizontal=True, key="dxb_smooth", label_visibility="collapsed",
                    help="Smoothing is a centred LOWESS fit — locally weighted regression over the "
                         "neighbouring months. The actual monthly observations are never "
                         "replaced, and the partial final month is excluded from the fit.")

    fig, monthly = ch.price_rate_trend(df, dark=dark, mode=mode)
    st.plotly_chart(fig, use_container_width=True, config=PC)

    # dropna() first: the trend is deliberately blank for the partial final
    # month, and pct_change would otherwise pad across that gap.
    raw_vol = monthly["median_rate"].dropna().pct_change().std() * 100
    sm_vol = monthly["smooth_rate"].dropna().pct_change().std() * 100
    ui.chart_note(
        "Two different questions. The blue line moves with <b>what</b> people buy (more large "
        "units pushes it up). The teal line is price per m² — the cleaner read on whether "
        "Dubai property itself is getting more expensive. "
        f"Smoothing cuts the standard deviation of month-on-month change in the rate series "
        f"from {raw_vol:.1f}% to {sm_vol:.1f}% without moving the level."
    )

    thin = monthly[monthly["Transactions"] < 0.6 * monthly["Transactions"].median()]
    if not thin.empty:
        names = ", ".join(f"{r.Month} ({int(r.Transactions):,} deals)"
                          for r in thin.tail(3).itertuples())
        st.caption(
            f"Months with materially fewer transactions than usual (median "
            f"{int(monthly['Transactions'].median()):,} per month): {names}. "
            "The most recent one is a partial month — the dataset ends mid-month — which is "
            "why the line falls sharply at the right-hand edge. It is shaded on the chart."
        )

    with st.expander("📋  Monthly values — actual and smoothed, side by side"):
        t = monthly[["Month", "Transactions", "median_price", "smooth_price",
                     "median_rate", "smooth_rate"]].copy()
        t.columns = ["Month", "Transactions", "Median price (actual)", "Median price (trend)",
                     "Median rate (actual)", "Median rate (trend)"]
        _fmt(t.iloc[::-1], {"Transactions": "{:,}", "Median price (actual)": "{:,.0f}",
                            "Median price (trend)": "{:,.0f}", "Median rate (actual)": "{:,.0f}",
                            "Median rate (trend)": "{:,.0f}"}, height=340)
        st.caption("Every actual monthly observation is preserved. The trend columns are a "
                   "centred LOWESS fit of the actual columns — nothing is substituted or "
                   "invented, and the trend is blank for any partial final month because "
                   "that month was excluded from the fit.")

    yt = mx.yoy_table(df)
    if len(yt) >= 2:
        first, last = yt.iloc[0], yt.iloc[-1]
        span_years = int(last["Year"]) - int(first["Year"])
        if span_years > 0 and first["Median rate (AED/m²)"]:
            total = (last["Median rate (AED/m²)"] / first["Median rate (AED/m²)"] - 1) * 100
            cagr = ((last["Median rate (AED/m²)"] / first["Median rate (AED/m²)"]) ** (1 / span_years) - 1) * 100
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Median rate {int(first['Year'])}", aed(first["Median rate (AED/m²)"]))
            m2.metric(f"Median rate {int(last['Year'])}", aed(last["Median rate (AED/m²)"]),
                      f"{total:+.1f}% total")
            m3.metric("Compound annual change", f"{cagr:+.1f}%",
                      help=f"Averaged over {span_years} years of the current selection.")

    # ── Volume against price, by year (MEAN rate) ────────────────────────────
    _volume_vs_price_panel(df, dark)

    # ── Year-wise summary table ──────────────────────────────────────────────
    # Replaces the off-plan pricing chart. Volume comes from the RAW registry,
    # rate statistics from the CLEANED dataset — each column says which.
    _yearly_summary_panel(df, dark)

    # ── Amenity association with recorded transactions ───────────────────────
    _amenity_association_panel(df, dark)

    # ── Building height ──────────────────────────────────────────────────────
    _building_height_panel(df, dark)

    # ── Price bands ──────────────────────────────────────────────────────────
    _price_bands_panel(df, dark)

    # ── Market history ───────────────────────────────────────────────────────
    # Position previously held by "Published price forecast". A forecast is not
    # replaced with another forecast — this is the recorded history instead.
    _market_history_panel(df)



def _yearly_summary_panel(df: pd.DataFrame, dark: bool) -> None:
    """
    Year-wise transactions and rate statistics, 2011 onwards.

    DATA SOURCE — two, on purpose and labelled as such:
      · Number of transactions → RAW registry (no preprocessing loss)
      · Mean and median rate/m² → CLEANED dataset (the validated price basis)

    The table makes no claim about off-plan against existing; it reports what
    each year looked like.
    """
    counts = load_raw_transaction_counts()
    table = mx.yearly_summary(counts, df)
    if table.empty:
        return

    ci.header("yearly_summary")

    partial = mx.partial_year_growth(counts)
    show = table.copy()
    show["Year"] = show["year"].astype(str)
    show.loc[~show["complete"], "Year"] = (
        show.loc[~show["complete"], "Year"] + f"  ({partial['period_label']}, in progress)")
    show = show[["Year", "transactions", "mean_rate", "median_rate", "priced_rows"]].rename(
        columns={"transactions": "Number of transactions (raw)",
                 "mean_rate": "Mean rate/m² (AED)",
                 "median_rate": "Median rate/m² (AED)",
                 "priced_rows": "Priced transactions used (cleaned)"})
    _fmt(show, {"Number of transactions (raw)": "{:,}", "Mean rate/m² (AED)": "{:,.0f}",
                "Median rate/m² (AED)": "{:,.0f}",
                "Priced transactions used (cleaned)": "{:,}"}, height=420)

    st.caption(
        "**Number of transactions** is counted in the raw registry, so it is not reduced by "
        "cleaning. **Mean and median rate/m²** are computed on the cleaned dataset, which is "
        "the validated basis for every price figure on this page and reflects the current "
        "sidebar selection — which is why the last column, the number of priced transactions "
        "actually used, is smaller. The mean sits above the median in every year because a "
        "few very large deals pull an average upward; the median is the typical transaction."
    )



def _amenity_association_panel(df: pd.DataFrame, dark: bool) -> None:
    """
    Part 5/6 — how common each amenity is among RECORDED transactions.

    This is deliberately NOT a price comparison and NOT a probability.

    There is no purchase / non-purchase outcome anywhere in either dataset:
    every row is a completed, recorded transaction, and a keyword sweep of both
    schemas for purchase / lead / enquiry / outcome / conversion / target
    columns returns nothing. A customer purchase probability therefore cannot
    be estimated here, and none is claimed. What is measured is the share of
    recorded transactions that carry each amenity flag.
    """
    ci.header("amenity_transaction_share")

    # Two local filters — Property type and Amenity. Area is NOT one of them:
    # it is chosen once in the global 📍 Area section and has already been
    # applied to `df`. Every number below comes from that one frame, so no
    # calculation can silently fall back to the full dataset.
    # TWO local filters only — Property type and Amenity. The area is global.
    scope, amn_area = df, nav.area()

    types = [lbl for val, lbl in mx.PROPERTY_TYPE_LABELS.items()
             if val in set(scope[COL["rooms"]].dropna().unique())]
    if not types:
        st.info(f"No property types recorded in {amn_area} within the current selection.",
                icon="ℹ️")
        return

    c1, c2 = st.columns(2)
    with c1:
        type_label = st.selectbox("Property type", types, key="dxb_amn_type")
    with c2:
        amenity_label = st.selectbox("Amenity", list(AMENITIES.values()), key="dxb_amn_field")

    column = {v: k for k, v in AMENITIES.items()}[amenity_label]
    ptype = mx.LABEL_TO_PROPERTY_TYPE[type_label]

    # The slice the user chose, and the Dubai-wide reference it is read against.
    # `df` is the full sidebar selection — every area, every property type.
    table, aud = mx.amenity_share_vs_baseline(scope, df, ptype)
    within = mx.amenity_transaction_share(scope, ptype)

    if table.empty or within.empty:
        n_here = int(aud.get("scope_rows", (scope[COL["rooms"]] == ptype).sum()))
        where = f"in {amn_area}" if amn_area != C.ALL_AREAS else "in the current selection"
        st.warning(
            f"**Only {n_here:,} {type_label} transactions {where}** — fewer than the "
            f"{mx.MIN_CELL} needed before a share is worth reporting. A percentage from "
            f"this few records would move wildly on one or two transactions, so none is "
            f"shown. Choose a different area or property type, or widen the sidebar "
            f"filters.", icon="⚠️")
        return

    # ONE graph — a plain grouped bar, not stacked. Each amenity gets its
    # recorded share in the selected slice beside the same figure across Dubai.
    #
    # It is a comparison rather than a ranking on purpose. Parking is recorded
    # on 88.9%-100.0% of transactions in every property type, so a ranking of
    # raw shares put parking first every time and looked like "parking matters
    # most" — a fact about record-keeping wearing the clothes of a market
    # finding. Against its own baseline parking shows no gap and stops
    # dominating, and a real difference becomes the thing you notice.
    scope_label = (f"{type_label} in {amn_area}" if amn_area != C.ALL_AREAS
                   else f"{type_label}, all areas")
    st.plotly_chart(
        ch.amenity_share_grouped(table, amenity_label, scope_label, dark=dark),
        use_container_width=True, config=PC)

    row = table[table["Amenity"] == amenity_label]
    if not row.empty:
        r = row.iloc[0]
        k1, k2, k3 = st.columns(3)
        k1.metric(f"{type_label} transactions in scope",
                  f"{int(r['Transactions (selection)']):,}")
        k2.metric(f"Recorded with {amenity_label.lower()}",
                  f"{int(r['Recorded with (selection)']):,}",
                  f"{r['Share in selection (%)']:.1f}% of them", delta_color="off")
        k3.metric("Against the Dubai figure",
                  f"{r['Share across Dubai (%)']:.1f}%",
                  f"{r['Difference (pp)']:+.1f} pp here", delta_color="off")

    top = table.iloc[0]
    ui.chart_note(
        f"Two bars per amenity: the coloured one is <b>{scope_label}</b>, the grey one is the "
        f"same measurement across all of Dubai under your current filters. "
        f"<b>Read the gap between them, not the height.</b> The biggest gap here is "
        f"<b>{top['Amenity'].lower()}</b>, recorded on {top['Share in selection (%)']:.1f}% of "
        f"these sales against {top['Share across Dubai (%)']:.1f}% city-wide "
        f"({top['Difference (pp)']:+.1f} percentage points). Amenities are ordered by the "
        f"size of that gap, so the most distinctive one is on the left."
    )

    st.caption(
        "**Reading the bars.** Each bar is how often a feature appears on the transaction "
        "record. Parking is recorded on almost every Dubai apartment, so the useful signal "
        "is the gap between the coloured bar and the grey one: that is where this slice of "
        "the market differs from the city as a whole."
    )

    with st.expander(f"📋  Every amenity — {scope_label} against Dubai"):
        t = table[["Amenity", "Share in selection (%)", "Share across Dubai (%)",
                   "Difference (pp)", "Recorded with (selection)",
                   "Transactions (selection)"]].copy()
        t.columns = ["Amenity", f"{scope_label} (%)", "All Dubai (%)",
                     "Difference (pp)", "Recorded with", "Transactions in scope"]
        _fmt(t, {f"{scope_label} (%)": "{:.1f}", "All Dubai (%)": "{:.1f}",
                 "Difference (pp)": "{:+.1f}", "Recorded with": "{:,}",
                 "Transactions in scope": "{:,}"})
        st.caption(f"Both percentages are shares of recorded transactions. The difference "
                   f"column is simply the first minus the second, in percentage points. "
                   f"Scope: {aud['scope_rows']:,} transactions; Dubai reference: "
                   f"{aud['baseline_rows']:,}.")


def _volume_vs_price_panel(df: pd.DataFrame, dark: bool) -> None:
    """
    Part 8 — transaction volume against price, by year.

    Volume from the RAW registry; rate from the CLEANED dataset. This chart uses
    the MEAN rate per m², not the median — see `metrics.volume_vs_mean_rate` for
    why, and the note on screen states it.
    """
    counts = load_raw_transaction_counts()
    table = mx.volume_vs_mean_rate(counts, df)
    if table.empty:
        return

    ci.header("volume_vs_price")
    st.plotly_chart(ch.volume_vs_mean_rate(table, dark=dark),
                    use_container_width=True, config=PC)

    priced = table.dropna(subset=["mean_rate"])
    corr = float(priced["transactions"].corr(priced["mean_rate"])) if len(priced) > 2 else float("nan")
    ui.chart_note(
        f"Bars are the number of transactions recorded each year, counted in the <b>raw "
        f"registry</b>. The line is the <b>mean</b> rate per m² for the same year, from the "
        f"cleaned dataset. Across the years in this selection the two move together "
        f"(correlation {corr:.2f}) — busier years have also been dearer years."
    )

    st.info(
        "**Why the mean here, when the rest of the page uses the median.** This chart asks "
        "whether busy years are also expensive years — a question about the money moving "
        "through the market as a whole. The mean reflects the entire distribution, including "
        "the upper tail that a hot market actually adds; the median deliberately ignores it. "
        "Both are reported side by side in the year-by-year table below, so the difference "
        "between them stays visible — the mean sits above the median in every year, which is "
        "the effect of a small number of very large deals.",
        icon="ℹ️")

    with st.expander("📋  Year · transaction volume · mean rate/m²"):
        t = table.copy()
        t["Year"] = t["year"].astype(int).astype(str)
        t.loc[~t["complete"], "Year"] = t.loc[~t["complete"], "Year"] + " (part year)"
        t = t[["Year", "transactions", "mean_rate", "median_rate"]]
        t.columns = ["Year", "Transaction volume (raw)", "Mean rate/m² (AED)",
                     "Median rate/m² (AED)"]
        _fmt(t, {"Transaction volume (raw)": "{:,}", "Mean rate/m² (AED)": "{:,.0f}",
                 "Median rate/m² (AED)": "{:,.0f}"})


def _building_height_panel(df: pd.DataFrame, dark: bool) -> None:
    """
    Rate per m² by building-height band, split by property type.

    IMPORTANT — what this is and is not. The dataset does not record which
    floor a unit sits on: `floor_bin` is the string "Unknown" wherever it is
    populated, and `floors` is identical for every sale in a given building, so
    it describes the building's height, not the unit's floor. This panel is
    therefore about building height, and says so. Bands are the quartiles of
    the height distribution taken one row per building.
    """
    ci.header("height_price")

    # PART 4 — Area selector first; the height bands and every median below are
    # computed from the sliced frame, not from all of Dubai.
    # Area comes from the global 📍 Area section, already applied to `df`.
    scope, hgt_area = df, nav.area()

    if scope.empty:
        st.info(f"No transactions recorded in {hgt_area} within the current sidebar "
                f"selection.", icon="ℹ️")
        return

    # Rows come from the area slice; band BOUNDARIES come from the unfiltered
    # selection, so "Low-rise" means the same thing in every area and two
    # areas remain comparable.
    frame, audit = mx.rate_by_building_height(scope, band_source=df)

    if frame.empty:
        with_height = int(scope[mx.FLOOR_FIELD].notna().sum()) if mx.FLOOR_FIELD in scope else 0
        st.warning(
            f"**No height-banded figures can be shown for {hgt_area}.** Building height is "
            f"recorded for {with_height:,} of the {len(scope):,} transactions here, and no "
            f"height-band × property-type combination reaches the {mx.MIN_CELL}-transaction "
            f"minimum. Rather than draw medians on a handful of deals, nothing is plotted. "
            f"Choose a larger area or widen the sidebar filters.", icon="⚠️")
        return

    st.plotly_chart(ch.rate_by_building_height(frame, dark=dark),
                    use_container_width=True, config=PC)

    counts = audit.get("band_counts", {})
    bands = " · ".join(f"{b} — {counts.get(b, 0):,} transactions" for b in audit["bands"])
    ui.chart_note(
        f"Four <b>fixed</b> floor bands, on round thresholds rather than quantiles, so "
        f"“Low-rise” means the same building in every area and does not shift when you "
        f"change the filters: {bands}. Boundaries are inclusive at the top — a building of "
        f"exactly 10 floors is Low-rise, exactly 11 is Mid-rise. The legend is the property "
        f"type; compare one colour across the bands to see how the rate differs by building "
        f"height for that size of apartment."
    )

    st.caption(
        "**Reading the bands.** These describe the height of the building, so the chart "
        "compares apartments in low-rise blocks against those in mid-rise, high-rise and "
        "tower buildings. `floors` is the field behind it, and it is well populated — a "
        "floor count is present for the large majority of transactions shown."
    )

    st.caption(
        f"Height is recorded for **{audit['rows_with_height']:,}** of "
        f"**{audit['rows_total']:,}** transactions in the current selection "
        f"({audit['coverage_pct']}%); the rest are not plotted."
        + (f" A further **{audit['invalid_floor']:,}** record zero floors — a building "
           f"cannot have none, so those are treated as an invalid reading and excluded "
           f"rather than counted as low-rise." if audit.get("invalid_floor") else "")
        + f" Combinations with fewer than {audit['min_cell']} transactions are omitted "
          f"rather than drawn on thin data"
        + (f" — {', '.join(audit['dropped'])}." if audit["dropped"] else ".")
    )

    with st.expander("📐  The four floor bands, and how they were set"):
        band_tbl = pd.DataFrame([
            {"Floor band": b, "Floors covered": audit["spans"].get(b, ""),
             "Transactions": counts.get(b, 0)}
            for b in audit["bands"]])
        _fmt(band_tbl, {"Transactions": "{:,}"})
        st.caption(
            "The dataset holds two floor-related columns and only one is usable. "
            "`floor_bin` is populated on 505,993 rows and carries the single literal value "
            "`Unknown` on every one of them — no information at all. `floors` is the number "
            "of floors in the **building**, verified identical for every sale within a given "
            "building across all 2,245 buildings tested. The bands above are fixed "
            "thresholds on round numbers, so they are stable across areas and filters; "
            "earlier they were quartiles of the current selection, which could label a "
            "17-storey building “Low-rise” in a district of towers."
        )

    with st.expander("📋  Median and mean rate behind every bar"):
        t = frame[["height_band", "Property type", "median_rate", "mean_rate",
                   "transactions"]].copy()
        t.columns = ["Building height band", "Property type", "Median rate (AED/m²)",
                     "Mean rate (AED/m²)", "Transactions"]
        _fmt(t, {"Median rate (AED/m²)": "{:,.0f}", "Mean rate (AED/m²)": "{:,.0f}",
                 "Transactions": "{:,}"})


def _price_bands_panel(df: pd.DataFrame, dark: bool) -> None:
    ci.header("price_bands")
    bands, audit = mx.price_bands(df)

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.plotly_chart(ch.band_bar(bands, dark=dark), use_container_width=True, config=PC)
    with c2:
        _fmt(bands, {"Transactions": "{:,}", "Share (%)": "{:.1f}"})
        st.caption(f"Chart and table are generated from the same computed frame, so they "
                   f"cannot disagree. **{audit['assigned']:,}** of **{audit['total']:,}** "
                   f"transactions were assigned to a band "
                   f"({audit['unassigned']:,} unassigned); shares sum to "
                   f"{audit['share_sum']:.1f}%.")

    _top_areas_by_band(df, dark)


def _band_count_unfiltered(band: str) -> int:
    """
    How many transactions sit in a bracket across the WHOLE cleaned dataset,
    ignoring the sidebar filters.

    Used only to tell the difference between "your filters emptied this
    bracket" and "this bracket is genuinely empty" — so a filtering artefact is
    never presented as missing data. Read-only, and it reuses the existing
    cached loader rather than reading the parquet again.
    """
    try:
        full = load_market()
    except Exception:  # pragma: no cover - loader already failed louder upstream
        return 0
    counted = pd.cut(full[COL["price"]], bins=mx.BAND_EDGES, labels=mx.BAND_LABELS,
                     right=False)
    return int((counted == band).sum())


def _top_areas_by_band(df: pd.DataFrame, dark: bool) -> None:
    """
    PART 5 — the five busiest areas inside each sale-price bracket.

    Area names are never hard-coded: they come out of the filtered dataframe by
    transaction count. Bracket boundaries are left-closed / right-open, so a
    sale of exactly AED 1,000,000 sits in "1M – 2M" and in nothing else. The
    audit underneath proves every priced transaction landed in exactly one
    bracket.
    """
    table, audit = mx.top_areas_by_band(df)

    ci.header("top_areas_by_band")

    if table.empty:
        st.info("No transactions with both a valid sale price and a recorded area in the "
                "current selection.", icon="ℹ️")
        return

    # All seven brackets are always offered, including any the sidebar filters
    # have emptied. Hiding a bracket would make a filtering effect look like
    # missing data — and the top bracket is the one most often filtered away,
    # because the sale-price slider defaults to the 1st–99th percentile.
    choice = st.radio("Price bracket", mx.BAND_LABELS, horizontal=True,
                      key="dxb_band_top_areas",
                      help="Each bracket is ranked independently. The ranking is by number "
                           "of transactions inside that bracket, not by price. Brackets with "
                           "no transactions under your current filters are still listed.")

    n_band = audit["band_totals"].get(choice, 0)
    single = audit.get("single_area")

    if n_band == 0 and single:
        st.info(
            f"**{single} has no transactions in the {choice} bracket.** That is a real "
            f"absence in this area, not missing data — nothing in {single} sold at this "
            f"price under the current filters. Pick another bracket, or clear the area at "
            f"the top of the page to see which areas do trade here.", icon="ℹ️")
        return

    if n_band == 0:
        in_full = _band_count_unfiltered(choice)
        if in_full:
            st.warning(
                f"**No transactions in the {choice} bracket under the current filters — but "
                f"{in_full:,} exist in the dataset.** The sidebar's sale-price slider starts "
                f"at the 1st–99th percentile, which trims the very top and bottom of the "
                f"market, and that is what has emptied this bracket. Widen the sale-price "
                f"slider to its full range and this bracket will populate. Nothing is "
                f"missing from the data.", icon="⚠️")
        else:
            st.info(f"No transactions fall in the {choice} bracket, either under the current "
                    f"filters or in the dataset as a whole.", icon="ℹ️")
        return

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.plotly_chart(ch.top_areas_in_band(table, choice, dark=dark),
                        use_container_width=True, config=PC)
    with right:
        t = table[table["Price band (AED)"] == choice][
            ["Rank", "Area", "Transactions", "Share of band (%)"]]
        _fmt(t, {"Transactions": "{:,}", "Share of band (%)": "{:.1f}"})
        top_share = float(t["Share of band (%)"].sum())
        if single:
            st.caption(f"**{n_band:,}** transactions in {single} fall in the {choice} "
                       f"bracket. Only {single} is in scope, so it accounts for all of them.")
        else:
            st.caption(f"**{n_band:,}** transactions fall in the {choice} bracket. These "
                       f"{len(t)} areas account for **{top_share:.1f}%** of them; the "
                       f"remainder are spread across the other areas in the selection.")

    ui.chart_note(
        f"Ranked by transaction count inside the <b>{choice}</b> bracket only — an area that "
        f"is busy overall will not appear here unless it is busy <i>at this price</i>. "
        f"Rank 1 is drawn at the top. Both the chart and the table are built from one "
        f"computed frame, so they cannot disagree."
    )

    with st.expander("📋  Top 5 areas in every bracket, and the classification audit"):
        _fmt(table, {"Transactions": "{:,}", "Share of band (%)": "{:.1f}"})

        st.markdown("**Boundary rule**")
        st.caption(audit["boundary_rule"])

        st.markdown("**Classification audit**")
        a1, a2, a3 = st.columns(3)
        a1.metric("Transactions in selection", f"{audit['total']:,}")
        a2.metric("Valid sale price", f"{audit['valid']:,}")
        a3.metric("Classified into a bracket", f"{audit['classified']:,}",
                  "0 unassigned" if audit["unassigned"] == 0
                  else f"{audit['unassigned']:,} unassigned", delta_color="off")

        lines = [
            f"- Every one of the **{audit['valid']:,}** transactions with a valid sale price "
            f"was classified into exactly one bracket "
            f"(**{audit['unassigned']:,}** unassigned).",
        ]
        if audit["invalid_price"]:
            lines.append(f"- **{audit['invalid_price']:,}** excluded for a missing or "
                         f"non-positive sale price — a genuinely invalid value, not a "
                         f"filtering choice.")
        if audit["missing_area"]:
            lines.append(f"- **{audit['missing_area']:,}** have a valid price but no recorded "
                         f"area, so they count toward the bracket totals but cannot be "
                         f"ranked into an area.")
        if audit["empty_bands"]:
            lines.append(f"- Brackets with no qualifying transaction in this selection: "
                         f"{', '.join(audit['empty_bands'])}. Empty because of the current "
                         f"sidebar filters, not because the ranking failed — widen the "
                         f"sale-price slider to see them.")
        else:
            lines.append("- Every bracket has qualifying transactions and a populated top 5.")
        st.markdown("\n".join(lines))

    ui.chart_note("Bands are left-closed and right-open, so every transaction falls in exactly "
                  "one band. The mass of the market sits in the tallest bars; the tail to the "
                  "right is the luxury segment.")

    # The default price slider truncates the top bands — say so rather than
    # letting an empty band read as a data error.
    lo, hi = st.session_state.get("dxb_price", (None, None))
    if hi is not None and audit["empty_bands"]:
        st.warning(
            f"**The sale-price filter is currently set to AED {lo:,.0f} – {hi:,.0f}**, which "
            f"is why {', '.join(audit['empty_bands'])} "
            f"{'shows' if len(audit['empty_bands']) == 1 else 'show'} zero transactions. "
            "That is the filter, not the data — widen the **Sale price (AED)** slider in the "
            "sidebar to see the full range. Unfiltered, the cleaned dataset contains 5,308 "
            "sales at AED 10M or more (0.6% of the market).",
            icon="🔍",
        )


def _unit_size_summary(df: pd.DataFrame) -> None:
    """
    Replaces the removed "Unit size distribution" histogram, in its own position.

    Same subject — how big the units are — expressed as a compact statistical
    table by property type instead of a shape. DATA SOURCE: CLEANED.
    """
    ci.header("unit_size_summary")

    order = [v for v in mx.PROPERTY_TYPE_LABELS
             if v in set(df[COL["rooms"]].dropna().unique())]
    if not order:
        st.caption("No property types in the current selection.")
        return

    g = (df[df[COL["rooms"]].isin(order)]
         .groupby(COL["rooms"], observed=True)[COL["area_sqm"]]
         .agg(Transactions="size", Smallest="min", p25=lambda s: s.quantile(.25),
              Median="median", p75=lambda s: s.quantile(.75), Largest="max")
         .reindex(order).dropna(how="all").reset_index())
    g["Property type"] = g[COL["rooms"]].map(mx.PROPERTY_TYPE_LABELS)
    g = g[["Property type", "Transactions", "Smallest", "p25", "Median", "p75", "Largest"]]
    g.columns = ["Property type", "Transactions", "Smallest (m²)", "25th pct (m²)",
                 "Median (m²)", "75th pct (m²)", "Largest (m²)"]
    _fmt(g, {"Transactions": "{:,}", "Smallest (m²)": "{:,.0f}", "25th pct (m²)": "{:,.0f}",
             "Median (m²)": "{:,.0f}", "75th pct (m²)": "{:,.0f}", "Largest (m²)": "{:,.0f}"})

    overall = df[COL["area_sqm"]].dropna()
    st.caption(
        f"Half of all transactions in this selection are between "
        f"**{overall.quantile(.25):,.0f} m²** and **{overall.quantile(.75):,.0f} m²**, with a "
        f"median of **{overall.median():,.0f} m²**. The smallest and largest columns are single "
        f"transactions, not typical sizes."
    )


def _price_by_reg_summary(df: pd.DataFrame) -> None:
    """
    Replaces the removed "Sale price by registration type" box plot, in place.

    A descriptive summary of each registration type: how many transactions, and
    what the prices looked like. No comparison between the two is computed and
    no premium or discount is stated. DATA SOURCE: CLEANED.
    """
    ci.header("price_by_reg_summary")

    if COL["reg_type"] not in df.columns or df.empty:
        st.caption("No registration-type information in the current selection.")
        return

    # Mean sits BESIDE the median, never instead of it: the mean is the
    # arithmetic average and is pulled by very large deals, the median is the
    # middle transaction and is not. Both are computed per registration type,
    # from the same sale-price field (COL["price"]) on the same filtered frame.
    g = (df.groupby(COL["reg_type"], observed=True)
           .agg(Transactions=(COL["price"], "size"),
                p25=(COL["price"], lambda s: s.quantile(.25)),
                Mean=(COL["price"], "mean"),
                Median=(COL["price"], "median"),
                p75=(COL["price"], lambda s: s.quantile(.75)),
                MedianRate=(COL["rate"], "median"))
           .reset_index().rename(columns={COL["reg_type"]: "Registration type"}))
    g["Share of transactions (%)"] = g["Transactions"] / g["Transactions"].sum() * 100
    g = g[["Registration type", "Transactions", "Share of transactions (%)",
           "p25", "Mean", "Median", "p75", "MedianRate"]]
    g.columns = ["Registration type", "Transactions", "Share of transactions (%)",
                 "25th pct price (AED)", "Mean price (AED)", "Median price (AED)",
                 "75th pct price (AED)", "Median rate (AED/m²)"]
    _fmt(g, {"Transactions": "{:,}", "Share of transactions (%)": "{:.1f}",
             "25th pct price (AED)": "{:,.0f}", "Mean price (AED)": "{:,.0f}",
             "Median price (AED)": "{:,.0f}",
             "75th pct price (AED)": "{:,.0f}", "Median rate (AED/m²)": "{:,.0f}"})

    st.caption(
        "Each row describes its own registration type: how many transactions it accounts "
        "for, and where its prices sit. The 25th and 75th percentile columns bracket the "
        "middle half of that group's sales. The two rows are reported separately and are "
        "not compared against each other here."
    )

    gap = g["Mean price (AED)"] - g["Median price (AED)"]
    ui.chart_note(
        "<b>Mean and median are both shown, because they answer different questions.</b> "
        "The mean is the arithmetic average — every sale, including the largest, pulls on "
        "it. The median is the middle transaction, so a handful of very large deals cannot "
        "move it. "
        + " ".join(
            f"For <b>{r['Registration type']}</b> the mean sits AED {d:,.0f} "
            f"{'above' if d >= 0 else 'below'} the median."
            for (_, r), d in zip(g.iterrows(), gap)
        )
        + " A mean above the median is the signature of a right-skewed price distribution."
    )


def _market_history_panel(df: pd.DataFrame) -> None:
    """
    Replaces the removed "Published price forecast", in its own position.

    A forecast is not replaced with another forecast. This is the historical and
    current record instead: where rates have been, where they are now, and how
    long it took to get there. DATA SOURCE: CLEANED, filtered selection.
    """
    ci.header("market_history")

    yearly = (df.groupby(COL["year"], observed=True)
                .agg(median_rate=(COL["rate"], "median"),
                     median_price=(COL["price"], "median"),
                     transactions=(COL["rate"], "size"))
                .sort_index())
    if len(yearly) < 2:
        st.caption("Not enough years in the current selection.")
        return

    first_year, last_year = int(yearly.index[0]), int(yearly.index[-1])
    first_rate = float(yearly["median_rate"].iloc[0])
    last_rate = float(yearly["median_rate"].iloc[-1])
    peak_year = int(yearly["median_rate"].idxmax())
    trough_year = int(yearly["median_rate"].idxmin())
    span = max(last_year - first_year, 1)
    cagr = ((last_rate / first_rate) ** (1 / span) - 1) * 100 if first_rate else float("nan")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"Median rate — {last_year}", aed(last_rate),
              f"{(last_rate / first_rate - 1) * 100:+.0f}% since {first_year}",
              delta_color="off")
    k2.metric("Highest year on record", f"{peak_year}",
              aed(yearly['median_rate'].max()), delta_color="off")
    k3.metric("Lowest year on record", f"{trough_year}",
              aed(yearly['median_rate'].min()), delta_color="off")
    k4.metric("Average change per year", f"{cagr:+.1f}%",
              f"across {span} years", delta_color="off")

    recovery = ""
    if trough_year < last_year:
        rec = (last_rate / float(yearly.loc[trough_year, "median_rate"]) - 1) * 100
        recovery = (f" Since the low point in {trough_year} the median rate has moved "
                    f"**{rec:+.0f}%**.")

    st.info(
        f"**What the record shows, on the current selection.** The median rate moved from "
        f"**{aed(first_rate)}/m²** in {first_year} to **{aed(last_rate)}/m²** in {last_year} "
        f"— an average of **{cagr:+.1f}% a year**, though not evenly: the strongest year was "
        f"{peak_year} and the weakest {trough_year}.{recovery} These are recorded outcomes, "
        f"not a projection — no forecast is made here.",
        icon="🧭")

    with st.expander("📋  Median rate and price for every year in the selection"):
        t = yearly.reset_index()
        t.columns = ["Year", "Median rate (AED/m²)", "Median price (AED)", "Transactions"]
        t["Year"] = t["Year"].astype(int).astype(str)
        _fmt(t, {"Median rate (AED/m²)": "{:,.0f}", "Median price (AED)": "{:,.0f}",
                 "Transactions": "{:,}"})
        st.caption("Computed on the cleaned dataset under the current sidebar filters. "
                   "Transaction counts here are the priced rows behind each median — the "
                   "raw registry counts are in the Trends section.")


def _price_range_explainer(df: pd.DataFrame) -> None:
    """
    §10 — what the range on the two histograms above actually means.

    The wording below describes the calculation that is genuinely running:
    `charts.price_histogram` trims the display to the 0.5th–99.5th percentile,
    divides THAT span into 60 equal-width bins, counts transactions per bin, and
    draws the median of the untrimmed data as a dashed line. Every figure quoted
    here is recomputed from the same selection, so the text cannot describe one
    thing while the chart draws another.
    """
    price = df[COL["price"]].dropna()
    rate = df[COL["rate"]].dropna()
    if price.empty or rate.empty:
        return

    lo, hi = price.quantile([0.005, 0.995])
    p25, p75 = price.quantile([0.25, 0.75])
    inside = float(((price >= p25) & (price <= p75)).mean() * 100)
    bin_width = (hi - lo) / 60

    ui.block("How to read the range on these two charts", "", "📏")
    st.markdown(
        f"""
- **The far left is the cheapest end.** The lowest sale price in this selection is
  **{aed(price.min())}**. That is one real transaction, not a typical one.
- **The far right is the most expensive end.** The highest is **{aed(price.max())}** —
  again a single transaction.
- **Most of the market is nowhere near either end.** Half of all sales here fall between
  **{aed(p25)}** and **{aed(p75)}** ({inside:.0f}% of transactions), and the middle of the
  market — the median — is **{aed(price.median())}**, marked by the dashed line.
- **Where one property sits.** Find its price along the bottom axis. The height of the bar
  above it is how many other sales landed in the same slice of the range, so a tall bar
  means "priced like a lot of other people", and a short bar out on the right means
  "unusual for this market".
        """
    )
    st.caption(
        f"**Method, stated plainly.** The bars cover the 0.5th to 99.5th percentile of the "
        f"current selection — **{aed(lo)}** to **{aed(hi)}** — so that a handful of extreme "
        f"deals cannot squash everything else into one bar. That span is cut into 60 equal "
        f"slices about {aed(bin_width)} wide, and the height of each bar is the number of "
        f"transactions in that slice. The 1% of sales outside that span are still in every "
        f"other calculation on this page, including the median line and the minimum and "
        f"maximum quoted above; they are simply off the ends of this picture. The rate "
        f"chart beside it is built the same way, on AED per m² instead of total price "
        f"(median **{aed(rate.median())}**/m²)."
    )


def _section_distribution(df: pd.DataFrame, dark: bool) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        ci.header("dist_price")
        st.plotly_chart(ch.price_histogram(df, COL["price"], "", "AED", dark=dark),
                        use_container_width=True, config=PC)
        ui.chart_note("Tallest bars = the most common price points. The long right tail is "
                      "normal for property — a few very large deals pull the average above "
                      "the median.")
    with c2:
        ci.header("dist_rate")
        st.plotly_chart(ch.price_histogram(df, COL["rate"], "", "AED/m²", dark=dark),
                        use_container_width=True, config=PC)
        ui.chart_note("More than one peak here would suggest distinct market tiers rather "
                      "than one continuous market.")

    _price_range_explainer(df)

    c3, c4 = st.columns(2, gap="large")
    with c3:
        # Position previously held by "Unit size distribution".
        _unit_size_summary(df)
    with c4:
        # Position previously held by "Sale price by registration type".
        _price_by_reg_summary(df)

    ci.header("rate_violin_year")
    st.plotly_chart(ch.rate_violin_by_year(df, dark=dark), use_container_width=True, config=PC)
    ui.chart_note("Each shape is one year. Wider = more transactions at that rate. Watch both "
                  "the centre moving up and the shape getting wider — the second means the "
                  "market is spreading out, not just rising.")

    ui.block("Summary statistics", "Computed on the full filtered selection, not a sample.",
             "📋")
    rows = []
    for label, col, unit in [("Sale price", COL["price"], "AED"),
                             ("Rate per m²", COL["rate"], "AED/m²"),
                             ("Unit size", COL["area_sqm"], "m²"),
                             ("Balcony area", COL["balcony_area"], "m²")]:
        s = mx.summary_stats(df, col)
        if s:
            rows.append({
                "Measure": f"{label} ({unit})", "Count": s["count"], "Mean": s["mean"],
                "Median": s["median"], "25th pct": s["p25"], "75th pct": s["p75"],
                "95th pct": s["p95"], "Min": s["min"], "Max": s["max"], "Skew": s["skew"],
            })
    _fmt(pd.DataFrame(rows), {"Count": "{:,}", "Mean": "{:,.1f}", "Median": "{:,.1f}",
                              "25th pct": "{:,.1f}", "75th pct": "{:,.1f}",
                              "95th pct": "{:,.1f}", "Min": "{:,.1f}", "Max": "{:,.1f}",
                              "Skew": "{:.2f}"})
    ui.chart_note("A positive skew means the average sits above the median — the median is "
                  "the more representative figure for a typical transaction.")


# ─────────────────────────────────────────────────────────────────────────────
# DATA PROVENANCE
# ─────────────────────────────────────────────────────────────────────────────


def _provenance_panel() -> None:
    prov = load_provenance()
    if not prov:
        return
    raw, clean, rel = prov["raw"], prov["clean"], prov["relationship"]
    with st.expander("🗄️  Where this data comes from"):
        st.markdown(
            f"""
Two Dubai datasets ship with the platform.

| | Raw registry | Cleaned dataset (used here) |
|---|---|---|
| **File** | `{raw['file']}` | `{clean['file']}` |
| **Transactions** | {raw['rows']:,} | {clean['rows']:,} |
| **Columns** | {raw['columns']} | {clean['columns']} |
| **Date range** | {raw['date_min']} → {raw['date_max']} | {clean['date_min']} → {clean['date_max']} |
| **Areas** | {raw['areas']} | {clean['areas']} |

The raw file is the full transaction registry — sales, mortgages and gifts, across units,
villas, land and whole buildings. {rel['note']}

Of the {rel['raw_matching_slice']:,} residential-unit sales in the raw registry,
**{rel['clean_rows']:,} ({rel['coverage_pct']}%)** carry through to the cleaned dataset,
which adds {rel['added_columns']} engineered columns.

**Every chart on this page states its own source** in the badge beside its title, and the ⓘ
control names the exact columns and calculation. Charts marked CLEANED read the cleaned
dataset; the price-band and parking analyses were additionally validated against the raw
registry. This comparison is precomputed by `tools/build_dubai_provenance.py`, so the 81 MB
raw file is never read to draw a page.
            """
        )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — DOWNLOAD REPORT
# ─────────────────────────────────────────────────────────────────────────────


def _report_body(df: pd.DataFrame, df_all: pd.DataFrame, area: str) -> None:
    """
    The PDF report, sitting inside the Dubai dashboard right after Distribution.

    It reports on exactly what the rest of this page is showing: the same
    dataframe, after the same sidebar filters and the same global area. The
    file builds itself when this tab opens and rebuilds whenever the area
    changes, so the download button is simply present rather than hidden
    behind a "generate" step.
    """
    ui.section("Download detailed report",
               f"A print-ready PDF of this Dubai analysis for {area}.", "📄")

    if df.empty:
        st.warning("No transactions in the current selection, so there is nothing to "
                   "report.", icon="🔍")
        return

    try:
        from platform_core import dubai_report as builder
    except Exception as exc:  # pragma: no cover
        st.error(f"**The report builder could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Area covered", area)
    c2.metric("Transactions in report", f"{len(df):,}")
    c3.metric("Share of Dubai", f"{len(df) / max(len(df_all), 1) * 100:.1f}%")

    signature = (area, len(df))
    if st.session_state.get("dxb_report_sig") != signature:
        try:
            with st.spinner(f"Preparing the {area} report — computing figures and drawing "
                            f"charts…"):
                st.session_state["dxb_report_pdf"] = builder.build(df, area, len(df_all))
            st.session_state["dxb_report_sig"] = signature
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            st.session_state.pop("dxb_report_pdf", None)
            st.session_state.pop("dxb_report_sig", None)
            st.error(f"**The report could not be generated.**\n\n"
                     f"`{type(exc).__name__}: {exc}`", icon="⚠️")
            return

    pdf_bytes = st.session_state.get("dxb_report_pdf")
    if not pdf_bytes:
        return

    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in area)
    fname = f"Dubai_Analytics_Report_{safe}_{datetime.now():%Y%m%d}.pdf"

    st.download_button(
        f"⬇️   Download the {area} report  ·  PDF",
        data=pdf_bytes, file_name=fname, mime="application/pdf",
        type="primary", use_container_width=True, key="dxb_report_dl")

    st.caption(
        f"**{fname}** — {len(pdf_bytes) / 1024:,.0f} KB, covering {len(df):,} transactions "
        f"for {area}. Change the area at the top of this page and the report rebuilds "
        f"itself for that area."
    )

    st.info(
        "**What is inside.** Title page with the reporting period and area context; "
        "executive summary with headline figures and key findings; then transaction volume, "
        "price levels and movement, rate per m² by layout, rate by building height, amenity "
        "analysis, registration type, and price brackets with the top five areas in each — "
        "each with its chart, its table and a note on what the numbers do and do not mean; "
        "and a closing methodology section covering the data sources, how this selection was "
        "formed, and the assumptions and limitations. Every figure is computed from the same "
        "data driving the charts above, at the moment you open this tab.", icon="ℹ️")


def _section_download_report(df: pd.DataFrame, df_all: pd.DataFrame, area: str,
                             dark: bool = False) -> None:
    """
    The Download Report tab: the area PDF for whatever 📍 Area holds.

    The forecast is NOT rendered here. It has its own destination — 🔮 Forecast
    in the rail — where its inputs, chart and explanation belong. The 📄 Download
    Detailed Report page is where the two are offered together as downloads.
    """
    _report_body(df, df_all, area)

    st.caption("Looking for the forecast? It has its own page — 🔮 **Forecast** in the "
               "rail. The 📄 **Download Detailed Report** page offers the area report, "
               "the forecast report and both combined in one PDF.")


def _global_area_picker(df_all: pd.DataFrame) -> str:
    """
    The Dubai area selector, shown at the top of the page.

    It writes the SAME platform state (`C.SS_AREA`) that the 📍 Area section in
    the rail writes, so the two are one control in two places rather than two
    controls that can disagree. Changing it reruns the page, and because the
    slice is applied before any aggregation, every KPI, chart and table below
    changes with it.
    """
    counts = df_all[COL["area"]].dropna().value_counts()
    options = [C.ALL_AREAS] + [str(a) for a in counts.index]
    labels = {C.ALL_AREAS: f"{C.ALL_AREAS}  ({len(df_all):,} transactions)"}
    labels.update({str(a): f"{a}  ({int(n):,})" for a, n in counts.items()})

    current = nav.area()
    if current not in options:
        current = C.ALL_AREAS

    left, right = st.columns([3, 2], gap="large")
    with left:
        chosen = st.selectbox(
            "📍  Area — applies to this entire Dubai dashboard",
            options, index=options.index(current),
            format_func=lambda a: labels.get(a, a), key="dxb_global_area",
            help="Pick an area once here and every section of this dashboard — KPIs, "
                 "insights, all six analytical tabs and the downloadable report — is "
                 "recalculated from that area's transactions only.")
    with right:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        if chosen != C.ALL_AREAS:
            st.caption(f"Showing **{chosen}** only. Set it back to *{C.ALL_AREAS}* for the "
                       f"whole Dubai market.")
        else:
            st.caption("Showing every Dubai area. Choose one to narrow the whole page.")

    if chosen != nav.area():
        nav.set_area(chosen)
        st.rerun()
    return chosen



def render(dark: bool = False) -> None:
    """Render the whole Dubai regional dashboard."""
    try:
        with st.spinner("Loading Dubai market data…"):
            df_all = load_market()
            opts = filter_options()
    except (DubaiDataError, FileNotFoundError) as exc:
        st.error(f"**Dubai market data could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    filters = _sidebar_filters(opts)
    df = apply_filters(df_all, **filters)

    # ── GLOBAL AREA ──────────────────────────────────────────────────────────
    # One value, chosen once — either here at the top of the page or in the
    # 📍 Area section in the rail; both write the same platform state. It is
    # applied HERE, after the sidebar filters and before every calculation on
    # the page, so no individual panel needs (or has) its own area control and
    # every figure below is guaranteed to describe one population.
    global_area = _global_area_picker(df_all)
    if global_area != C.ALL_AREAS:
        df = df[df[COL["area"]] == global_area]

    if df.empty:
        if global_area != C.ALL_AREAS:
            st.warning(
                f"**No transactions in {global_area} match the current sidebar filters.** "
                f"The area itself has data — the Dubai controls in the sidebar have narrowed "
                f"it to nothing. Widen them, or change the area under 📍 **Area**.", icon="🔍")
        else:
            st.warning("No transactions match the current filters. Adjust the selection in "
                       "the sidebar under **Dubai controls**.", icon="🔍")
        return

    if len(df) == len(df_all):
        scope = f"all {len(df_all):,} transactions"
    else:
        scope = (f"{len(df):,} of {len(df_all):,} transactions — the price and size "
                 "sliders start at the 1st–99th percentile")

    if global_area != C.ALL_AREAS:
        st.info(
            f"📍 **Area: {global_area}.** Every figure on this page is calculated from the "
            f"**{len(df):,}** transactions recorded in {global_area} that match your sidebar "
            f"filters. Change or clear it under 📍 **Area** in the rail.", icon="📍")

    # ── 1. Executive KPIs ────────────────────────────────────────────────────
    ui.section("Executive KPIs", f"Live indicators across {scope} in the current selection.", "📊")
    ui.kpi_grid(mx.executive_kpis(df))

    # ── 2. Smart Business Insights ───────────────────────────────────────────
    ui.section("Smart Business Insights",
               "Observations derived automatically from the filtered Dubai data.", "💡")
    insights = mx.smart_insights(df)
    if insights:
        left, right = st.columns(2, gap="large")
        half = (len(insights) + 1) // 2
        for emoji, html in insights[:half]:
            with left:
                ui.insight_row(emoji, html)
        for emoji, html in insights[half:]:
            with right:
                ui.insight_row(emoji, html)
    else:
        st.caption("Not enough data in the current selection to generate observations.")

    # ── 3. Market Snapshot ───────────────────────────────────────────────────
    ui.section("Market Snapshot", "Quick-reference summary of the current selection.", "📋")
    snap = mx.market_snapshot(df)
    cols = st.columns(3, gap="large")
    for i, (label, value) in enumerate(snap):
        with cols[i % 3]:
            st.metric(label, value)

    _provenance_panel()

    # ── 4–9. Analytics ───────────────────────────────────────────────────────
    ui.divider_label("Analytics")

    tabs = st.tabs([
        "💡 Insights", "📈 Trends", "🗺️ Geography",
        "🏠 Property", "💵 Price", "📊 Distribution", "📄 Download Report",
    ])

    with tabs[0]:
        _section_insights(df, dark)
    with tabs[1]:
        _section_trends(df, dark)
    with tabs[2]:
        _section_geography(df, dark)
    with tabs[3]:
        _section_property(df, dark)
    with tabs[4]:
        _section_price(df, dark)
    with tabs[5]:
        _section_distribution(df, dark)
    with tabs[6]:
        _section_download_report(df, df_all, global_area, dark)
