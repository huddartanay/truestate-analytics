"""
RAK — regional market intelligence tab.

Sourced entirely from three RAK Statistics Office / Lands & Properties Sector
reports. Uses Dubai's design language as the visual reference, but its data
model is separate: no Dubai, Sharjah, Abu Dhabi or other-emirate value is
carried into it.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from regions.rak import dashboard as rak


def render() -> None:
    region = C.REGIONS[C.ROUTE_RAK]
    dark = nav.is_dark()

    ui.breadcrumb("TruEstate Analytics", "Locations", "RAK")
    ui.region_header(
        region,
        chips=[
            "2025 · RAK Statistics Office",
            "Report-sourced",
            "Annual + monthly",
        ],
    )

    with st.expander("🧭  What am I looking at?", expanded=False):
        st.markdown(
            """
This is the **Ras Al Khaimah** regional tab. Every figure and every table on
this page is drawn from three official reports published by the RAK Statistics
Office (Lands & Properties Sector):

1. **RAK Annual 2024–2025** — the primary source for 2025 headline figures,
   the popular-areas ranking, the property-use table and the investor tables.
2. **RAK Annual 2020–2021** — historical context: the same categories reported
   four years earlier.
3. **RAK Monthly — January 2026** — the most recent monthly transaction report.

Nothing else is used. No Dubai, Sharjah or other-emirate value has been
carried in, nothing is inferred from a UAE-wide aggregate, and no metric that
is not explicitly present in the reports is invented.
            """
        )

    rak.render(dark=dark)

    ui.footer(C.PLATFORM_VERSION, "RAK · Real Estate Analytics")
