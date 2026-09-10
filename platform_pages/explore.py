"""
Explore Platform — the orientation page.

Answers four questions: where am I, what am I looking at, what else exists,
and how do I get there.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav


def render() -> None:
    ad = C.REGIONS[C.ROUTE_ABU_DHABI]
    dxb = C.REGIONS[C.ROUTE_DUBAI]
    shj = C.REGIONS[C.ROUTE_SHARJAH]
    rak = C.REGIONS[C.ROUTE_RAK]
    exp = C.REGIONS[C.ROUTE_EXPERIMENTAL]

    ui.breadcrumb("TruEstates analytics", "Explore Platform")

    ui.hero(
        eyebrow="🧭 Orientation",
        title_html='Explore the <span class="accent">platform</span>',
        lede=(
            "Four regional experiences and one research environment, each with a clear role. "
            "This page is the map: everything that exists, what it does, and a direct route "
            "to it."
        ),
    )

    # ── Tree ─────────────────────────────────────────────────────────────────
    ui.section("Platform structure", "How the four regional experiences and research environment fit together.", "🗂️")

    ui.platform_map(
        branches=[
            {
                "title": f"{ad['flag']} Abu Dhabi",
                "subtitle": "Regional dashboard · 12 tabs",
                "accent": ad["accent"], "soft": ad["accent_soft"],
                "leaves": [("", f"{i}  {n}") for i, n, _ in C.ABU_DHABI_TABS],
            },
            {
                "title": f"{dxb['flag']} Dubai",
                "subtitle": "Regional dashboard · 3 summary + 6 sections",
                "accent": dxb["accent"], "soft": dxb["accent_soft"],
                "leaves": (
                    [("KPI", f"{i}  {n}") for i, n, _ in C.DUBAI_SUMMARY_BLOCKS]
                    + [("", f"{i}  {n}") for i, n, _ in C.DUBAI_SECTIONS]
                ),
            },
            {
                "title": f"{shj['flag']} Sharjah",
                "subtitle": "Report-sourced regional intelligence · 14 sections",
                "accent": shj["accent"], "soft": shj["accent_soft"],
                "leaves": [(badge, label) for badge, label in [
                    ("", "Overview"), ("", "Key Stats"), ("", "Monthly Dynamics"),
                    ("", "Transaction Value"), ("", "Transaction Volume"),
                    ("", "Investors"), ("", "Property Type"), ("", "Top Areas"),
                    ("", "Notable Transactions"), ("", "New Projects"),
                    ("", "Regulation"), ("", "Infrastructure"), ("", "Outlook"),
                    ("", "Sources & Report"),
                ]],
            },
            {
                "title": f"{rak['flag']} Ras Al Khaimah / RAK",
                "subtitle": "Report-sourced regional intelligence · 6 sections",
                "accent": rak["accent"], "soft": rak["accent_soft"],
                "leaves": [("", label) for label in [
                    "Overview", "Annual Transactions", "Popular Areas",
                    "Property Use", "Investors", "Monthly Time Series & Report",
                ]],
            },
            {
                "title": f"{exp['flag']} Experimental",
                "subtitle": "Research · 6 generations",
                "accent": exp["accent"], "soft": exp["accent_soft"],
                "leaves": [(e["short"], f"{e['icon']}  {e['label'].split('· ')[-1]}")
                           for e in C.EXPERIMENTS],
            },
        ]
    )

    ui.note(
        "The <b>regional experiences</b> answer \"what is happening in each market?\". "
        "The <b>research environment</b> holds the modelling work behind the platform and is "
        "kept separate so its older figures never get mistaken for the current market view.",
        icon="🧭",
    )

    # ── Abu Dhabi directory ──────────────────────────────────────────────────
    ui.section(
        f"{ad['flag']} Abu Dhabi — 12 analytical tabs",
        "One dashboard, filtered globally from the sidebar. Every tab reads the same "
        "filtered dataset.",
        "🏙️",
    )

    left, right = st.columns(2, gap="large")
    for i, (icon, name, desc) in enumerate(C.ABU_DHABI_TABS):
        with (left if i % 2 == 0 else right):
            ui.directory_row(icon, name, desc, accent=ad["accent"],
                             accent_soft=ad["accent_soft"], delay=(i // 2) + 1)

    if st.button("🇦🇪  Open Abu Dhabi Analytics  →", key="ex-go-ad"):
        nav.goto(C.ROUTE_ABU_DHABI)

    # ── Dubai directory ──────────────────────────────────────────────────────
    ui.section(
        f"{dxb['flag']} Dubai — summary, then six sections",
        "Same shape as Abu Dhabi: three summary blocks at the top of the page, then six "
        "analytical sections as tabs.",
        "🌇",
    )

    st.markdown("**On landing**")
    l2, r2 = st.columns(2, gap="large")
    for i, (icon, name, desc) in enumerate(C.DUBAI_SUMMARY_BLOCKS):
        with (l2 if i % 2 == 0 else r2):
            ui.directory_row(icon, name, desc, badge="SUMMARY", accent=dxb["accent"],
                             accent_soft=dxb["accent_soft"], delay=(i // 2) + 1)

    st.markdown("**Analytical sections**")
    l3, r3 = st.columns(2, gap="large")
    for i, (icon, name, desc) in enumerate(C.DUBAI_SECTIONS):
        with (l3 if i % 2 == 0 else r3):
            ui.directory_row(icon, name, desc, accent=dxb["accent"],
                             accent_soft=dxb["accent_soft"], delay=(i // 2) + 1)

    if st.button("🇦🇪  Open Dubai Analytics  →", key="ex-go-dxb"):
        nav.goto(C.ROUTE_DUBAI)

    # ── Sharjah directory ───────────────────────────────────────────────────
    ui.section(
        f"{shj['flag']} Sharjah — report-sourced intelligence",
        "A 14-section regional view built from the published Sharjah source set.",
        "🏙️",
    )
    shj_sections = [
        ("📊", "Key Stats", "Q1 2026 headline figures reported by Savills"),
        ("📈", "Market Dynamics", "Monthly, value and volume reference points"),
        ("🌍", "Investors & Property", "Nationality and residential property mix"),
        ("🗺️", "Areas & Transactions", "Top areas and notable reported deals"),
        ("🏗️", "Projects & Infrastructure", "New registrations and named programmes"),
        ("⚖️", "Regulation & Outlook", "Market rules and forward signals"),
        ("📄", "Sources & Report", "Provenance and downloadable regional report"),
    ]
    shj_left, shj_right = st.columns(2, gap="large")
    for i, (icon, name, desc) in enumerate(shj_sections):
        with (shj_left if i % 2 == 0 else shj_right):
            ui.directory_row(icon, name, desc, accent=shj["accent"],
                             accent_soft=shj["accent_soft"], delay=(i // 2) + 1)
    if st.button("🇦🇪  Open Sharjah Analytics  →", key="ex-go-sharjah"):
        nav.goto(C.ROUTE_SHARJAH)

    # ── RAK directory ───────────────────────────────────────────────────────
    ui.section(
        f"{rak['flag']} Ras Al Khaimah / RAK — report-sourced intelligence",
        "A six-section regional view built from the current RAK report set.",
        "🏙️",
    )
    rak_sections = [
        ("📊", "Overview", "2025 annual snapshot and key statistics"),
        ("📈", "Transactions", "Annual comparisons and monthly time series"),
        ("🗺️", "Popular Areas", "Reported area rankings by sales value"),
        ("🏠", "Property Use", "Land and property-use breakdowns"),
        ("🌍", "Investors", "Top nationalities by value and number"),
        ("📄", "Latest Month & Report", "January 2026 view and downloadable report"),
    ]
    rak_left, rak_right = st.columns(2, gap="large")
    for i, (icon, name, desc) in enumerate(rak_sections):
        with (rak_left if i % 2 == 0 else rak_right):
            ui.directory_row(icon, name, desc, accent=rak["accent"],
                             accent_soft=rak["accent_soft"], delay=(i // 2) + 1)
    if st.button("🇦🇪  Open RAK Analytics  →", key="ex-go-rak"):
        nav.goto(C.ROUTE_RAK)

    # ── Experimental directory ───────────────────────────────────────────────
    ui.section(
        f"{exp['flag']} Experimental Analysis — 6 generations",
        "Each generation is a self-contained study with its own views, preserved exactly as "
        "it was built.",
        "🧪",
    )

    ui.note(
        "Nothing here was merged or recalculated. The badge shows the original generation "
        "label used in the project.",
        icon="📎",
    )

    for i, e in enumerate(C.EXPERIMENTS):
        row, btn = st.columns([5, 1], vertical_alignment="center")
        with row:
            views = " · ".join(e["views"])
            ui.directory_row(
                e["icon"], e["label"],
                f"{e['detail']}<br><span style='opacity:.75'>Views: {views}</span>",
                badge=e["short"], accent=exp["accent"], accent_soft=exp["accent_soft"],
                delay=i + 1,
            )
        with btn:
            if st.button("Open →", key=f"ex-exp-{e['id']}", use_container_width=True):
                nav.goto(C.ROUTE_EXPERIMENTAL, experiment=e["id"])

    ui.footer(C.PLATFORM_VERSION, "Explore Platform")
