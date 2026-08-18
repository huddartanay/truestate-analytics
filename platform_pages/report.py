"""
📄 Download Detailed Report — the download actions, and nothing else.

This page is deliberately not an analysis page. It offers the reports and gets
out of the way:

    Dubai      Area-wise · Forecast · Both, for the global 📍 Area
    Abu Dhabi  Area-wise, for a district of that dataset

The forecast's own explanation, inputs and chart live on the 🔮 Forecast page,
which is where they belong. This page only *packages* what the forecast already
produced: it reads the response already held in session state and never issues a
request of its own.

THE AREA RULE
─────────────
Dubai's reports follow the global 📍 Area. There is no second Dubai area control
here. Abu Dhabi has no global area in the shell — its districts live only inside
that region's own dataset — so its district picker on this page is the first one,
not a duplicate.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav

# Session keys for prepared documents. Each is stored with the signature that
# produced it, so a document can never be offered for a different area.
K_AREA_PDF = "uae.rep_area_pdf"
K_AREA_SIG = "uae.rep_area_sig"
K_FC_PDF = "uae.rep_fc_pdf"
K_FC_SIG = "uae.rep_fc_sig"
K_BOTH_PDF = "uae.rep_both_pdf"
K_BOTH_SIG = "uae.rep_both_sig"
K_AD_PDF = "uae.rep_ad_pdf"
K_AD_SIG = "uae.rep_ad_sig"

# Written by the Forecast page when a forecast is fetched.
FC_RESULT = "dxb_fc_result"
FC_INPUTS = "dxb_fc_inputs"
FC_AREA = "dxb_fc_area"


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))


def _get(key):
    try:
        return st.session_state[key]
    except (KeyError, AttributeError):
        return None


def _offer(pdf: bytes, filename: str, label: str, key: str) -> None:
    st.download_button(label, data=pdf, file_name=filename, mime="application/pdf",
                       type="primary", use_container_width=True, key=key)
    st.caption(f"{filename} — {len(pdf) / 1024:,.0f} KB")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────


def render() -> None:
    ui.breadcrumb("TruEstate Analytics", "Download Detailed Report")

    area = nav.area()

    st.markdown(
        '<div class="uae-card uae-d1" style="margin-bottom:1.1rem">'
        '<p class="uae-h3">📄 Download detailed report</p>'
        '<p class="uae-sub" style="max-width:96ch">Print-ready PDFs, built from the live '
        'data at the moment you ask for them. Dubai\'s reports follow whatever is selected '
        'under 📍 Area; Abu Dhabi\'s follows the district chosen below.</p></div>',
        unsafe_allow_html=True,
    )

    _dubai_block(area)
    st.markdown("---")
    _abu_dhabi_block()

    ui.footer(C.PLATFORM_VERSION, f"Download Detailed Report · {area}")


# ─────────────────────────────────────────────────────────────────────────────
# DUBAI
# ─────────────────────────────────────────────────────────────────────────────


def _dubai_block(area: str) -> None:
    ui.section("Dubai", "Reports for the area selected under 📍 Area.", "🇦🇪")

    try:
        from regions.dubai_market.data import COL, DubaiDataError, load_market
    except Exception as exc:  # pragma: no cover
        st.error("**The Dubai module could not be loaded, so its reports are "
                 f"unavailable.**\n\n`{type(exc).__name__}: {exc}`", icon="⚠️")
        return

    try:
        with st.spinner("Loading Dubai market data…"):
            df_all = load_market()
    except (DubaiDataError, FileNotFoundError) as exc:
        st.error(f"**Dubai market data could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    df = df_all if area == C.ALL_AREAS else df_all[df_all[COL["area"]] == area]

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected area", area)
    c2.metric("Transactions covered", f"{len(df):,}")
    c3.metric("Share of Dubai", f"{len(df) / max(len(df_all), 1) * 100:.1f}%")

    if df.empty:
        st.warning(f"No transactions are recorded in **{area}**, so there is nothing to "
                   f"report. Choose another area under 📍 **Area**.", icon="🔍")
        return

    st.caption("Change the area under 📍 **Area** and every report below follows it.")

    # The forecast that the 🔮 Forecast page produced, if there is one for this area.
    fc_result = _get(FC_RESULT)
    fc_inputs = _get(FC_INPUTS) or {}
    fc_ready = fc_result is not None and _get(FC_AREA) == area
    fc_news = bool(fc_inputs.get("news_available", True))

    stamp = f"{datetime.now():%Y%m%d}"
    a, b, c = st.columns(3, gap="large")

    # ── A. Area-wise ────────────────────────────────────────────────────────
    with a:
        st.markdown("**Area-wise report**")
        st.caption("Transaction activity, price levels, layout, building height, "
                   "amenities, registration type and price brackets.")
        if st.button("Prepare area-wise report", use_container_width=True,
                     key="rep_prep_area"):
            _prepare_area(df, area, len(df_all))
        sig = (area, len(df))
        if _get(K_AREA_SIG) == sig and _get(K_AREA_PDF):
            _offer(_get(K_AREA_PDF), f"Dubai_Area_Report_{_safe(area)}_{stamp}.pdf",
                   "⬇️  Download area-wise report", "rep_dl_area")

    # ── B. Forecast ─────────────────────────────────────────────────────────
    with b:
        st.markdown("**Forecast report**")
        st.caption("The valuation point, the months ahead, and the market narrative "
                   "when it is switched on.")
        if not fc_ready:
            st.info(f"Run a forecast for **{area}** on the 🔮 **Forecast** page first — "
                    f"this report packages that result rather than requesting a new one.",
                    icon="🔮")
        else:
            if st.button("Prepare forecast report", use_container_width=True,
                         key="rep_prep_fc"):
                _prepare_forecast(fc_result, area, fc_inputs, fc_news)
            sig = (area, fc_news, id(fc_result))
            if _get(K_FC_SIG) == sig and _get(K_FC_PDF):
                _offer(_get(K_FC_PDF), f"Dubai_Forecast_Report_{_safe(area)}_{stamp}.pdf",
                       "⬇️  Download forecast report", "rep_dl_fc")

    # ── C. Both ─────────────────────────────────────────────────────────────
    with c:
        st.markdown("**Both, in one PDF**")
        st.caption("Section 1 the recorded market, Section 2 the forecast — one document, "
                   "one download, the same area throughout.")
        if not fc_ready:
            st.info("Available once a forecast has been run for this area.", icon="🔮")
        else:
            if st.button("Prepare combined report", use_container_width=True,
                         key="rep_prep_both"):
                _prepare_both(df, area, len(df_all), fc_result, fc_inputs, fc_news)
            sig = (area, len(df), fc_news, id(fc_result))
            if _get(K_BOTH_SIG) == sig and _get(K_BOTH_PDF):
                _offer(_get(K_BOTH_PDF), f"Dubai_Full_Report_{_safe(area)}_{stamp}.pdf",
                       "⬇️  Download both", "rep_dl_both")

    if fc_ready:
        st.caption(
            f"The forecast reports use the result currently on the 🔮 Forecast page, "
            f"with the news-adjusted series **{'included' if fc_news else 'excluded'}** — "
            f"the state of that page's toggle. The API is not called again to build them.")


def _prepare_area(df, area, all_rows) -> None:
    try:
        from platform_core import dubai_report as builder
        with st.spinner(f"Building the {area} area report…"):
            st.session_state[K_AREA_PDF] = builder.build(df, area, all_rows)
        st.session_state[K_AREA_SIG] = (area, len(df))
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        st.session_state.pop(K_AREA_PDF, None)
        st.session_state.pop(K_AREA_SIG, None)
        st.error(f"**The area-wise report could not be built.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")


def _prepare_forecast(result, area, inputs, show_news) -> None:
    try:
        from platform_core import forecast_report as builder
        with st.spinner(f"Building the {area} forecast report…"):
            st.session_state[K_FC_PDF] = builder.build(
                result, area, inputs, show_news=show_news)
        st.session_state[K_FC_SIG] = (area, show_news, id(result))
    except Exception as exc:  # pragma: no cover
        st.session_state.pop(K_FC_PDF, None)
        st.session_state.pop(K_FC_SIG, None)
        st.error(f"**The forecast report could not be built.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")


def _prepare_both(df, area, all_rows, result, inputs, show_news) -> None:
    try:
        from platform_core import combined_report as builder
        with st.spinner(f"Building the combined {area} report…"):
            st.session_state[K_BOTH_PDF] = builder.build(
                df, area, all_rows, result, inputs, show_news=show_news)
        st.session_state[K_BOTH_SIG] = (area, len(df), show_news, id(result))
    except Exception as exc:  # pragma: no cover
        st.session_state.pop(K_BOTH_PDF, None)
        st.session_state.pop(K_BOTH_SIG, None)
        st.error(f"**The combined report could not be built.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")


# ─────────────────────────────────────────────────────────────────────────────
# ABU DHABI
# ─────────────────────────────────────────────────────────────────────────────


def _abu_dhabi_block() -> None:
    ui.section("Abu Dhabi", "An area-wise report for a district of the Abu Dhabi "
                            "apartment dataset.", "🇦🇪")

    try:
        from platform_core import abu_dhabi_report as adr
    except Exception as exc:  # pragma: no cover
        st.error("**The Abu Dhabi report module could not be loaded.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")
        return

    try:
        with st.spinner("Loading Abu Dhabi data…"):
            df, cols = adr.load_clean()
    except adr.AbuDhabiReportError as exc:
        st.error(f"**{exc}**", icon="⚠️")
        return

    options = [adr.ALL_AREAS] + adr.districts(df)
    counts = df[adr.AREA_COL].astype(str).value_counts()
    labels = {adr.ALL_AREAS: f"{adr.ALL_AREAS}  ({len(df):,} transactions)"}
    labels.update({d: f"{str(d).title()}  ({int(counts.get(d, 0)):,})"
                   for d in options[1:]})

    left, right = st.columns([3, 2], gap="large")
    with left:
        district = st.selectbox(
            "🏙️  District — applies to the Abu Dhabi report",
            options, index=0, format_func=lambda d: labels.get(d, str(d).title()),
            key="rep_ad_district",
            help="Abu Dhabi's districts come from its own dataset. The Dubai 📍 Area "
                 "setting does not apply here — the two regions have separate records.")
    with right:
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        rows = len(df) if district == adr.ALL_AREAS else int(counts.get(district, 0))
        st.caption(f"**{rows:,}** recorded apartment sales in this selection.")

    if st.button("Prepare Abu Dhabi area-wise report", use_container_width=True,
                 key="rep_prep_ad"):
        try:
            with st.spinner(f"Building the {str(district).title()} report…"):
                st.session_state[K_AD_PDF] = adr.build(district)
            st.session_state[K_AD_SIG] = district
        except adr.AbuDhabiReportError as exc:
            st.session_state.pop(K_AD_PDF, None)
            st.session_state.pop(K_AD_SIG, None)
            st.warning(f"**{exc}**", icon="🔍")
        except Exception as exc:  # pragma: no cover
            st.session_state.pop(K_AD_PDF, None)
            st.session_state.pop(K_AD_SIG, None)
            st.error(f"**The Abu Dhabi report could not be built.**\n\n"
                     f"`{type(exc).__name__}: {exc}`", icon="⚠️")

    if _get(K_AD_SIG) == district and _get(K_AD_PDF):
        _offer(_get(K_AD_PDF),
               f"AbuDhabi_Area_Report_{_safe(str(district).title())}_"
               f"{datetime.now():%Y%m%d}.pdf",
               "⬇️  Download Abu Dhabi area-wise report", "rep_dl_ad")
