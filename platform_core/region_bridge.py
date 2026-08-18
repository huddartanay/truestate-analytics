"""
Compatibility bridge between the unified shell and the two regional apps.

This module is the ONLY thing the regional applications import from the
platform. Every function is written so that the regional app still runs
standalone (exactly as before) when the shell is not present:

    streamlit run regions/abu_dhabi/app.py     # still works
    streamlit run regions/dubai/trial.py       # still works

See docs/INTEGRATION_CHANGES.md for the exact lines that changed.
"""

from __future__ import annotations

import streamlit as st

_EMBEDDED = False


# ─────────────────────────────────────────────────────────────────────────────
# EMBED FLAG (set by platform_core.runtime before a region executes)
# ─────────────────────────────────────────────────────────────────────────────


def _set_embedded(value: bool) -> None:
    global _EMBEDDED
    _EMBEDDED = value


def is_embedded() -> bool:
    """True when the region is running inside the unified platform shell."""
    return _EMBEDDED


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────


def page_config(**kwargs) -> None:
    """
    Regional replacement for st.set_page_config().

    Inside the platform there is exactly one global page configuration, owned by
    platform_core.config. Standalone, the region keeps its original config.
    """
    if _EMBEDDED:
        return
    try:
        st.set_page_config(**kwargs)
    except Exception:
        # Streamlit only permits one call per script run; ignore duplicates.
        pass


# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────


def render_theme_toggle(dark: bool, label_dark: str = "🌙 Dark Mode",
                        label_light: str = "☀️ Light Mode") -> None:
    """
    Abu Dhabi's original in-sidebar theme switch.

    Embedded, the platform rail owns appearance (writing to the same
    `dark_mode` session key), so this renders nothing and the region simply
    follows the global setting. Standalone, the original button is drawn.
    """
    if _EMBEDDED:
        return
    icon = label_light if dark else label_dark
    if st.button(icon, key="theme_toggle", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown("---")


def render_region_brand(html: str) -> None:
    """
    Region-specific sidebar logo.

    Embedded, the platform already shows the product brand at the top of the
    rail — a second logo underneath would be confusing nested branding, so this
    is suppressed. Standalone, the original markup is rendered unchanged.
    """
    if _EMBEDDED:
        return
    st.markdown(html, unsafe_allow_html=True)


def render_region_sidebar_title(text: str) -> None:
    """
    Region-specific sidebar heading (e.g. "FlipOse-RE-Analytics-V1").

    Embedded, the rail already names the active workspace in plain language, so
    repeating the raw generation string here would be redundant navigation
    noise. Standalone, the original heading is rendered unchanged.
    """
    if _EMBEDDED:
        return
    st.sidebar.title(text)


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENTAL ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────


def experiment_selection(options: list[str]) -> str:
    """
    Replacement for the experimental app's top-level
    `st.sidebar.radio("Versions", [...])`.

    Embedded, the generation is chosen from the global rail and this returns the
    matching legacy identifier ("V1", "V2", "V2.1", "FC", "area_combination",
    "V_2.2") so every downstream `if page == ...` branch in trial.py keeps
    working byte-for-byte. Standalone, the original radio is rendered.
    """
    if not _EMBEDDED:
        return st.sidebar.radio("Versions", options)

    from . import config as C

    exp_id = st.session_state.get(C.SS_EXPERIMENT, C.DEFAULT_EXPERIMENT)
    legacy = C.EXPERIMENT_BY_ID.get(exp_id, C.EXPERIMENTS[0])["legacy"]

    # Safety net: never hand the experiment a value its branches don't recognise.
    return legacy if legacy in options else options[0]


def experiment_views(options: list[str]) -> list[str]:
    """
    Filter an experiment's own view list before it is rendered.

    Embedded, views listed in `config.EXPERIMENT_HIDDEN_VIEWS` are removed from
    the interface — currently "Data Summary", by request. The code behind those
    views is left untouched in trial.py; it simply becomes unreachable from the
    UI. Standalone, the original list is returned unchanged.

    If filtering would empty the list, the original list is returned so the
    experiment can never be left with no navigation at all.
    """
    if not _EMBEDDED:
        return options

    from . import config as C

    kept = [o for o in options if o not in C.EXPERIMENT_HIDDEN_VIEWS]
    return kept or options
