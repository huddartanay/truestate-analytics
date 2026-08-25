"""
🇦🇪 Dubai — the regional analytics dashboard.

Structurally equivalent to Abu Dhabi:

    Executive KPIs → Smart Business Insights → Market Snapshot
    ──────────────────── ANALYTICS ────────────────────
    Insights · Trends · Geography · Property · Price · Distribution

The Dubai experimental / version work is NOT part of this page. It lives in
🧪 Experimental Analysis.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from regions.dubai_market import dashboard as dxb


def render() -> None:
    region = C.REGIONS[C.ROUTE_DUBAI]
    dark = nav.is_dark()

    ui.breadcrumb("TruEstates Analytics", "Locations", "Dubai")
    ui.region_header(
        region,
        chips=["6 analytical sections", "Residential unit sales", "2010 – 2026"],
    )

    with st.expander("🧭  What am I looking at?", expanded=False):
        st.markdown(
            """
This is the **Dubai residential market dashboard**. It is built on the cleaned Dubai
transaction dataset — every residential *unit* sale registered in Dubai from 2010 onwards —
and every figure recomputes when you change a filter.

**How the page is laid out**

1. **Executive KPIs** — twelve headline numbers for whatever selection you have made.
2. **Smart Business Insights** — short observations the platform derives from that same
   selection. They change when the filters change.
3. **Market Snapshot** — the six figures you would quote in a meeting.
4. **Analytics** — six deeper sections: Insights, Trends, Geography, Property, Price and
   Distribution.

**Two terms worth knowing.** *Rate per m²* is the sale price divided by the unit's area — the
fairest way to compare a studio with a penthouse. *Median* is the midpoint: half of sales sit
above it, half below. It is more representative than the average, which a handful of very
large deals can pull upward.

Set your scope in the sidebar under **Dubai controls**. Leaving a filter empty means
"include everything".
            """
        )

    # The dashboard's own filters render below this divider in the rail.
    nav.region_controls_divider("Dubai controls")

    dxb.render(dark=dark)

    ui.footer(C.PLATFORM_VERSION, "Dubai · Real Estate Analytics")
