"""
🔮 Forecast — its own destination in the rail, directly under Download
Detailed Report.

This page is a frame, not a second implementation. The whole section comes from
`regions.dubai_market.forecast_ui`, the same module the Download Detailed Report
page and the Dubai dashboard's Download Report tab render. One implementation in
three places means the three cannot drift apart, and — more importantly — there
is still exactly ONE area control in the application: the global 📍 Area. This
page reads it and shows it read-only, like the others.
"""

from __future__ import annotations

import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav


def render() -> None:
    ui.breadcrumb("TruEstate Analytics", "Forecast")

    area = nav.area()
    st.markdown(
        '<div class="uae-card uae-d1" style="margin-bottom:1.1rem">'
        '<p class="uae-h3">🔮 Price forecast</p>'
        '<p class="uae-sub" style="max-width:96ch">Describe a property — rooms, floor, '
        'size, grades, amenities — and the TruEstate Forecast API returns what it is '
        'worth per square metre now and where it is heading over the months ahead, with '
        'and without recent news weighed in. The area follows whatever is set under '
        '📍 Area; every other attribute is chosen below, from the values recorded for '
        'that area.</p></div>',
        unsafe_allow_html=True,
    )

    try:
        from regions.dubai_market.data import COL, DubaiDataError, load_market
    except Exception as exc:  # pragma: no cover
        st.error(f"**Dubai module could not be imported.**\n\n{exc}", icon="⚠️")
        return

    df = None
    if area != C.ALL_AREAS:
        try:
            with st.spinner("Loading Dubai market data…"):
                df_all = load_market()
            df = df_all[df_all[COL["area"]] == area]
        except (DubaiDataError, FileNotFoundError) as exc:
            # The forecast itself does not need the local dataset — only the
            # optional context line does — so this is reported and the section
            # still renders.
            st.warning(
                f"**The local dataset could not be loaded**, so the recorded-median "
                f"context line is unavailable. The forecast itself is unaffected.\n\n"
                f"{exc}", icon="📄")
            df = None

    try:
        from regions.dubai_market import forecast_ui
        forecast_ui.render(
            area, df_area=df,
            dark=bool(st.session_state.get(C.SS_THEME_DARK, False)))
    except Exception as exc:  # pragma: no cover - surfaced, never swallowed
        st.error(f"**The forecast section could not be loaded.**\n\n"
                 f"`{type(exc).__name__}: {exc}`", icon="⚠️")
        st.exception(exc)
        return

    ui.footer(C.PLATFORM_VERSION, f"Forecast · {area}")
