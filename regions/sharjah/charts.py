"""
Plotly builders for the Sharjah dashboard.

Every chart is a faithful reproduction of a chart drawn in one of the three
source reports, using the values recorded in `sources.py` and no others.
Styling comes from `platform_core.chart_theme` so Sharjah looks native to the
same product as Dubai and Abu Dhabi.
"""

from __future__ import annotations

import plotly.graph_objects as go

from platform_core.chart_theme import (
    AMBER, CHART_COLORS, PRIMARY, SECONDARY, VIOLET, layout,
)

from . import sources as S


# ─────────────────────────────────────────────────────────────────────────────
# INVESTMENT BY NATIONALITY — horizontal bar
# Reproduces: Savills Q1 2026, page 3 — "INVESTMENT BY NATIONALITY"
# ─────────────────────────────────────────────────────────────────────────────


def investor_nationality(dark: bool = False) -> go.Figure:
    items = S.SHARJAH_INVESTOR_NATIONALITY
    labels = [d["label"] for d in items]
    values = [d["value_aed_billion"] for d in items]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=[PRIMARY, SECONDARY, AMBER, VIOLET][: len(items)],
        text=[f"AED {v:.1f}B" for v in values],
        textposition="outside",
        hovertemplate="%{y}<br>AED %{x:.1f}B<extra></extra>",
    ))
    lo = layout(
        title="Investment by Nationality — Q1 2026 (AED billion)",
        height=340,
        show_legend=False,
        dark=dark,
        hovermode="closest",
    )
    lo["yaxis"]["autorange"] = "reversed"       # UAE Nationals at top
    lo["xaxis"]["title"] = {"text": "AED billion"}
    lo["margin"] = {"l": 130, "r": 55, "t": 55, "b": 45}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SALES BY PROPERTY TYPE — vertical bar
# Reproduces: Savills Q1 2026, page 3 — "SALES BY PROPERTY TYPE"
# The source percentages do NOT sum to 100% and are not normalised.
# ─────────────────────────────────────────────────────────────────────────────


def property_type_share(dark: bool = False) -> go.Figure:
    items = S.SHARJAH_PROPERTY_TYPE_SHARE
    labels = [d["label"] for d in items]
    values = [d["share_pct"] for d in items]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=[SECONDARY, PRIMARY, AMBER][: len(items)],
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>",
    ))
    lo = layout(
        title="Sales by Property Type — Share of residential sales transactions (%)",
        height=360,
        show_legend=False,
        dark=dark,
        hovermode="closest",
    )
    lo["yaxis"]["title"] = {"text": "Share of transactions (%)"}
    lo["yaxis"]["range"] = [0, max(values) * 1.25]
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TOP PERFORMING AREAS — horizontal ranking
# Reproduces: Savills Q1 2026, page 3 — "TOP PERFORMING AREAS BY TRADING VALUE"
# ─────────────────────────────────────────────────────────────────────────────


def top_areas(dark: bool = False) -> go.Figure:
    items = S.SHARJAH_TOP_AREAS
    areas = [d["area"] for d in items]
    values = [d["value_aed_million"] for d in items]

    fig = go.Figure(go.Bar(
        x=values,
        y=areas,
        orientation="h",
        marker_color=PRIMARY,
        text=[f"AED {v:,}M" for v in values],
        textposition="outside",
        hovertemplate="%{y}<br>AED %{x:,}M<extra></extra>",
    ))
    lo = layout(
        title="Top Performing Areas by Trading Value — Q1 2026 (AED million)",
        height=380,
        show_legend=False,
        dark=dark,
        hovermode="closest",
    )
    lo["yaxis"]["autorange"] = "reversed"       # Rank 1 at top
    lo["xaxis"]["title"] = {"text": "Trading value (AED million)"}
    lo["margin"] = {"l": 165, "r": 65, "t": 55, "b": 45}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION VALUE — published data points only
# Reproduces the SUBSET of the Savills Q1 2026 quarterly chart for which the
# report provides explicit numeric values. Individual mid-quarter bars are not
# fabricated from pixels.
# ─────────────────────────────────────────────────────────────────────────────


def transaction_value_points(dark: bool = False) -> go.Figure:
    items = S.SHARJAH_TRANSACTION_VALUE_POINTS
    labels = [d["period"] for d in items]
    values = [d["value_aed_billion"] for d in items]
    statuses = [d["status"] for d in items]

    colours = []
    for st in statuses:
        if "post-Q1" in st:
            colours.append(AMBER)
        elif st == "derived":
            colours.append(CHART_COLORS[4])       # muted, so it reads as reference
        else:
            colours.append(PRIMARY)

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colours,
        text=[f"AED {v:.1f}B" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>AED %{y:.1f}B<br>%{customdata}<extra></extra>",
        customdata=statuses,
    ))
    lo = layout(
        title="Transaction Value — published reference points (AED billion)",
        height=360,
        show_legend=False,
        dark=dark,
        hovermode="closest",
    )
    lo["yaxis"]["title"] = {"text": "AED billion"}
    fig.update_layout(**lo)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION VOLUME — published data points only
# ─────────────────────────────────────────────────────────────────────────────


def transaction_volume_points(dark: bool = False) -> go.Figure:
    items = S.SHARJAH_TRANSACTION_VOLUME_POINTS
    labels = [d["period"] for d in items]
    values = [d["transactions"] for d in items]
    statuses = [d["status"] for d in items]

    colours = []
    for st in statuses:
        if "post-Q1" in st:
            colours.append(AMBER)
        elif st == "derived":
            colours.append(CHART_COLORS[4])
        else:
            colours.append(SECONDARY)

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colours,
        text=[f"{v:,}" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:,} transactions<br>%{customdata}<extra></extra>",
        customdata=statuses,
    ))
    lo = layout(
        title="Transaction Volume — published reference points (number of transactions)",
        height=360,
        show_legend=False,
        dark=dark,
        hovermode="closest",
    )
    lo["yaxis"]["title"] = {"text": "Transactions"}
    fig.update_layout(**lo)
    return fig
