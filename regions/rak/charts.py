"""Reusable Plotly builders for RAK yearly and quarterly analytics."""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go

from platform_core.chart_theme import AMBER, PRIMARY, SECONDARY, layout

from . import analytics as data
from . import sources as S


def _bar_chart(
    *,
    categories: Sequence[str],
    values: Sequence[float | int | None],
    series_name: str,
    title: str,
    y_title: str,
    suffix: str,
    scale: float,
    color: str,
    dark: bool,
    height: int = 420,
) -> go.Figure:
    """Build one consistently styled category bar chart."""
    scaled = [value / scale if value is not None else None for value in values]
    text = [f"{value / scale:,.2f}{suffix}" if value is not None else "—"
            for value in values]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=series_name,
        x=list(categories),
        y=scaled,
        marker_color=color,
        text=text,
        textposition="outside",
        hovertemplate=(
            f"{series_name}<br>%{{x}}<br>%{{y:,.2f}}{suffix}"
            "<extra></extra>"
        ),
    ))
    chart_layout = layout(
        title=title,
        height=height,
        show_legend=False,
        dark=dark,
        hovermode="x",
    )
    chart_layout["yaxis"]["title"] = {"text": y_title}
    chart_layout["margin"] = {"l": 65, "r": 25, "t": 60, "b": 115}
    fig.update_layout(**chart_layout)
    return fig


def _metric_chart(
    snapshot: data.AnnualSnapshot | data.QuarterlySnapshot,
    metrics: Sequence[tuple[str, str, str]],
    *,
    title: str,
    y_title: str,
    suffix: str,
    scale: float,
    color: str,
    dark: bool,
) -> go.Figure:
    return _bar_chart(
        categories=[label for label, _, _ in metrics],
        values=[snapshot.metrics.get(key) for _, key, _ in metrics],
        series_name=str(snapshot.year),
        title=title,
        y_title=y_title,
        suffix=suffix,
        scale=scale,
        color=color,
        dark=dark,
    )


def annual_value_chart(snapshot: data.AnnualSnapshot, dark: bool = False) -> go.Figure:
    return _metric_chart(
        snapshot,
        data.CHART_VALUE_METRICS,
        title=f"Yearly Aggregate Transaction Value — {snapshot.year}",
        y_title="AED billion",
        suffix="B",
        scale=1e9,
        color=PRIMARY,
        dark=dark,
    )


def quarterly_monthly_value_chart(
    snapshot: data.QuarterlySnapshot,
    dark: bool = False,
) -> go.Figure:
    """Plot the three complete monthly reports inside the selected quarter."""
    colors = (PRIMARY, SECONDARY, AMBER)
    fig = go.Figure()
    for (label, key, _), color in zip(data.CHART_VALUE_METRICS, colors):
        fig.add_trace(go.Scatter(
            name=label,
            x=list(snapshot.months),
            y=[row[key] / 1e9 for row in snapshot.monthly],
            mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"color": color, "size": 8},
            hovertemplate=(
                f"{label}<br>%{{x}}<br>AED %{{y:,.2f}}B<extra></extra>"
            ),
        ))
    chart_layout = layout(
        title=f"Monthly Transaction Value — {snapshot.quarter} {snapshot.year}",
        height=420,
        show_legend=True,
        dark=dark,
        hovermode="x unified",
    )
    chart_layout["yaxis"]["title"] = {"text": "AED billion"}
    chart_layout["margin"] = {"l": 65, "r": 25, "t": 60, "b": 65}
    fig.update_layout(**chart_layout)
    return fig


# POPULAR AREAS 2025 — grouped bar (2024 vs 2025)
# Reproduces: RAK Annual 2025 Figure 2
# ─────────────────────────────────────────────────────────────────────────────


def popular_areas_2025(dark: bool = False) -> go.Figure:
    rows = S.RAK_POPULAR_AREAS_2025
    areas = [r["region"] for r in rows]
    y2024 = [r["sales_value_2024_aed"] / 1e6 for r in rows]
    y2025 = [r["sales_value_2025_aed"] / 1e6 for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="2024", x=areas, y=y2024, marker_color=SECONDARY,
                         text=[f"{v:,.0f}M" for v in y2024], textposition="outside",
                         hovertemplate="2024<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    fig.add_trace(go.Bar(name="2025", x=areas, y=y2025, marker_color=PRIMARY,
                         text=[f"{v:,.0f}M" for v in y2025], textposition="outside",
                         hovertemplate="2025<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    lo = layout(title="Sales Value Index for the 3 most Traded Regions (AED million)",
                height=420, show_legend=True, dark=dark, hovermode="x")
    lo["barmode"] = "group"
    lo["yaxis"]["title"] = {"text": "AED million"}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PROPERTY USE 2024 vs 2025 — grouped bar
