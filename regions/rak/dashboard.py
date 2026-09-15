"""RAK Analytics page: one dynamic yearly view and one dynamic quarterly view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from platform_core import components as ui
from platform_core.chart_theme import PLOTLY_CONFIG

from . import analytics as data
from . import charts as ch


PC = PLOTLY_CONFIG


def _format_aed(value: float | int | None) -> str:
    if value is None:
        return "—"
    absolute = abs(value)
    if absolute >= 1e9:
        return f"AED {value / 1e9:,.2f}B"
    if absolute >= 1e6:
        return f"AED {value / 1e6:,.2f}M"
    if absolute >= 1e3:
        return f"AED {value / 1e3:,.1f}K"
    return f"AED {value:,.0f}"


def _format_metric(value: float | int | None, unit: str) -> str:
    if unit == "AED":
        return _format_aed(value)
    if value is None:
        return "—"
    return f"{value:,.0f}"


def _metric_table(snapshot: data.AnnualSnapshot | data.QuarterlySnapshot) -> None:
    rows = [
        {"Metric": label, "Value": _format_metric(snapshot.metrics.get(key), unit), "Unit": unit}
        for label, key, unit in data.ALL_METRICS
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _kpis(snapshot: data.AnnualSnapshot | data.QuarterlySnapshot) -> None:
    """Render the same source metric set for either selected period."""
    metrics = data.ALL_METRICS
    for start in range(0, len(metrics), 4):
        columns = st.columns(4, gap="medium")
        for column, (label, key, unit) in zip(columns, metrics[start:start + 4]):
            with column:
                st.metric(label, _format_metric(snapshot.metrics.get(key), unit))


def _charts(snapshot: data.AnnualSnapshot | data.QuarterlySnapshot, dark: bool, *, quarterly: bool) -> None:
    if quarterly:
        value_chart = ch.quarterly_value_chart(snapshot, dark=dark)
        count_chart = ch.quarterly_count_chart(snapshot, dark=dark)
    else:
        value_chart = ch.annual_value_chart(snapshot, dark=dark)
        count_chart = ch.annual_count_chart(snapshot, dark=dark)
    left, right = st.columns(2, gap="large")
    with left:
        st.plotly_chart(value_chart, use_container_width=True, config=PC)
    with right:
        st.plotly_chart(count_chart, use_container_width=True, config=PC)


def _section_yearly(dark: bool) -> None:
    ui.section(
        "Yearly Analytics",
        "Select one year to view the values, counts, KPIs and table from that annual report.",
        "📈",
    )
    year_options = list(data.ANNUAL_YEAR_OPTIONS)
    default_year = data.latest_available_annual_year() or year_options[-1]
    year = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(default_year),
        key="rak.yearly.year",
    )
    snapshot = data.annual_snapshot(year)
    if snapshot is None:
        st.info(
            f"No annual RAK report containing {year} is available in the source registry. "
            "This view does not reconstruct annual values from monthly reports."
        )
        return

    st.caption(f"Source: {snapshot.source['citation']}")
    _kpis(snapshot)
    _charts(snapshot, dark, quarterly=False)
    _metric_table(snapshot)


def _section_quarterly(dark: bool) -> None:
    ui.section(
        "Quarterly Analytics",
        "Quarterly values are summed from complete January–March, April–June, "
        "July–September or October–December monthly report triplets.",
        "📆",
    )
    year_options = list(data.ANNUAL_YEAR_OPTIONS)
    latest = data.latest_completed_quarter(year_options)
    default_year = latest[0] if latest else year_options[-1]
    with_year, with_quarter = st.columns(2, gap="medium")
    with with_year:
        year = st.selectbox(
            "Year",
            year_options,
            index=year_options.index(default_year),
            key="rak.quarterly.year",
        )
    quarter_options = list(data.available_quarters(year))
    with with_quarter:
        if quarter_options:
            default_quarter = latest[1] if latest and latest[0] == year else quarter_options[-1]
            quarter = st.selectbox(
                "Quarter",
                quarter_options,
                index=quarter_options.index(default_quarter),
                key="rak.quarterly.quarter",
            )
        else:
            st.selectbox(
                "Quarter",
                ["No completed quarter"],
                disabled=True,
                key="rak.quarterly.quarter.unavailable",
            )
            quarter = None

    if quarter is None:
        st.info(
            f"No complete quarter is available for {year}. A quarter is shown only when "
            "all three required monthly reports are present; no incomplete quarter is generated."
        )
        return
    snapshot = data.quarterly_snapshot(year, quarter)
    if snapshot is None:
        st.info("That quarter is no longer complete in the available monthly source set.")
        return

    st.caption(
        f"Monthly sources: {', '.join(snapshot.months)} {year}. "
        "Only numeric report fields are aggregated."
    )
    _kpis(snapshot)
    _charts(snapshot, dark, quarterly=True)
    _metric_table(snapshot)


def render(dark: bool = False) -> None:
    """Render exactly the two dynamic RAK analytics sections."""
    _section_yearly(dark)
    _section_quarterly(dark)
