"""
📍 Area — the one global Dubai area selector.

This is the single place an area is chosen. The value is held in platform state
(`C.SS_AREA`) and read by the Dubai dashboard, which slices its dataframe with
it **before** any grouping or aggregation runs. No Dubai chart carries its own
area control any more.

Two things this page deliberately does NOT do:

  * It does not touch Abu Dhabi. Abu Dhabi loads a different dataset with its
    own area column and its own filters, and nothing here reaches it.
  * It does not replace the Dubai sidebar's existing `Area` multiselect. That
    control pre-dates this page and is left exactly as it was; this selector
    sits in front of it, so the two compose rather than fight.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core import config as C
from platform_core import navigation as nav


def _area_counts() -> pd.DataFrame:
    """Areas present in the Dubai cleaned dataset, busiest first, with counts."""
    from regions.dubai_market.data import COL, load_market

    df = load_market()
    vc = df[COL["area"]].dropna().value_counts()
    out = vc.reset_index()
    out.columns = ["Area", "Transactions"]
    out["Share of Dubai (%)"] = out["Transactions"] / len(df) * 100
    med = (df.groupby(COL["area"], observed=True)[COL["rate"]].median()
             .reindex(out["Area"]).values)
    out["Median rate (AED/m²)"] = med
    return out


def render() -> None:
    ui.breadcrumb("TruEstate Analytics", "Area")

    st.markdown(
        '<div class="uae-card uae-d1" style="margin-bottom:1.1rem">'
        '<p class="uae-h3">📍 Dubai area — global analytical context</p>'
        '<p class="uae-sub" style="max-width:96ch">Choose an area once here. Every Dubai '
        'analysis that can be narrowed by area is then calculated from those transactions '
        'only — the dataframe is filtered before any grouping or aggregation runs, so the '
        'numbers change, not just the titles.</p></div>',
        unsafe_allow_html=True,
    )

    try:
        counts = _area_counts()
    except Exception as exc:  # pragma: no cover - surfaced to the user instead
        st.error(f"**Dubai area list could not be loaded.**\n\n{exc}", icon="⚠️")
        return

    total = int(counts["Transactions"].sum())
    labels = {C.ALL_AREAS: f"{C.ALL_AREAS}  ({total:,} transactions)"}
    labels.update({r.Area: f"{r.Area}  ({int(r.Transactions):,})"
                   for r in counts.itertuples()})
    options = [C.ALL_AREAS] + list(counts["Area"])

    current = nav.area()
    if current not in options:          # dataset changed under a stale selection
        current = C.ALL_AREAS

    chosen = st.selectbox(
        "Area", options, index=options.index(current),
        format_func=lambda a: labels.get(a, a),
        help="Applies to every Dubai analysis that can be narrowed by area. Areas are "
             "listed busiest first; the count is how many transactions each one holds "
             "in the cleaned Dubai dataset.",
    )
    if chosen != nav.area():
        nav.set_area(chosen)
        st.rerun()

    # ── what the current selection means ────────────────────────────────────
    if chosen == C.ALL_AREAS:
        st.success(
            f"**All Areas selected.** Dubai analytics run on the complete eligible dataset — "
            f"**{total:,}** transactions across **{len(counts)}** areas. This is the default.",
            icon="✅")
    else:
        row = counts[counts["Area"] == chosen].iloc[0]
        st.success(
            f"**{chosen} selected.** Every Dubai analysis that can be narrowed by area now "
            f"uses only these **{int(row.Transactions):,}** transactions "
            f"({row['Share of Dubai (%)']:.1f}% of Dubai). Median rate here is "
            f"**AED {row['Median rate (AED/m²)']:,.0f}/m²**.", icon="✅")

        k1, k2, k3 = st.columns(3)
        k1.metric("Transactions in this area", f"{int(row.Transactions):,}")
        k2.metric("Share of Dubai", f"{row['Share of Dubai (%)']:.1f}%")
        k3.metric("Median rate", f"AED {row['Median rate (AED/m²)']:,.0f}/m²")

        if st.button("↩︎  Reset to All Areas", use_container_width=False):
            nav.set_area(C.ALL_AREAS)
            st.rerun()

    st.info(
        "**Where this applies.** The Dubai dashboard's Rate per m² by layout, amenity "
        "analysis, building-height analysis and the rest of its area-sensitive views all "
        "read this one value — none of them carries its own area dropdown. It does **not** "
        "affect Abu Dhabi, which is a separate dataset with its own filters, and it does not "
        "affect the Experimental Analysis environment, which keeps its own original "
        "controls.", icon="ℹ️")

    with st.expander(f"📋  Every Dubai area — {len(counts)} of them, by transaction count"):
        show = counts.copy()
        st.dataframe(
            show.style.format({"Transactions": "{:,}", "Share of Dubai (%)": "{:.2f}",
                               "Median rate (AED/m²)": "{:,.0f}"}, na_rep="—"),
            use_container_width=True, hide_index=True, height=420)
        st.caption("Counts come from the cleaned Dubai dataset before any sidebar filter is "
                   "applied, so they describe the area itself rather than your current "
                   "selection. Median rate is the median of `meter_sale_price` for that area.")

    ui.footer(C.PLATFORM_VERSION, f"Area · {chosen}")
