"""
Resident-memory governor for the shell.
════════════════════════════════════════════════════════════════════════════

WHY THIS EXISTS
---------------
Streamlit Cloud runs the whole platform inside ONE process. `st.cache_data`
entries are process-global, so a dataset loaded by one environment stays
resident after the visitor has moved on to another. Nothing releases it,
because from Streamlit's point of view the cache is still valid — and it is.
The cost is simply that the process ends up holding every environment the
visitor has ever opened, all at once.

Measured on a full walk of the rail, one process, before this module existed:

    baseline (interpreter only)                145 MB
    Overview                                   152 MB
    Dubai dashboard                            378 MB   (transient peak 831 MB)
    Area                                       399 MB
    Download Detailed Report                   467 MB
    Forecast                                   471 MB
    Abu Dhabi                                1,213 MB   ← +742 MB, never released
    Experimental Analysis                    1,270 MB
    session high-water mark                  1,334 MB

The Community Cloud free tier is about 1 GB. The process is killed somewhere
around the Abu Dhabi step and the visitor is shown "Oh no. Error running app."
The app is not broken; it ran out of room.

WHAT THIS DOES
--------------
Nothing to any environment's code, data, logic or output. It only decides WHEN
a cache may be released. Routes are grouped into families that share a dataset;
when a visitor leaves one family for another, the caches behind the family they
left are dropped, so the process holds ONE environment at a time instead of the
running total of every environment visited.

    dubai        Dubai dashboard · Area · Download Detailed Report · Forecast
    abu_dhabi    Abu Dhabi
    experimental Experimental Analysis
    (none)       Overview · Explore · About — these hold nothing worth releasing,
                 so passing through them never costs a reload

The only visible effect is that returning to an environment reloads its data,
which is the same few seconds the visitor paid the first time. Every number,
chart, filter and report is computed by exactly the same code from exactly the
same files as before; a cache is an optimisation, never a source of truth.

`st.cache_resource` is deliberately left alone. It holds objects that are
expensive or unsafe to rebuild — loaded models and the like — and it is not
what the measurement above is made of.
"""

from __future__ import annotations

import gc

import streamlit as st

from platform_core import config as C

# Routes that share a dataset. A route absent from this map is a light page:
# it holds nothing, so moving through it must not trigger a reload of whatever
# the visitor was looking at before.
FAMILY: dict[str, str] = {
    C.ROUTE_DUBAI: "dubai",
    C.ROUTE_AREA: "dubai",
    C.ROUTE_REPORT: "dubai",
    C.ROUTE_FORECAST: "dubai",
    C.ROUTE_ABU_DHABI: "abu_dhabi",
    C.ROUTE_EXPERIMENTAL: "experimental",
}

SS_FAMILY = "uae.mem_family"


def govern(route: str) -> None:
    """
    Called once per run, BEFORE the route renders.

    If this run belongs to a different data family than the last heavy route,
    release the previous family's cached frames first, so the incoming
    environment loads into a process that is not still holding the outgoing
    one. Called before rendering on purpose: clearing afterwards would free the
    data that had just been loaded.
    """
    family = FAMILY.get(route)
    if family is None:
        # Overview / Explore / About — no dataset of their own. Leave the
        # visitor's current environment cached so stepping onto an information
        # page and straight back is free.
        return

    previous = st.session_state.get(SS_FAMILY)
    if previous is not None and previous != family:
        release()

    st.session_state[SS_FAMILY] = family


def release() -> None:
    """Drop every `st.cache_data` entry and return the pages to the allocator."""
    try:
        st.cache_data.clear()
    except Exception:
        # A cache that cannot be cleared is not a reason to fail a page render.
        pass
    gc.collect()