# Reproduces: RAK Annual 2025 Figure 3
# ─────────────────────────────────────────────────────────────────────────────


def property_use_2024_2025(dark: bool = False) -> go.Figure:
    rows = [r for r in S.RAK_PROPERTY_USE_2024_2025
            if r["y2024_aed"] > 0 or r["y2025_aed"] > 0]
    uses = [r["use"] for r in rows]
    y2024 = [r["y2024_aed"] / 1e6 for r in rows]
    y2025 = [r["y2025_aed"] / 1e6 for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="2024", x=uses, y=y2024, marker_color=SECONDARY,
                         hovertemplate="2024<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    fig.add_trace(go.Bar(name="2025", x=uses, y=y2025, marker_color=PRIMARY,
                         hovertemplate="2025<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    lo = layout(title="Real Estate Sales Value by Land Type (AED million)",
                height=500, show_legend=True, dark=dark, hovermode="closest")
    lo["barmode"] = "group"
    lo["yaxis"]["title"] = {"text": "AED million"}
    lo["xaxis"]["tickangle"] = -30
    lo["margin"] = {"l": 55, "r": 25, "t": 55, "b": 120}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# INVESTORS BY VALUE 2025 — horizontal ranking
# Reproduces: RAK Annual 2025 Table 4 (value)
# ─────────────────────────────────────────────────────────────────────────────


def investors_by_value_2025(dark: bool = False) -> go.Figure:
    rows = S.RAK_INVESTORS_BY_VALUE_2025
    labels = [r["nationality"] for r in rows]
    values = [r["value_aed"] / 1e6 for r in rows]

    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h",
                           marker_color=PRIMARY,
                           text=[f"AED {v:,.0f}M" for v in values],
                           textposition="outside",
                           hovertemplate="%{y}<br>AED %{x:,.0f}M<extra></extra>"))
    lo = layout(title="Top Ten Investing Nationalities by Transaction Value — 2025 (AED million)",
                height=460, show_legend=False, dark=dark, hovermode="closest")
    lo["yaxis"]["autorange"] = "reversed"
    lo["xaxis"]["title"] = {"text": "AED million"}
    lo["margin"] = {"l": 150, "r": 90, "t": 55, "b": 45}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# INVESTORS BY NUMBER 2025 — horizontal ranking
# Reproduces: RAK Annual 2025 Figure 4 (number)
# ─────────────────────────────────────────────────────────────────────────────


def investors_by_number_2025(dark: bool = False) -> go.Figure:
    rows = S.RAK_INVESTORS_BY_NUMBER_2025
    labels = [r["nationality"] for r in rows]
    values = [r["count"] for r in rows]

    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h",
                           marker_color=SECONDARY,
                           text=[f"{v:,}" for v in values], textposition="outside",
                           hovertemplate="%{y}<br>%{x:,} investors<extra></extra>"))
    lo = layout(title="Top Ten Investing Nationalities by Number — 2025",
                height=460, show_legend=False, dark=dark, hovermode="closest")
    lo["yaxis"]["autorange"] = "reversed"
    lo["xaxis"]["title"] = {"text": "Number of investors"}
    lo["margin"] = {"l": 150, "r": 65, "t": 55, "b": 45}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# LATEST MONTHLY VALUE — grouped bar (Jan 2025 vs Jan 2026)
# Reproduces: RAK Monthly Jan 2026 Figure 1
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY TIME SERIES — from the 26 monthly PDFs
# Each dot is one month whose value was extracted verbatim from a monthly report.
# Series are drawn as lines with gaps where the source is missing (Sales-only
# reports carry no mortgage/waiver values, and those months simply have no
# marker for those series).
# ─────────────────────────────────────────────────────────────────────────────

MONTHS_ORDER = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]


def _period_label(pt):
    return f"{pt['month'][:3]} {pt['year']}"


def monthly_sales_value(dark: bool = False) -> go.Figure:
    pts = S.RAK_MONTHLY_TIMESERIES
    x = [_period_label(p) for p in pts]
    ys = [p["sales_v"] / 1e6 if p.get("sales_v") else None for p in pts]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=ys, mode="lines+markers", name="Sales Volume",
        line=dict(color=PRIMARY, width=2.2),
        marker=dict(size=7, color=PRIMARY),
        connectgaps=False,
        hovertemplate="%{x}<br>Sales: AED %{y:,.1f}M<extra></extra>",
    ))
    lo = layout(
        title="Sales Value — Monthly Time Series 2019–2026 (AED million)",
        height=420, show_legend=False, dark=dark, hovermode="x",
    )
    lo["yaxis"]["title"] = {"text": "Sales value (AED million)"}
    lo["xaxis"]["tickangle"] = -45
    lo["margin"] = {"l": 60, "r": 25, "t": 55, "b": 90}
    fig.update_layout(**lo)
    return fig


