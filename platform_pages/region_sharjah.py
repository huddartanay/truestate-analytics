"""
🇦🇪 Sharjah — regional market intelligence, sourced entirely from three
published research reports.

The page is deliberately shaped like Dubai (breadcrumb → region header →
'What am I looking at?' expander → analytics), but its data model is
completely separate: nothing on this page comes from a live dataset, from
Dubai, from Abu Dhabi, or from any UAE-wide aggregate.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from regions.sharjah import dashboard as shj


def render() -> None:
    region = C.REGIONS[C.ROUTE_SHARJAH]
    dark = nav.is_dark()

    ui.breadcrumb("TruEstate Analytics", "Locations", "Sharjah")
    ui.region_header(
        region,
        chips=[
            "Q1 2026 · Savills",
            "Report-sourced",
            "3 source publications",
        ],
    )

    with st.expander("🧭  What am I looking at?", expanded=False):
        st.markdown(
            """
This is the **Sharjah regional market intelligence** view. Unlike the Dubai
dashboard, which is computed live from a transaction dataset, every figure and
every quote on this page is drawn from three published research reports:

1. **Savills** — *Sharjah Residential Market — Market in Minutes, Q1 2026* — the
   primary source, dedicated to Sharjah.
2. **Marmore / Markaz** — *UAE Real Estate Report, H1 2024 Review and H2 2024
   Outlook* — the Sharjah-specific item on page 22 (SRERD × UAE Pass).
3. **Marmore / Markaz** — *UAE Real Estate Report, H2 2024 Review and H1 2025
   Outlook* — the Sharjah-specific item on page 24 (Sharjah Law No. 5 of 2024
   on Property Leasing).

Nothing else is used. No Dubai figure has been carried over, no Abu Dhabi
figure has been inferred, and no UAE-wide value has been re-presented as a
Sharjah value. Where a report chart has visual bars without explicit numeric
labels, the underlying values are **not** reverse-engineered from pixels —
only values the reports state numerically are shown.
            """
        )

    shj.render(dark=dark)

    ui.footer(C.PLATFORM_VERSION, "Sharjah · Real Estate Analytics")
