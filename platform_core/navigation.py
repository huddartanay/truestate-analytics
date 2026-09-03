"""
Global navigation: the single sidebar for the whole platform.

    🏠 Overview
    LOCATIONS
        🇦🇪 Abu Dhabi
        🇦🇪 Dubai
        🧪 Experimental Analysis
    PLATFORM
        🧭 Explore Platform
        ℹ️ About

Routing state lives in `st.session_state` under the `uae.` namespace so it can
never collide with keys used inside any of the three environments.

The rail is rendered BEFORE the active environment executes, so whatever
sidebar widgets that environment owns (filters, view pickers) appear underneath
it, under a clearly labelled divider — one hierarchy, not two competing menus.
"""

from __future__ import annotations

import streamlit as st

from . import config as C


# ─────────────────────────────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────────────────────────────


def init_state() -> None:
    st.session_state.setdefault(C.SS_ROUTE, C.DEFAULT_ROUTE)
    st.session_state.setdefault(C.SS_EXPERIMENT, C.DEFAULT_EXPERIMENT)
    st.session_state.setdefault(C.SS_AREA, C.ALL_AREAS)
    # Shared with the Abu Dhabi dashboard, which already owns this key.
    st.session_state.setdefault(C.SS_THEME_DARK, False)


def route() -> str:
    return st.session_state.get(C.SS_ROUTE, C.DEFAULT_ROUTE)


def experiment_id() -> str:
    return st.session_state.get(C.SS_EXPERIMENT, C.DEFAULT_EXPERIMENT)


def area() -> str:
    """The globally selected Dubai area, or `All Areas`."""
    return st.session_state.get(C.SS_AREA, C.ALL_AREAS)


def set_area(value: str) -> None:
    st.session_state[C.SS_AREA] = value or C.ALL_AREAS


def is_dark() -> bool:
    return bool(st.session_state.get(C.SS_THEME_DARK, False))


def goto(new_route: str, experiment: str | None = None) -> None:
    st.session_state[C.SS_ROUTE] = new_route
    if experiment:
        st.session_state[C.SS_EXPERIMENT] = experiment
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _keyed(key: str):
    """st.container(key=...) with a graceful fallback for older Streamlit."""
    try:
        return st.container(key=key)
    except TypeError:  # pragma: no cover - only on Streamlit < 1.45
        return st.container()


def _nav_item(label: str, target: str, active: bool, prefix: str = "uaenav") -> bool:
    """
    One navigation row. The active state is expressed through the container key
    (`...-on` / `...-off`), which Streamlit turns into a CSS class — that is what
    the design system hooks into for the selected-state styling.
    """
    state = "on" if active else "off"
    with _keyed(f"{prefix}-{target}-{state}"):
        return st.button(label, key=f"btn-{prefix}-{target}", use_container_width=True)


def _group(label: str) -> None:
    st.markdown(f'<p class="uae-navgroup">{label}</p>', unsafe_allow_html=True)


