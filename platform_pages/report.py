"""
📄 Download Detailed Report — generate and download the Dubai analytics PDF.

The report is built from the SAME dataframe the Dubai dashboard is showing:
the same cleaned dataset, the same global area, and the same metric functions.
Nothing is hard-coded and nothing is re-derived by a second method, so the PDF
cannot disagree with the screen.

It is not a screenshot of the dashboard. Every page is composed for print —
title page, executive summary, analytical sections, tables and charts drawn at
print resolution, page borders, running headers and page numbers.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav


def render() -> None:
    ui.breadcrumb("TruEstate Analytics", "Download Detailed Report")

    area = nav.area()
    st.markdown(
        '<div class="uae-card uae-d1" style="margin-bottom:1.1rem">'
        '<p class="uae-h3">📄 Detailed analytics report</p>'
        '<p class="uae-sub" style="max-width:96ch">A print-ready PDF built from the live '
        'Dubai data — title page, executive summary, key findings, analytical sections with '
        'charts and tables, and a methodology section covering sources and scope. '
        'The report is prepared for whichever area is selected under 📍 Area, and every '
        'figure is computed at that moment — none is stored or hard-coded.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    try:
        from regions.dubai_market.data import COL, DubaiDataError, load_market
    except Exception as exc:  # pragma: no cover
        st.error(f"**Dubai module could not be imported.**\n\n{exc}", icon="⚠️")
        return

    try:
        with st.spinner("Loading Dubai market data…"):
            df_all = load_market()
    except (DubaiDataError, FileNotFoundError) as exc:
        st.error(f"**Dubai market data could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    # The report honours the same global area the dashboard uses.
    df = df_all if area == C.ALL_AREAS else df_all[df_all[COL["area"]] == area]

    if df.empty:
        st.warning(f"No transactions recorded in **{area}**, so there is nothing to report. "
                   f"Choose a different area under 📍 **Area**.", icon="🔍")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Area context", area)
    c2.metric("Transactions in report", f"{len(df):,}")
    c3.metric("Share of dataset", f"{len(df) / max(len(df_all), 1) * 100:.1f}%")

    if area == C.ALL_AREAS:
        st.info("This report covers **all Dubai areas**. For an area-specific report, pick "
                "an area under 📍 **Area** in the rail — the report follows that selection "
                "and rebuilds itself.", icon="📍")
    else:
        st.info(f"This report covers **{area}** only, because that is the area selected "
                f"under 📍 **Area**. Reset it there for a Dubai-wide report.", icon="📍")

    from platform_core import dubai_report as builder

    # ── the report builds itself ─────────────────────────────────────────────
    # It is generated as soon as this page opens, and again whenever the area
    # or the chosen sections change, so the Download button is simply there.
    # Making the user press "Generate" first only hid the thing they came for.
    default_sections = list(builder.ALL_SECTIONS)
    chosen = st.session_state.get("uae.report_sections", default_sections)
    signature = (area, tuple(chosen), len(df))

    if st.session_state.get("uae.report_sig") != signature:
        try:
            with st.spinner(f"Preparing the {area} report — computing figures and drawing "
                            f"charts…"):
                st.session_state["uae.report_pdf"] = builder.build(
                    df, area, len(df_all), sections=chosen)
            st.session_state["uae.report_sig"] = signature
            st.session_state["uae.report_area"] = area
            st.session_state["uae.report_rows"] = len(df)
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            st.session_state.pop("uae.report_pdf", None)
            st.session_state.pop("uae.report_sig", None)
            st.error(f"**The report could not be generated.**\n\n"
                     f"`{type(exc).__name__}: {exc}`", icon="⚠️")
            st.exception(exc)
            return

    pdf_bytes = st.session_state.get("uae.report_pdf")
    if pdf_bytes:
        rows = st.session_state.get("uae.report_rows", len(df))
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in area)
        from datetime import datetime
        fname = f"Dubai_Analytics_Report_{safe}_{datetime.now():%Y%m%d}.pdf"

        st.markdown("")
        st.download_button(
            f"⬇️   Download the {area} report  ·  PDF",
            data=pdf_bytes, file_name=fname, mime="application/pdf",
            type="primary", use_container_width=True)
        st.caption(
            f"**{fname}** — {len(pdf_bytes) / 1024:,.0f} KB, covering {rows:,} transactions "
            f"for {area}. Change the area under 📍 **Area** and this report rebuilds itself "
            f"for that area automatically."
        )

    st.markdown("---")
    with st.expander("⚙️  Choose which sections to include", expanded=False):
        picked: list[str] = []
        cols = st.columns(3)
        for i, key in enumerate(builder.ALL_SECTIONS):
            with cols[i % 3]:
                locked = key in ("summary", "method")
                on = st.checkbox(
                    builder.SECTION_LABELS[key], value=key in chosen,
                    key=f"rep_sec_{key}", disabled=locked,
                    help="Always included." if locked else None)
                if on or locked:
                    picked.append(key)
        st.caption("The executive summary and the methodology section are always "
                   "included, so every report carries its headline figures and its "
                   "sourcing.")
        if picked != chosen:
            st.session_state["uae.report_sections"] = picked
            st.rerun()

    with st.expander("📐  What is in the report, and how it is built"):
        st.markdown(
            "**Structure.** Title page with the reporting period, data coverage, area "
            "context and generation time; executive summary with headline figures and key "
            "findings; then one section per analysis, each with its chart, its table and a "
            "caption stating what the numbers do and do not mean; and a closing methodology "
            "section covering data sources, how the selection was formed, and the "
            "assumptions and limitations.\n\n"
            "**Where the numbers come from.** The report calls the same metric functions as "
            "the dashboard, on the same dataframe, with the same global area applied. There "
            "is no second calculation path that could drift from what you see on screen.\n\n"
            "**The charts.** Drawn for print from the same computed frames that feed the "
            "on-screen charts — vector renderings of identical numbers, not screenshots of "
            "the interface, so labels and axes stay sharp at any zoom.\n\n"
            "**Page design.** A4 portrait, a hairline border on every page, running header, "
            "page numbers, repeating table headers across page breaks, and no font shrunk "
            "to force a table to fit — a long table breaks across pages instead."
        )

    # ── Forecast ────────────────────────────────────────────────────────────
    # The same subsection the Dubai dashboard's Download Report tab carries,
    # reading the same global Area read-only. One implementation, two places —
    # so the two can never diverge, and neither adds a second area control.
    st.markdown("---")
    try:
        from regions.dubai_market import forecast_ui
        forecast_ui.render(area, df_area=df,
                           dark=bool(st.session_state.get(C.SS_THEME_DARK, False)))
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        st.error(f"**The forecast section could not be loaded.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")

    ui.footer(C.PLATFORM_VERSION, f"Download Detailed Report · {area}")
