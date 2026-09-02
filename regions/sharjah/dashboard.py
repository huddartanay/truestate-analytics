"""
Sharjah regional dashboard — report-sourced.

Every value on this page comes from `regions.sharjah.sources`. No live dataset
is loaded, no Dubai logic is invoked, and no value is computed from anything
that is not already published in one of the three source reports.

The visual language deliberately mirrors the Dubai dashboard so the page reads
as first-class regional analytics inside the same product.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core.chart_theme import PLOTLY_CONFIG

from . import charts as ch
from . import sources as S

PC = PLOTLY_CONFIG


def _fmt(df: pd.DataFrame, fmt: dict, **kwargs) -> None:
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True,
                 hide_index=True, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# SECTIONS
# ─────────────────────────────────────────────────────────────────────────────


def _section_overview() -> None:
    ui.section("Sharjah Market Overview", S.SHARJAH_OVERVIEW_SUBTITLE, "🏙️")
    st.markdown(
        f'<div class="uae-card uae-d1">'
        f'<p class="uae-sub" style="max-width:96ch">{S.SHARJAH_OVERVIEW_NARRATIVE}</p>'
        f'<p class="uae-sub" style="max-width:96ch;margin-top:.6rem;'
        f'font-size:.78rem;opacity:.75">Source: '
        f'{S.SAVILLS_Q1_2026["citation"]}</p></div>',
        unsafe_allow_html=True,
    )


def _section_key_stats() -> None:
    ui.section("Key Stats", "Q1 2026 headline figures as reported by Savills.", "📊")
    cards = [
        {"label": k["label"], "value": k["value"], "icon": k["icon"],
         "color_class": k["color_class"], "tooltip": f"{k['change']} — {k['period']}"}
        for k in S.SHARJAH_KEY_STATS
    ]
    ui.kpi_grid(cards, per_row=4)
    changes = st.columns(len(S.SHARJAH_KEY_STATS))
    for col, k in zip(changes, S.SHARJAH_KEY_STATS):
        with col:
            st.caption(f"**{k['change']}** — {k['period']}")


def _section_monthly_dynamics() -> None:
    ui.section("Monthly Dynamics — Q1 2026",
               "Month-by-month narrative from the Savills report.", "🗓️")
    cols = st.columns(3, gap="large")
    for col, m in zip(cols, S.SHARJAH_MONTHLY_DYNAMICS):
        with col:
            ui.block(m["month"], "", "▪")
            st.markdown(f"**{m['headline']}**")
            st.caption(m["note"])
    ui.chart_note(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_transaction_value() -> None:
    ui.section("Transaction Value",
               "Published quarterly reference points (AED billion).", "💰")
    st.plotly_chart(ch.transaction_value_points(), use_container_width=True, config=PC)
    ui.chart_note(S.SHARJAH_TRANSACTION_VALUE_CHART_NOTE)

    rows = [
        [p["period"], f"AED {p['value_aed_billion']:.1f}B", p["status"], p["note"]]
        for p in S.SHARJAH_TRANSACTION_VALUE_POINTS
    ]
    df = pd.DataFrame(rows, columns=["Period", "Value", "Status", "Note"])
    _fmt(df, {})
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_transaction_volume() -> None:
    ui.section("Transaction Volume",
               "Published transaction-count reference points.", "🔢")
    st.plotly_chart(ch.transaction_volume_points(), use_container_width=True, config=PC)
    ui.chart_note(S.SHARJAH_TRANSACTION_VOLUME_CHART_NOTE)

    rows = [
        [p["period"], f"{p['transactions']:,}", p["status"], p["note"]]
        for p in S.SHARJAH_TRANSACTION_VOLUME_POINTS
    ]
    df = pd.DataFrame(rows, columns=["Period", "Transactions", "Status", "Note"])
    _fmt(df, {})
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_investors() -> None:
    ui.section("Investment by Nationality",
               "Q1 2026 investment by buyer origin, in AED billion.", "🌍")
    st.plotly_chart(ch.investor_nationality(), use_container_width=True, config=PC)
    ui.chart_note(
        "Reproduces the Savills Q1 2026 investment-by-nationality chart using the "
        "exact reported AED-billion values in the order the source presents them."
    )
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_property_type() -> None:
    ui.section("Sales by Property Type",
               "Share of residential sales transactions (%), Q1 2026.", "🏠")
    st.plotly_chart(ch.property_type_share(), use_container_width=True, config=PC)
    ui.chart_note(S.SHARJAH_PROPERTY_TYPE_NOTE)
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_top_areas() -> None:
    ui.section("Top Performing Areas — Q1 2026",
               "Ranking by trading value, in AED million.", "🗺️")
    st.plotly_chart(ch.top_areas(), use_container_width=True, config=PC)

    rows = [[a["rank"], a["area"], f"AED {a['value_aed_million']:,}M", a.get("note", "")]
            for a in S.SHARJAH_TOP_AREAS]
    df = pd.DataFrame(rows, columns=["Rank", "Area", "Trading value", "Note"])
    _fmt(df, {})
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_notable_transactions() -> None:
    ui.section("Notable Transactions", "Q1 2026 individual deals from Savills.", "📋")
    rows = [[t["area"], t["type"], t["transaction_type"], f"AED {t['value_aed_million']:,}M"]
            for t in S.SHARJAH_NOTABLE_TRANSACTIONS]
    df = pd.DataFrame(rows, columns=["Area", "Type", "Transaction Type", "Value"])
    _fmt(df, {})
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_new_projects() -> None:
    ui.section("New Project Registrations", "Sharjah project pipeline, Q1 2026.", "🏗️")
    cols = st.columns(4, gap="medium")
    icons = ["🆕", "🔑", "📚", "🎪"]
    for col, item, icon in zip(cols, S.SHARJAH_NEW_PROJECTS, icons):
        with col:
            val = item["value"]
            display = f"{val}" if isinstance(val, int) and item["unit"] == "projects" \
                else f"AED {val}B"
            st.markdown(
                f'<div class="uae-kpi teal">'
                f'<div class="uae-kpi-ic">{icon}</div>'
                f'<div class="uae-kpi-label">{item["metric"]}</div>'
                f'<div class="uae-kpi-value">{display}</div></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{item['unit']} · {item['period']}")
    ui.chart_note(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_regulatory() -> None:
    ui.section("Regulatory Landscape",
               "Sharjah-specific regulation, from Savills and Markaz.", "⚖️")
    for reg in S.SHARJAH_REGULATORY:
        with st.expander(f"⚖️  {reg['title']}"):
            st.markdown(f"**Period:** {reg['period']}")
            st.markdown(reg["summary"])
            st.markdown(f"**Market relevance.** {reg['impact']}")
            st.caption(f"Source: {reg['source']['citation']}")


def _section_infrastructure() -> None:
    ui.section("Infrastructure",
               "Sharjah-specific infrastructure programmes.", "🚆")
    cols = st.columns(len(S.SHARJAH_INFRASTRUCTURE), gap="large")
    for col, item in zip(cols, S.SHARJAH_INFRASTRUCTURE):
        with col:
            ui.block(item["title"], item["expected"], "▪")
            st.markdown(item["detail"])
            st.caption(f"Source: {item['source']['citation']}")


def _section_near_term() -> None:
    ui.section("Near-term Conditions",
               "Savills' Q1 2026 interpretation of the market.", "🌡️")
    for para in S.SHARJAH_NEAR_TERM:
        st.markdown(f"• {para}")
    st.info(
        f"**{S.SHARJAH_APRIL_POST_Q1['period']}.** {S.SHARJAH_APRIL_POST_Q1['value']}. "
        f"{S.SHARJAH_APRIL_POST_Q1['note']}",
        icon="📅",
    )
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_fundamentals() -> None:
    ui.section("Underlying Market Fundamentals",
               "Structural characteristics identified in the Savills report.", "🧱")
    for para in S.SHARJAH_FUNDAMENTALS:
        st.markdown(f"• {para}")

    ui.block("Supply pipeline — masterplan developments named in the source", "", "🏘️")
    chips = " ".join(
        f'<span class="uae-chip"><span class="dot"></span>{m["name"]}</span>'
        for m in S.SHARJAH_MASTERPLANS
    )
    st.markdown(
        f'<div style="display:flex;gap:.4rem;flex-wrap:wrap">{chips}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_outlook() -> None:
    ui.section("Outlook — Forward Signals",
               "The three forward signals Savills lists at the end of the Q1 2026 report.",
               "🔭")
    for sig in S.SHARJAH_FORWARD_SIGNALS:
        st.markdown(
            f'<div class="uae-insight"><span class="em">0{sig["number"]}</span>'
            f'<p>{sig["text"]}</p></div>',
            unsafe_allow_html=True,
        )
    st.caption(f"Source: {S.SAVILLS_Q1_2026['citation']}")


def _section_sources() -> None:
    ui.section("Sources & Provenance",
               "Every figure and quote on this page traces to one of these three reports.",
               "🗄️")
    for r in S.all_sources():
        st.markdown(f"**{r['publisher']}** — {r['title']}  ·  _{r['period']}_")
    with st.expander("📋  Per-section provenance"):
        rows = [[section, cite] for section, cite in S.source_index()]
        df = pd.DataFrame(rows, columns=["Section", "Source"])
        _fmt(df, {})


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD REPORT (in-page, mirrors Dubai's pattern)
# ─────────────────────────────────────────────────────────────────────────────


def _section_download_report() -> None:
    ui.section("Download detailed report",
               "A print-ready Sharjah PDF built from the same source registry as this page.",
               "📄")
    try:
        from platform_core import sharjah_report as builder
    except Exception as exc:  # pragma: no cover
        st.error(f"**The Sharjah report builder could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    if st.session_state.get("shj_report_pdf") is None:
        try:
            with st.spinner("Building the Sharjah report…"):
                st.session_state["shj_report_pdf"] = builder.build()
        except Exception as exc:  # pragma: no cover
            st.session_state.pop("shj_report_pdf", None)
            st.error(f"**The report could not be generated.**\n\n"
                     f"`{type(exc).__name__}: {exc}`", icon="⚠️")
            return

    pdf_bytes = st.session_state.get("shj_report_pdf")
    if not pdf_bytes:
        return

    fname = f"Sharjah_Market_Analytics_Report_{datetime.now():%Y%m%d}.pdf"
    st.download_button(
        "⬇️   Download the Sharjah report  ·  PDF",
        data=pdf_bytes, file_name=fname, mime="application/pdf",
        type="primary", use_container_width=True, key="shj_report_dl")
    st.caption(f"{fname} — {len(pdf_bytes) / 1024:,.0f} KB")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────────────────────


def render(dark: bool = False) -> None:
    """Render the whole Sharjah regional dashboard."""
    _section_overview()
    _section_key_stats()
    _section_monthly_dynamics()

    ui.divider_label("Analytics")

    tabs = st.tabs([
        "💰 Value", "🔢 Volume", "🌍 Investors", "🏠 Property Type",
        "🗺️ Top Areas", "📋 Notable", "🏗️ Projects", "⚖️ Regulation",
        "🚆 Infrastructure", "🌡️ Near-term", "🧱 Fundamentals", "🔭 Outlook",
        "🗄️ Sources", "📄 Report",
    ])

    with tabs[0]:  _section_transaction_value()
    with tabs[1]:  _section_transaction_volume()
    with tabs[2]:  _section_investors()
    with tabs[3]:  _section_property_type()
    with tabs[4]:  _section_top_areas()
    with tabs[5]:  _section_notable_transactions()
    with tabs[6]:  _section_new_projects()
    with tabs[7]:  _section_regulatory()
    with tabs[8]:  _section_infrastructure()
    with tabs[9]:  _section_near_term()
    with tabs[10]: _section_fundamentals()
    with tabs[11]: _section_outlook()
    with tabs[12]: _section_sources()
    with tabs[13]: _section_download_report()
