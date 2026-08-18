"""
Abu Dhabi region page.

Renders the platform banner, then hands over to the EXISTING Abu Dhabi
dashboard untouched (regions/abu_dhabi/app.py).
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from platform_core import runtime


def render() -> None:
    region = C.REGIONS[C.ROUTE_ABU_DHABI]

    ui.breadcrumb("TruEstate Analytics", "Locations", "Abu Dhabi")
    ui.region_header(
        region,
        chips=["12 analytical tabs", "Live filters", "Abu Dhabi DMT data"],
    )

    with st.expander("🧭  What am I looking at?", expanded=False):
        st.markdown(
            """
This is the **Abu Dhabi transaction dashboard**. Everything on this page is computed live from
the official Abu Dhabi sales records, and re-computed whenever you change a filter.

**How to use it**

1. Set your scope in the sidebar under **Region controls** — dataset (all properties or
   residential apartments only), years, property type and layout, district, transaction type,
   and price / area ranges.
2. The KPI band at the top always reflects the current filter selection.
3. Each tab below answers one question — trends over time, where transactions happen, what is
   being sold, how prices are distributed, how variables relate, and how clean the data is.

**Two terms worth knowing.** *Rate (AED per SQM)* is price divided by area — the fairest
like-for-like comparison between properties of different sizes. *Median* is the midpoint
(half of sales sit above it, half below) and is more representative than the average, which a
handful of luxury deals can pull upward.
            """
        )

    # The region's own sidebar widgets appear below this divider.
    nav.region_controls_divider("Abu Dhabi controls")

    runtime.run_region(
        entry=C.ABU_DHABI_ENTRY,
        working_dir=C.ABU_DHABI_DIR,
        region_label="Abu Dhabi",
    )

    ui.footer(C.PLATFORM_VERSION, "Abu Dhabi · Real Estate Analytics")
