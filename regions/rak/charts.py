"""Reusable Plotly builders for RAK yearly and quarterly analytics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import plotly.graph_objects as go

from platform_core.chart_theme import PRIMARY, SECONDARY, layout

from . import analytics as data


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
        title=f"Annual Transaction Value — {snapshot.year}",
        y_title="AED billion",
        suffix="B",
        scale=1e9,
        color=PRIMARY,
        dark=dark,
    )


def annual_count_chart(snapshot: data.AnnualSnapshot, dark: bool = False) -> go.Figure:
    return _metric_chart(
        snapshot,
        data.CHART_COUNT_METRICS,
        title=f"Annual Transaction Count — {snapshot.year}",
        y_title="Number of transactions",
        suffix="",
        scale=1,
        color=SECONDARY,
        dark=dark,
    )


def quarterly_value_chart(snapshot: data.QuarterlySnapshot, dark: bool = False) -> go.Figure:
    return _metric_chart(
        snapshot,
        data.CHART_VALUE_METRICS,
        title=f"Quarterly Transaction Value — {snapshot.quarter} {snapshot.year}",
        y_title="AED billion",
        suffix="B",
        scale=1e9,
        color=PRIMARY,
        dark=dark,
    )


def quarterly_count_chart(snapshot: data.QuarterlySnapshot, dark: bool = False) -> go.Figure:
    return _metric_chart(
        snapshot,
        data.CHART_COUNT_METRICS,
        title=f"Quarterly Transaction Count — {snapshot.quarter} {snapshot.year}",
        y_title="Number of transactions",
        suffix="",
        scale=1,
        color=SECONDARY,
        dark=dark,
    )