def monthly_sales_count(dark: bool = False) -> go.Figure:
    pts = S.RAK_MONTHLY_TIMESERIES
    x = [_period_label(p) for p in pts]
    ys = [p["sales_n"] if p.get("sales_n") else None for p in pts]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=ys, mode="lines+markers", name="Sales Number",
        line=dict(color=SECONDARY, width=2.2),
        marker=dict(size=7, color=SECONDARY),
        connectgaps=False,
        hovertemplate="%{x}<br>%{y:,} sales<extra></extra>",
    ))
    lo = layout(
        title="Sales Number — Monthly Time Series 2019–2026",
        height=380, show_legend=False, dark=dark, hovermode="x",
    )
    lo["yaxis"]["title"] = {"text": "Number of sales"}
    lo["xaxis"]["tickangle"] = -45
    lo["margin"] = {"l": 55, "r": 25, "t": 55, "b": 90}
    fig.update_layout(**lo)
    return fig


def monthly_three_series(dark: bool = False) -> go.Figure:
    """Sales / Mortgages / Waivers on one chart — only points where source has values."""
    pts = S.RAK_MONTHLY_TIMESERIES
    x = [_period_label(p) for p in pts]
    sv = [p["sales_v"] / 1e6 if p.get("sales_v") else None for p in pts]
    mv = [p["mort_v"]  / 1e6 if p.get("mort_v")  else None for p in pts]
    wv = [p["waiv_v"]  / 1e6 if p.get("waiv_v")  else None for p in pts]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=sv, mode="lines+markers", name="Sales",
                             line=dict(color=PRIMARY, width=2.0), marker=dict(size=6),
                             connectgaps=False,
                             hovertemplate="Sales · %{x}<br>AED %{y:,.1f}M<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=mv, mode="lines+markers", name="Mortgages",
                             line=dict(color=SECONDARY, width=2.0), marker=dict(size=6),
                             connectgaps=False,
                             hovertemplate="Mortgages · %{x}<br>AED %{y:,.1f}M<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=wv, mode="lines+markers", name="Waivers",
                             line=dict(color=AMBER, width=2.0), marker=dict(size=6),
                             connectgaps=False,
                             hovertemplate="Waivers · %{x}<br>AED %{y:,.1f}M<extra></extra>"))
    lo = layout(
        title="Sales / Mortgages / Waivers — Monthly Values 2019–2026 (AED million)",
        height=460, show_legend=True, dark=dark, hovermode="x unified",
    )
    lo["yaxis"]["title"] = {"text": "AED million"}
    lo["xaxis"]["tickangle"] = -45
    lo["margin"] = {"l": 60, "r": 25, "t": 55, "b": 100}
    fig.update_layout(**lo)
    return fig


def jan_2025_vs_2026(dark: bool = False) -> go.Figure:
    cats = ["Sales", "Mortgages", "Waivers"]
    y25 = [
        S.RAK_JAN_2025["sales_value_aed"] / 1e6,
        S.RAK_JAN_2025["mortgages_aed"] / 1e6,
        S.RAK_JAN_2025["waivers_aed"] / 1e6,
    ]
    y26 = [
        S.RAK_JAN_2026["sales_value_aed"] / 1e6,
        S.RAK_JAN_2026["mortgages_aed"] / 1e6,
        S.RAK_JAN_2026["waivers_aed"] / 1e6,
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Jan 2025", x=cats, y=y25, marker_color=SECONDARY,
                         text=[f"AED {v:,.0f}M" for v in y25], textposition="outside",
                         hovertemplate="Jan 2025<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    fig.add_trace(go.Bar(name="Jan 2026", x=cats, y=y26, marker_color=PRIMARY,
                         text=[f"AED {v:,.0f}M" for v in y26], textposition="outside",
                         hovertemplate="Jan 2026<br>%{x}<br>AED %{y:,.0f}M<extra></extra>"))
    lo = layout(title="Real Estate Transactions Value in January 2025 / 2026 (AED million)",
                height=380, show_legend=True, dark=dark, hovermode="x")
    lo["barmode"] = "group"
    lo["yaxis"]["title"] = {"text": "AED million"}
    fig.update_layout(**lo)
    return fig
