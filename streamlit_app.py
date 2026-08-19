"""
TRUESTATE ANALYTICS — unified platform entry point.
════════════════════════════════════════════════════════════════════════════

    streamlit run streamlit_app.py

This is the ONLY application in the repository. It owns:

    · the single global st.set_page_config()
    · the global design system
    · the global sidebar navigation
    · page routing

The two regional dashboards keep their own code, data and analytical logic
and are executed behind this shell (see platform_core/runtime.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_core import config as C  # noqa: E402
from platform_core import design_system as ds  # noqa: E402
from platform_core import memory as mem  # noqa: E402
from platform_core import navigation as nav  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# 1. GLOBAL PAGE CONFIGURATION — must be the first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(**C.PAGE_CONFIG)

# ─────────────────────────────────────────────────────────────────────────────
# 2. STATE + GLOBAL DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

nav.init_state()
DARK = nav.is_dark()

st.markdown(ds.build_platform_css(dark=DARK), unsafe_allow_html=True)

# The shell lock is emitted twice, on purpose:
#   · here, so the navigation rail is fully styled from the first paint and
#     never flashes unstyled while a slow region is still loading;
#   · again at the end of the run (see the `finally` block), so it also wins on
#     ordering against any stylesheet a region injects during its own run.
st.markdown(ds.build_shell_lock_css(dark=DARK), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. GLOBAL NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

route = nav.render_sidebar()

# ─────────────────────────────────────────────────────────────────────────────
# 4. ROUTING
#    Regions are imported lazily so that opening the Overview page never pays
#    the cost of touching a regional module.
#
#    The memory governor runs first, before anything is rendered. If this run
#    belongs to a different environment than the last heavy one, it releases
#    the outgoing environment's cached frames so the incoming one does not load
#    on top of them. See platform_core/memory.py for the measurements behind it.
# ─────────────────────────────────────────────────────────────────────────────

mem.govern(route)

try:
    if route == C.ROUTE_ABU_DHABI:
        from platform_pages import region_abu_dhabi

        region_abu_dhabi.render()

    elif route == C.ROUTE_DUBAI:
        from platform_pages import region_dubai

        region_dubai.render()

    elif route == C.ROUTE_AREA:
        from platform_pages import area as area_page

        area_page.render()

    elif route == C.ROUTE_REPORT:
        from platform_pages import report

        report.render()

    elif route == C.ROUTE_FORECAST:
        from platform_pages import forecast as forecast_page

        forecast_page.render()

    elif route == C.ROUTE_EXPERIMENTAL:
        from platform_pages import region_experimental

        region_experimental.render()

    elif route == C.ROUTE_EXPLORE:
        from platform_pages import explore

        explore.render()

    elif route == C.ROUTE_ABOUT:
        from platform_pages import about

        about.render()

    else:
        from platform_pages import overview

        overview.render()

finally:
    # ─────────────────────────────────────────────────────────────────────────
    # 5. SHELL LOCK
    #    Emitted last so the platform chrome always wins over any stylesheet a
    #    regional dashboard injected during its own run. Inside `finally` so it
    #    still applies when a region calls st.stop().
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(ds.build_shell_lock_css(dark=DARK), unsafe_allow_html=True)
    nav.render_sidebar_footer()