def _rule() -> None:
    st.markdown('<div class="uae-navrule"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────


def render_sidebar() -> str:
    """Render the global rail and return the active route."""
    current = route()

    with st.sidebar:
        # ── Brand ────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="uae-brand">'
            f'<div class="uae-brand-mark">{C.PLATFORM_ICON}</div>'
            f'<div><p class="uae-brand-name">{C.PLATFORM_NAME}<br>'
            f'<span class="l2">{C.PLATFORM_NAME_2}</span></p>'
            f'<p class="uae-brand-tag">{C.PLATFORM_TAGLINE}</p></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Home ─────────────────────────────────────────────────────────────
        if _nav_item("🏠   Overview", C.ROUTE_OVERVIEW, current == C.ROUTE_OVERVIEW):
            goto(C.ROUTE_OVERVIEW)

        # ── Locations ────────────────────────────────────────────────────────
        _group("Locations")

        if _nav_item("🇦🇪   Abu Dhabi", C.ROUTE_ABU_DHABI, current == C.ROUTE_ABU_DHABI):
            goto(C.ROUTE_ABU_DHABI)

        if _nav_item("🇦🇪   Dubai", C.ROUTE_DUBAI, current == C.ROUTE_DUBAI):
            goto(C.ROUTE_DUBAI)

        # Dubai sub-navigation — Area Selection, Forecast, Download Reports.
        # Expanded whenever Dubai or any of its sub-destinations is active,
        # exactly the way Experimental Analysis expands its generations below.
        # The routes themselves are unchanged; only the entry point has moved.
        DUBAI_SUB = (C.ROUTE_DUBAI, C.ROUTE_AREA, C.ROUTE_FORECAST, C.ROUTE_REPORT)
        if current in DUBAI_SUB:
            _area = area()
            _area_label = "📍   Area Selection" + (
                "" if _area == C.ALL_AREAS else f"  ·  {_area}"
            )
            if _nav_item(_area_label, C.ROUTE_AREA,
                         current == C.ROUTE_AREA, prefix="uaesub"):
                goto(C.ROUTE_AREA)
            if _nav_item("🔮   Forecast", C.ROUTE_FORECAST,
                         current == C.ROUTE_FORECAST, prefix="uaesub"):
                goto(C.ROUTE_FORECAST)
            if _nav_item("📄   Download Reports", C.ROUTE_REPORT,
                         current == C.ROUTE_REPORT, prefix="uaesub"):
                goto(C.ROUTE_REPORT)

        # Sharjah — sits directly under Dubai's sub-nav.
        # Report-sourced regional dashboard (see regions/sharjah/).
        if _nav_item("🇦🇪   Sharjah", C.ROUTE_SHARJAH, current == C.ROUTE_SHARJAH):
            goto(C.ROUTE_SHARJAH)

        # RAK — sits directly under Sharjah. Report-sourced (see regions/rak/).
        if _nav_item("🇦🇪   RAK", C.ROUTE_RAK, current == C.ROUTE_RAK):
            goto(C.ROUTE_RAK)

        if _nav_item("🧪   Experimental Analysis", C.ROUTE_EXPERIMENTAL,
                     current == C.ROUTE_EXPERIMENTAL):
            goto(C.ROUTE_EXPERIMENTAL)

        # Experiment generations expand only while the research environment is
        # active, so nobody else ever sees six raw version switches.
        if current == C.ROUTE_EXPERIMENTAL:
            active = experiment_id()
            for exp in C.EXPERIMENTS:
                if _nav_item(f"{exp['icon']}  {exp['label']}", exp["id"],
                             active == exp["id"], prefix="uaesub"):
                    goto(C.ROUTE_EXPERIMENTAL, experiment=exp["id"])

        # ── Platform ─────────────────────────────────────────────────────────
        _group("Platform")

        if _nav_item("🧭   Explore Platform", C.ROUTE_EXPLORE, current == C.ROUTE_EXPLORE):
            goto(C.ROUTE_EXPLORE)

        if _nav_item("ℹ️   About", C.ROUTE_ABOUT, current == C.ROUTE_ABOUT):
            goto(C.ROUTE_ABOUT)

        # ── Appearance ───────────────────────────────────────────────────────
        _rule()
        dark = is_dark()
        with _keyed("uaetheme"):
            if st.button(
                "☀️  Light appearance" if dark else "🌙  Dark appearance",
                key="btn-uaetheme",
                use_container_width=True,
            ):
                st.session_state[C.SS_THEME_DARK] = not dark
                st.rerun()

    return current


def render_sidebar_footer() -> None:
    """
    Rail footer — emitted at the very END of the script run so it sits beneath
    any widgets the active environment added to the sidebar, instead of floating
    in the middle of the rail.
    """
    st.sidebar.markdown(
        f'<div class="uae-side-footer">v{C.PLATFORM_VERSION} · Local build<br>'
        "Abu Dhabi · Dubai · Experimental</div>",
        unsafe_allow_html=True,
    )


def region_controls_divider(label: str = "Region controls") -> None:
    """
    Separator placed in the sidebar immediately before an environment renders
    its own controls, so they read as a second level of the same rail.
    """
    st.sidebar.markdown(
        f'<div class="uae-ctrl-head"><span class="lbl">{label}</span><span class="ln"></span></div>',
        unsafe_allow_html=True,
    )
