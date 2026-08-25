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
    exp = C.REGIONS[C.ROUTE_EXPERIMENTAL]

    ui.breadcrumb("TruEstates analytics", "Explore Platform")

    ui.hero(
        eyebrow="🧭 Orientation",
        title_html='Explore the <span class="accent">platform</span>',
        lede=(
            "Three environments, each with a lot inside it. This page is the map: everything "
            "that exists, what it does, and a direct route to it."
        ),
    )

    # ── Tree ─────────────────────────────────────────────────────────────────
    ui.section("Platform structure", "How the three environments fit together.", "🗂️")

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
                "title": f"{exp['flag']} Experimental",
                "subtitle": "Research · 6 generations",
                "accent": exp["accent"], "soft": exp["accent_soft"],
                "leaves": [(e["short"], f"{e['icon']}  {e['label'].split('· ')[-1]}")
                           for e in C.EXPERIMENTS],
            },
        ]
    )

    ui.note(
        "The two <b>regional dashboards</b> answer \"what is the market doing?\". The "
        "<b>research environment</b> holds the modelling work behind them and is kept "
        "separate so its older figures never get mistaken for the current market view.",
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
