"""
Abu Dhabi region page.

Renders the platform banner, then hands over to the EXISTING Abu Dhabi
dashboard untouched (regions/abu_dhabi/app.py).
"""

from __future__ import annotations

import contextlib

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav
from platform_core import runtime


@contextlib.contextmanager
def _excel_writer_engine():
    """
    Serve the Download tab's Excel export from xlsxwriter instead of openpyxl,
    for the duration of the region's run only.

    WHY
    ---
    The Download tab builds the .xlsx eagerly on every render — Streamlit
    executes the body of every `st.tabs` tab, whether or not it is the one on
    screen — and openpyxl materialises a Python object for each of the
    1,854,649 cells before writing anything. Measured on this dataset:

        engine="openpyxl"     file 9.6 MB    +533 MB resident, 937 MB peak
        engine="xlsxwriter"   file 8.4 MB    +208 MB resident, 476 MB peak

    Whole Abu Dhabi page, cold process, peak resident memory:

        as written          1,217 MB     ← above the ~1 GB hosting limit
        with this shim        794 MB

    That gap is what was killing the hosted app: the process was terminated
    while building a workbook nobody had asked for yet, and the visitor was
    shown "Oh no. Error running app."

    IS THE FILE THE SAME?
    ---------------------
    Yes — verified, not assumed. Both workbooks were written and read back:
    same two sheets (Transactions, Summary), same shape (109,097 x 17), same
    column order, and `DataFrame.equals` True on both sheets — all 1,854,649
    cells identical. (xlsxwriter's `constant_memory` option is cheaper still
    but was REJECTED: it silently altered 1,737,178 cells. It is not used.)

    WHY IT IS DONE HERE AND NOT IN THE REGION
    -----------------------------------------
    `regions/abu_dhabi/` is to stay untouched, so nothing in it is edited. The
    swap is installed around the region's run and removed again in `finally`,
    so it cannot leak into the Dubai reports or anything else on the platform.
    """
    original = pd.ExcelWriter

    def writer(path_or_buffer, *args, **kwargs):
        if kwargs.get("engine") == "openpyxl":
            kwargs["engine"] = "xlsxwriter"
        return original(path_or_buffer, *args, **kwargs)

    try:
        pd.ExcelWriter = writer
        yield
    finally:
        pd.ExcelWriter = original


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

    with _excel_writer_engine():
        runtime.run_region(
            entry=C.ABU_DHABI_ENTRY,
            working_dir=C.ABU_DHABI_DIR,
            region_label="Abu Dhabi",
        )

    ui.footer(C.PLATFORM_VERSION, "Abu Dhabi · Real Estate Analytics")
