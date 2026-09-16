"""Small shared helper for server-side page-preparation timing."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

import streamlit as st

_LOGGER = logging.getLogger(__name__)

_PAGE_LABELS = {
    "overview": "Overview",
    "abu_dhabi": "Abu Dhabi",
    "dubai": "Dubai",
    "sharjah": "Sharjah",
    "rak": "RAK",
    "area": "Area Analysis",
    "report": "Download Reports",
    "forecast": "Forecast",
    "experimental": "Experimental Analysis",
    "explore": "Explore Platform",
    "about": "About",
}


def page_label(route: str) -> str:
    """Return the friendly label used by the timing caption and log."""
    return _PAGE_LABELS.get(route, route.replace("_", " ").title())


@contextmanager
def page_timer(route: str) -> Iterator[None]:
    """Measure server-side preparation and show one unobtrusive caption.

    The duration ends after the active route's Python rendering has completed.
    It does not claim to measure browser paint, network transfer, or the time
    Streamlit Cloud spends waking a sleeping container.
    """
    started = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - started
        label = page_label(route)
        _LOGGER.info("page_preparation page=%s duration_seconds=%.4f", label, elapsed)
        st.caption(f"Page prepared in {elapsed:.2f}s")
