"""RAK regional dashboard — report-sourced.

The existing RAK overview, monthly, popular-area, property-use, investor,
latest-month and report-download subsections remain available alongside the
new dynamic Yearly Analytics and Quarterly Analytics views.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core.chart_theme import PLOTLY_CONFIG

from . import analytics as data
from . import charts as ch
from . import sources as S

PC = PLOTLY_CONFIG


def _fmt(df: pd.DataFrame, fmt: dict, **kwargs) -> None:
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True,
                 hide_index=True, **kwargs)


def _aed(v) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"AED {v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"AED {v / 1e6:,.2f}M"
    if abs(v) >= 1e3:
        return f"AED {v / 1e3:,.1f}K"
    return f"AED {v:,.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────


def _section_overview() -> None:
    ui.section("RAK Market Overview", "Report-sourced Ras Al Khaimah market intelligence.", "🏙️")
    st.markdown(
        f'<div class="uae-card uae-d1">'
        f'<p class="uae-sub" style="max-width:96ch">{S.RAK_OVERVIEW_NARRATIVE}</p>'
        f'<p class="uae-sub" style="max-width:96ch;margin-top:.6rem;'
        f'font-size:.78rem;opacity:.75">Source: '
        f'{S.RAK_ANNUAL_2025["citation"]}</p></div>',
        unsafe_allow_html=True,
    )

    cards = [
        {"label": k["label"], "value": k["value"], "icon": k["icon"],
         "color_class": k["color_class"], "tooltip": f"{k['change']} — {k['period']}"}
        for k in S.RAK_KEY_STATS
    ]
    ui.kpi_grid(cards, per_row=4)
    cols = st.columns(4)
    for col, k in zip(cols, S.RAK_KEY_STATS):
        with col:
            st.caption(f"**{k['change']}** — {k['period']}")


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC YEARLY + QUARTERLY ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────


def _format_metric(value: float | int | None, unit: str) -> str:
    if unit == "AED":
        return _aed(value)
    if value is None:
        return "—"
    return f"{value:,.0f}"


def _metric_table(snapshot: data.AnnualSnapshot | data.QuarterlySnapshot) -> None:
    rows = [
        {"Metric": label, "Value": _format_metric(snapshot.metrics.get(key), unit), "Unit": unit}
        for label, key, unit in data.ALL_METRICS
    ]
    _fmt(pd.DataFrame(rows), {})


def _kpis(snapshot: data.AnnualSnapshot | data.QuarterlySnapshot) -> None:
    for start in range(0, len(data.ALL_METRICS), 4):
        columns = st.columns(4, gap="medium")
        for column, (label, key, unit) in zip(columns, data.ALL_METRICS[start:start + 4]):
            with column:
                st.metric(label, _format_metric(snapshot.metrics.get(key), unit))


def _chart(figure) -> None:
    st.plotly_chart(figure, use_container_width=True, config=PC)


def _section_yearly(dark: bool) -> None:
    ui.section(
        "Yearly Analytics",
        "Select a year to view one aggregate annual-report graph, KPIs and table.",
        "📈",
    )
    year_options = list(data.ANNUAL_YEAR_OPTIONS)
    default_year = data.latest_available_annual_year() or year_options[-1]
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(default_year),
        key="rak.yearly.year",
    )
    snapshot = data.annual_snapshot(year)
    if snapshot is None:
        available = ", ".join(str(period) for period in data.available_annual_years())
        st.info(
            f"No supplied annual report contains {year}. "
            f"Annual report-backed years currently available: {available}."
        )
        return

    st.caption(f"Source: RAK Statistics Office official annual transaction report · {year}.")
    _kpis(snapshot)
    _chart(ch.annual_value_chart(snapshot, dark=dark))
    _metric_table(snapshot)


def _section_quarterly(dark: bool) -> None:
    ui.section(
        "Quarterly Analytics",
        "Quarterly values come from complete January–March, April–June, "
        "July–September or October–December monthly report triplets.",
        "📆",
    )
    year_options = list(data.ANNUAL_YEAR_OPTIONS)
    latest = data.latest_completed_quarter(year_options)
    default_year = latest[0] if latest else year_options[-1]
    with_year, with_quarter = st.columns(2, gap="medium")
    with with_year:
        year = st.selectbox(
            "Year",
            year_options,
            index=year_options.index(default_year),
            key="rak.quarterly.year",
        )
    quarter_options = list(data.available_quarters(year))
    with with_quarter:
        if quarter_options:
            default_quarter = latest[1] if latest and latest[0] == year else quarter_options[-1]
            quarter = st.selectbox(
                "Quarter",
                quarter_options,
                index=quarter_options.index(default_quarter),
                key="rak.quarterly.quarter",
            )
        else:
            st.selectbox(
                "Quarter",
                ["No completed quarter"],
                disabled=True,
                key="rak.quarterly.quarter.unavailable",
            )
            quarter = None

    if quarter is None:
        st.info(
            f"No complete quarter is available for {year}. A quarter is shown only when "
            "all three required monthly reports are present; no incomplete quarter is generated."
        )
        return

    snapshot = data.quarterly_snapshot(year, quarter)
    if snapshot is None:
        st.info("That quarter is no longer complete in the available monthly source set.")
        return

    st.caption(
        f"Monthly sources: {', '.join(snapshot.months)} {year}. "
        "The chart shows month-by-month values inside the selected complete quarter."
    )
    _kpis(snapshot)
    _chart(ch.quarterly_monthly_value_chart(snapshot, dark=dark))
    _metric_table(snapshot)


# SECTION 3 — POPULAR AREAS
# ─────────────────────────────────────────────────────────────────────────────


def _section_areas() -> None:
    ui.section("Popular Areas",
               "The three most-traded regions by sales value in 2025 (with 2024 comparison).",
               "🗺️")

    st.plotly_chart(ch.popular_areas_2025(), use_container_width=True, config=PC)
    ui.chart_note(
        "Reproduces RAK Annual 2025 Figure 2. Jazeerat AL Marjan topped the ranking "
        "in both 2024 and 2025 by sales value, though its 2025 sales value fell 77% "
        "from AED 4.04B to AED 940M."
    )

    rows = [[r["rank"], r["region"],
             _aed(r["sales_value_2025_aed"]), f"{r['sales_number_2025']:,}",
             _aed(r["sales_value_2024_aed"]), f"{r['sales_number_2024']:,}",
             f"{r['change_pct']:+d}%"]
            for r in S.RAK_POPULAR_AREAS_2025]
    _fmt(pd.DataFrame(rows, columns=["Rank", "Region",
                                      "2025 sales value", "2025 sales #",
                                      "2024 sales value", "2024 sales #",
                                      "Δ value"]), {})
    st.caption(f"Source: {S.RAK_ANNUAL_2025['citation']}")

    with st.expander("📋  Historical — top three regions in 2022 (RAK Annual 2022 Table 2)"):
        rows = [[r["rank"], r["region"],
                 _aed(r["sales_value_2022_aed"]), f"{r['sales_number_2022']:,}"]
                for r in S.RAK_POPULAR_AREAS_2022]
        _fmt(pd.DataFrame(rows, columns=["Rank", "Region",
                                          "2022 sales value", "2022 sales #"]), {})
        st.caption(f"Top region in 2022 by transaction value: {S.RAK_TOP_REGION_2022['region']}. "
                   f"Source: {S.RAK_ANNUAL_2022['citation']}")

    with st.expander("📋  Historical — top three regions in 2021 (RAK Annual 2021 Table 2)"):
        rows = [[r["rank"], r["region"],
                 _aed(r["sales_value_2021_aed"]), f"{r['sales_number_2021']:,}",
                 _aed(r["sales_value_2020_aed"]) if r["sales_value_2020_aed"] else "—",
                 f"{r['sales_number_2020']:,}" if r["sales_number_2020"] else "—",
                 f"{r['change_pct']:+d}%" if r["change_pct"] is not None
                    else r.get("note", "—")]
                for r in S.RAK_POPULAR_AREAS_2021]
        _fmt(pd.DataFrame(rows, columns=["Rank", "Region",
                                          "2021 sales value", "2021 sales #",
                                          "2020 sales value", "2020 sales #",
                                          "Δ value"]), {})
        st.caption(f"Source: {S.RAK_ANNUAL_2021['citation']}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — PROPERTY USE
# ─────────────────────────────────────────────────────────────────────────────


def _section_property() -> None:
    ui.section("Property Use",
               "Sales value by land type, as reported in RAK Annual 2025 Table 3.",
               "🏠")

    st.plotly_chart(ch.property_use_2024_2025(), use_container_width=True, config=PC)
    ui.chart_note(
        "Reproduces RAK Annual 2025 Figure 3. The source highlights a sharp increase "
        "in Popular Houses (+55%) and Commercial Unit (+43%), and a sharp decrease in "
        "Touristic Lands (-87%) between 2024 and 2025."
    )

    rows = []
    for r in S.RAK_PROPERTY_USE_2024_2025:
        rows.append([
            r["use"],
            _aed(r["y2024_aed"]) if r["y2024_aed"] else "—",
            f"{r['y2024_n']:,}" if r["y2024_n"] else "—",
            f"{r['y2024_share']}%",
            _aed(r["y2025_aed"]) if r["y2025_aed"] else "—",
            f"{r['y2025_n']:,}" if r["y2025_n"] else "—",
            f"{r['y2025_share']}%",
            f"{r['change_pct']:+d}%" if r["change_pct"] is not None
                else r.get("note", "—"),
        ])
    _fmt(pd.DataFrame(rows, columns=["Property use",
                                      "2024 sales value", "2024 #", "2024 share",
                                      "2025 sales value", "2025 #", "2025 share",
                                      "Δ value"]), {})
    st.caption(f"Source: {S.RAK_ANNUAL_2025['citation']}. {S.RAK_PROPERTY_USE_NOTE}")

    with st.expander("📋  Historical — Property Use 2021 vs 2022 (RAK Annual 2022 Table 3)"):
        rows = []
        for r in S.RAK_PROPERTY_USE_2021_2022:
            rows.append([
                r["use"],
                _aed(r["y2021_aed"]), f"{r['y2021_n']:,}" if r["y2021_n"] else "—",
                f"{r['y2021_share']}%",
                _aed(r["y2022_aed"]), f"{r['y2022_n']:,}" if r["y2022_n"] else "—",
                f"{r['y2022_share']}%",
                f"{r['change_pct']:+d}%" if r["change_pct"] is not None else "—",
            ])
        _fmt(pd.DataFrame(rows, columns=["Property use",
                                          "2021 sales value", "2021 #", "2021 share",
                                          "2022 sales value", "2022 #", "2022 share",
                                          "Δ value"]), {})
        st.caption(f"Source: {S.RAK_ANNUAL_2022['citation']}. Sharp increases: Touristic Lands "
                   f"+192%, Commercial Unit +76%; sharp decrease: Commercial Lands -61%.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — INVESTORS
# ─────────────────────────────────────────────────────────────────────────────


def _section_investors() -> None:
    ui.section("Investors",
               "Top ten investing nationalities by transaction value and by number.",
               "🌍")

    tot = S.RAK_INVESTORS_TOTALS
    left, right = st.columns(2)
    with left:
        st.metric("Total Investors 2025", f"{tot['y2025']:,}",
                  f"vs {tot['y2024']:,} in 2024", delta_color="off")
    with right:
        st.metric("Change 2024 → 2025", f"+{tot['y2025'] - tot['y2024']:,} investors",
                  f"{(tot['y2025'] / tot['y2024'] - 1) * 100:+.1f}%", delta_color="off")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(ch.investors_by_value_2025(),
                        use_container_width=True, config=PC)
    with c2:
        st.plotly_chart(ch.investors_by_number_2025(),
                        use_container_width=True, config=PC)

    ui.chart_note(
        "Reproduces RAK Annual 2025 Table 4 (value) and Figure 4 (number). UAE "
        "nationals dominate both rankings by a wide margin."
    )

    with st.expander("📋  Full 2024 & 2025 tables — investors by transaction value"):
        rows25 = [[r["rank"], r["nationality"], _aed(r["value_aed"])]
                  for r in S.RAK_INVESTORS_BY_VALUE_2025]
        _fmt(pd.DataFrame(rows25, columns=["Rank", "Nationality", "2025 value"]), {})
        rows24 = [[r["rank"], r["nationality"], _aed(r["value_aed"])]
                  for r in S.RAK_INVESTORS_BY_VALUE_2024]
        _fmt(pd.DataFrame(rows24, columns=["Rank", "Nationality", "2024 value"]), {})
    st.caption(f"Source: {S.RAK_ANNUAL_2025['citation']}")

    with st.expander("📋  Historical — Investors 2022 (RAK Annual 2022 Tables 4 & 5)"):
        st.caption(f"Total Investors in 2022: {S.RAK_TOTAL_INVESTORS_2022:,}. "
                   f"Source: {S.RAK_ANNUAL_2022['citation']}")
        rows_v = [[r["rank"], r["nationality"], _aed(r["value_aed"])]
                  for r in S.RAK_INVESTORS_BY_VALUE_2022]
        _fmt(pd.DataFrame(rows_v, columns=["Rank", "Nationality", "2022 value"]), {})
        rows_n = [[r["rank"], r["nationality"], f"{r['count']:,}"]
                  for r in S.RAK_INVESTORS_BY_NUMBER_2022]
        _fmt(pd.DataFrame(rows_n, columns=["Rank", "Nationality", "2022 investor count"]), {})


# ─────────────────────────────────────────────────────────────────────────────
# SECTION — MONTHLY TIME SERIES (built from every readable monthly PDF)
# ─────────────────────────────────────────────────────────────────────────────


def _section_monthly() -> None:
    ui.section("Monthly Time Series",
               "Every monthly RAK Statistics Office report the user provided, "
               "with values extracted verbatim.", "📆")

    n_pts = len(S.RAK_MONTHLY_TIMESERIES)
    with_full = sum(1 for r in S.RAK_MONTHLY_TIMESERIES if r["mort_v"] and r["waiv_v"])
    sales_only = sum(1 for r in S.RAK_MONTHLY_TIMESERIES
                     if r["sales_v"] and not (r["mort_v"] or r["waiv_v"]))

    c1, c2, c3 = st.columns(3)
    c1.metric("Data points extracted", f"{n_pts}")
    c2.metric("Months with full breakdown", f"{with_full}")
    c3.metric("Months with sales only", f"{sales_only}")

    ui.block("Sales / Mortgages / Waivers — all three series", "", "📈")
    st.plotly_chart(ch.monthly_three_series(), use_container_width=True, config=PC)
    ui.chart_note(
        "Each dot is one month whose value is stated in the corresponding RAK "
        "Statistics Office monthly report. Lines break where the source is missing "
        "for that series (older 2019–2020 monthlies only carry Sales figures)."
    )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(ch.monthly_sales_value(), use_container_width=True, config=PC)
    with c2:
        st.plotly_chart(ch.monthly_sales_count(), use_container_width=True, config=PC)

    with st.expander("📋  Full monthly table — every value with its source note"):
        rows = []
        for r in S.RAK_MONTHLY_TIMESERIES:
            rows.append([
                f"{r['month']} {r['year']}",
                _aed(r["sales_v"]) if r["sales_v"] else "—",
                f"{r['sales_n']:,}" if r["sales_n"] else "—",
                _aed(r["mort_v"])  if r["mort_v"]  else "—",
                f"{r['mort_n']:,}"  if r["mort_n"]  else "—",
                _aed(r["waiv_v"])  if r["waiv_v"]  else "—",
                f"{r['waiv_n']:,}"  if r["waiv_n"]  else "—",
                r["source_note"],
            ])
        _fmt(pd.DataFrame(rows, columns=["Period", "Sales value", "Sales #",
                                          "Mortgages value", "Mortgages #",
                                          "Waivers value", "Waivers #",
                                          "Source note"]), {})

# SECTION 6 — LATEST MONTH + DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────


def _section_latest_and_download() -> None:
    ui.section("Latest Month — January 2026",
               "Most recent monthly report from the RAK Statistics Office.",
               "📅")

    st.plotly_chart(ch.jan_2025_vs_2026(), use_container_width=True, config=PC)
    ui.chart_note(
        "Reproduces RAK Monthly Jan 2026 Figure 1. The source states: Real Estate "
        "Volume decreased 55% and Mortgages Value decreased 88% year-on-year, while "
        "Sales Number increased 29%."
    )

    m26 = S.RAK_JAN_2026
    m25 = S.RAK_JAN_2025
    rows = [
        ["Real Estate Sales Volume", _aed(m26["sales_value_aed"]),
         _aed(m25["sales_value_aed"]), "-55%"],
        ["Real Estate Mortgages Volume", _aed(m26["mortgages_aed"]),
         _aed(m25["mortgages_aed"]), "-88%"],
        ["Waivers Market Value", _aed(m26["waivers_aed"]),
         _aed(m25["waivers_aed"]), "-46%"],
        ["Real Estate Sales Number", f"{m26['sales_count']:,}",
         f"{m25['sales_count']:,}", "+29%"],
        ["Real Estate Mortgages Number", f"{m26['mortgages_count']:,}",
         f"{m25['mortgages_count']:,}", "-6%"],
        ["Waivers Number", f"{m26['waivers_count']:,}",
         f"{m25['waivers_count']:,}", "-28%"],
    ]
    _fmt(pd.DataFrame(rows, columns=["Category", "January 2026", "January 2025",
                                      "Δ (source)"]), {})

    ui.block("Highest sale values", "", "🏆")
    for h in S.RAK_JAN_HIGHEST_SALES:
        st.markdown(f"• **{h['period']}** — {h['region']} · {h['type']} · "
                    f"**{_aed(h['value_aed'])}**")

    ui.block("Top region by sales — January", "", "🥇")
    top26 = S.RAK_JAN_TOP_REGION_2026
    top25 = S.RAK_JAN_TOP_REGION_2025
    st.markdown(
        f"• **January 2026:** {top26['region']} — {_aed(top26['sales_value_aed'])} "
        f"across {top26['sales_count']} sales"
    )
    st.markdown(
        f"• **January 2025:** {top25['region']} — {_aed(top25['sales_value_aed'])} "
        f"across {top25['sales_count']} sales"
    )

    ui.block("Freehold market — January 2026", "", "🏢")
    rows = [[r["land_use"], f"{r['count']:,}", _aed(r["value_aed"]), f"{r['share_pct']}%"]
            for r in S.RAK_JAN_FREEHOLD_MARKET]
    _fmt(pd.DataFrame(rows, columns=["Land use", "Sales #", "Sales value", "Share"]), {})
    tot = S.RAK_JAN_FREEHOLD_AREAS_TOTAL
    st.caption(
        f"Total in Freehold Areas (January 2026): **{tot['sales_count']:,}** sales, "
        f"**{_aed(tot['sales_value_aed'])}**. "
        f"Source: {S.RAK_MONTHLY_JAN26['citation']}"
    )

    st.markdown("---")

    # ── Sources & download ──────────────────────────────────────────────────
    ui.section("Download detailed report",
               "A print-ready RAK PDF in the TruEstate.ai report format.",
               "📄")

    try:
        from platform_core import rak_report as builder
    except Exception as exc:  # pragma: no cover
        st.error(f"**The RAK report builder could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    if st.session_state.get("rak_report_pdf") is None:
        try:
            with st.spinner("Building the RAK report…"):
                st.session_state["rak_report_pdf"] = builder.build()
        except Exception as exc:  # pragma: no cover
            st.session_state.pop("rak_report_pdf", None)
            st.error(f"**The report could not be generated.**\n\n"
                     f"`{type(exc).__name__}: {exc}`", icon="⚠️")
            return

    pdf_bytes = st.session_state.get("rak_report_pdf")
    if pdf_bytes:
        fname = f"RAK_Market_Analytics_Report_{datetime.now():%Y%m%d}.pdf"
        st.download_button(
            "⬇️   Download the RAK report  ·  PDF",
            data=pdf_bytes, file_name=fname, mime="application/pdf",
            type="primary", use_container_width=True, key="rak_report_dl")
        st.caption(f"{fname} — {len(pdf_bytes) / 1024:,.0f} KB")

    with st.expander("🗄️  Sources & per-section provenance"):
        for r in S.all_sources():
            st.markdown(f"**{r['publisher']}** — {r['title']}  ·  _{r['period']}_")
        rows = [[section, cite] for section, cite in S.source_index()]
        _fmt(pd.DataFrame(rows, columns=["Section", "Source"]), {})


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────────────────


def render(dark: bool = False) -> None:
    _section_overview()

    ui.divider_label("Analytics")

    tabs = st.tabs([
        "📈 Yearly Analytics",
        "📆 Quarterly Analytics",
        "📆 Monthly",
        "🗺️ Popular Areas",
        "🏠 Property Use",
        "🌍 Investors",
        "📅 Latest & Download",
    ])
    with tabs[0]:
        _section_yearly(dark)
    with tabs[1]:
        _section_quarterly(dark)
    with tabs[2]:
        _section_monthly()
    with tabs[3]:
        _section_areas()
    with tabs[4]:
        _section_property()
    with tabs[5]:
        _section_investors()
    with tabs[6]:
        _section_latest_and_download()
