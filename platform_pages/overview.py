"""Landing / Overview page for the unified platform."""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from platform_core.navigation import _keyed


def render() -> None:
    ad = C.REGIONS[C.ROUTE_ABU_DHABI]
    dxb = C.REGIONS[C.ROUTE_DUBAI]
    exp = C.REGIONS[C.ROUTE_EXPERIMENTAL]

    # ── Brand + hero ─────────────────────────────────────────────────────────
    # The company mark leads the opening page, above the product title.
    ui.brand_mark(width=232, caption="Property intelligence, built on transaction records")

    ui.hero(
        eyebrow="🇦🇪 United Arab Emirates · Property Intelligence",
        title_html='Tru<span class="accent">Estate</span><br>Analytics',
        lede=(
            "One platform for the UAE property market. Abu Dhabi and Dubai each have a full "
            "regional dashboard — headline KPIs, automatic business insights and deep "
            "analytical sections — alongside a separate research environment holding the "
            "modelling experiments behind them."
        ),
    )

    ui.stat_strip(
        [
            ("2", "Regional dashboards"),
            ("18", "Analytical sections"),
            ("6", "Research experiments"),
            ("1", "Entry point"),
        ]
    )

    st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)

    # ── Region cards ─────────────────────────────────────────────────────────
    ui.section(
        "Choose a region",
        "Both dashboards are laid out the same way, so what you learn in one transfers to "
        "the other.",
        "🗺️",
    )

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        ui.region_card(ad, delay=1)
        with _keyed("uaecta-abu_dhabi"):
            if st.button("Explore Analytics  →", key="ov-go-ad", use_container_width=True):
                nav.goto(C.ROUTE_ABU_DHABI)

    with col_b:
        ui.region_card(dxb, delay=2)
        with _keyed("uaecta-dubai"):
            if st.button("Explore Analytics  →", key="ov-go-dxb", use_container_width=True):
                nav.goto(C.ROUTE_DUBAI)

    # ── Research environment ─────────────────────────────────────────────────
    ui.section(
        "Research environment",
        "Kept separate from the regional dashboards on purpose.",
        "🧪",
    )

    col_c, col_d = st.columns([1, 1], gap="large")
    with col_c:
        ui.region_card(exp, delay=3)
        with _keyed("uaecta-experimental"):
            if st.button("Open Experimental Analysis  →", key="ov-go-exp",
                         use_container_width=True):
                nav.goto(C.ROUTE_EXPERIMENTAL)
    with col_d:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        ui.note(
            "<b>Why is this separate?</b> The experiments were built over several generations, "
            "each on a different dataset or modelling approach. Their numbers reflect the data "
            "they were run on and will not always match the current regional dashboards. "
            "Keeping them apart means the regional views stay clean and the research stays "
            "reproducible.",
            icon="🧭",
        )
        for icon, label, desc in [
            ("📊", "Six generations", "V1, V2, V2.1, FC, Area Combination and V2.2 — all preserved"),
            ("🤖", "20 area models", "Saved decision-tree models with published metrics"),
            ("📈", "Forecasting", "SARIMA and LOWESS forecasts with accuracy reporting"),
        ]:
            ui.directory_row(icon, label, desc, accent=exp["accent"],
                             accent_soft=exp["accent_soft"])

    # ── What you can do ──────────────────────────────────────────────────────
    ui.section(
        "What the platform gives you",
        "The same four capabilities, applied to two different markets.",
        "◆",
    )

    tiles = [
        ("📊", "Market measurement",
         "Volumes, values, median prices and rate per square metre — filtered live and "
         "recomputed from the source transaction records."),
        ("🔬", "Statistical analysis",
         "Distributions, concentration, seasonality and year-over-year growth, with "
         "plain-English readings of every chart."),
        ("🏗️", "Property & location",
         "How layout, unit size, off-plan status, locality and amenities relate to what "
         "buyers actually pay."),
        ("📈", "Forecasting",
         "Published SARIMA / ARIMA forecasts with confidence bands and accuracy metrics, "
         "reported per area."),
    ]
    cols = st.columns(4, gap="medium")
    for i, (icon, title, text) in enumerate(tiles):
        with cols[i]:
            ui.tile(icon, title, text, delay=i + 1)

    # ── Orientation ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    ui.note(
        "<b>New here?</b> The left rail is the only navigation you need — pick an environment, "
        "and its own filters and views appear underneath it under <b>Region controls</b>. "
        "For a full map of every section, open <b>Explore Platform</b>.",
        icon="🧭",
    )

    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button("🧭  Open the platform map", key="ov-go-explore", use_container_width=True):
            nav.goto(C.ROUTE_EXPLORE)
    with c2:
        if st.button("ℹ️  About this platform", key="ov-go-about", use_container_width=True):
            nav.goto(C.ROUTE_ABOUT)

    ui.footer(C.PLATFORM_VERSION, "Overview")
