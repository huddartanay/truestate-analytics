"""
Plotly builders for the Dubai regional dashboard.

Styling comes from `platform_core.chart_theme`, which restates the Abu Dhabi
palette and layout so the two regions look like one product.

Charts that would otherwise plot hundreds of thousands of marks take a
deterministic sample (`random_state=42`); every such chart states its sample
size on screen. Aggregated charts always use the full filtered dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from platform_core.chart_theme import CHART_COLORS, PRIMARY, SECONDARY, AMBER, VIOLET, SEQUENTIAL, layout

from .data import COL, ROOM_ORDER
from .metrics import (PROPERTY_TYPE_LABELS, lowess_trend, monthly_series,
                      partial_tail_months, yoy_table)

SCATTER_SAMPLE = 15_000


def _box_stats(df: pd.DataFrame, group: str, value: str, order: list[str] | None = None):
    """
    Quartiles computed in pandas rather than shipped to the browser.

    Plotly can draw a box from precomputed statistics. Sending 100k+ raw values
    per chart is what makes box plots slow; the drawn quartiles are identical
    either way.
    """
    g = df.groupby(group, observed=True)[value]
    stats = g.quantile([0.25, 0.5, 0.75]).unstack()
    stats.columns = ["q1", "med", "q3"]
    iqr = stats["q3"] - stats["q1"]
    lo = (stats["q1"] - 1.5 * iqr).clip(lower=float(df[value].min()))
    hi = stats["q3"] + 1.5 * iqr
    stats["lower"] = [float(g.get_group(k)[g.get_group(k) >= lo[k]].min()) for k in stats.index]
    stats["upper"] = [float(g.get_group(k)[g.get_group(k) <= hi[k]].max()) for k in stats.index]
    stats["n"] = g.size()
    if order:
        keep = [o for o in order if o in stats.index]
        stats = stats.loc[keep]
    return stats


def _order_rooms(values) -> list[str]:
    vals = [str(v) for v in values]
    known = [r for r in ROOM_ORDER if r in vals]
    return known + sorted(set(vals) - set(known))


# ─────────────────────────────────────────────────────────────────────────────
# TRENDS
# ─────────────────────────────────────────────────────────────────────────────


def monthly_volume_value(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    m = monthly_series(df)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=m["_sort"], y=m["total_value"], name="Total value (AED)",
               marker_color=SECONDARY, opacity=0.35,
               hovertemplate="%{x|%b %Y}<br>Value: AED %{y:,.0f}<extra></extra>"),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(x=m["_sort"], y=m["Transactions"], name="Transactions",
                   mode="lines", line=dict(color=PRIMARY, width=2.2),
                   fill="tozeroy", fillcolor="rgba(37,99,235,0.12)",
                   hovertemplate="%{x|%b %Y}<br>Transactions: %{y:,}<extra></extra>"),
        secondary_y=False,
    )
    if len(m) >= 3:
        fig.add_trace(
            go.Scatter(x=m["_sort"], y=m["Transactions"].rolling(3, min_periods=1).mean(),
                       name="3-month average", mode="lines",
                       line=dict(color=AMBER, width=1.8, dash="dot"),
                       hovertemplate="%{x|%b %Y}<br>3-mo avg: %{y:,.0f}<extra></extra>"),
            secondary_y=False,
        )
    fig.update_layout(**layout(height=430, dark=dark))
    fig.update_yaxes(title_text="Transactions", secondary_y=False)
    fig.update_yaxes(title_text="Total value (AED)", secondary_y=True, showgrid=False)
    return fig


def annual_volume(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    t = yoy_table(df)
    colors = [PRIMARY if pd.isna(v) or v >= 0 else CHART_COLORS[4] for v in t["Volume YoY (%)"]]
    fig = go.Figure(go.Bar(
        x=t["Year"], y=t["Transactions"], marker_color=colors,
        text=[f"{v:,}" for v in t["Transactions"]], textposition="outside",
        hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>",
    ))
    fig.update_layout(**layout(height=380, dark=dark, show_legend=False))
    fig.update_yaxes(title_text="Transactions")
    fig.update_xaxes(title_text="Year", type="category")
    return fig


def quarterly_heatmap(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    pivot = (
        df.pivot_table(index=COL["year"], columns=COL["quarter"],
                       values=COL["price"], aggfunc="size")
        .sort_index()
    )
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"Q{c}" for c in pivot.columns],
        y=pivot.index.astype(str),
        colorscale=SEQUENTIAL, colorbar=dict(title="Deals"),
        hovertemplate="%{y} %{x}<br>Transactions: %{z:,}<extra></extra>",
    ))
    fig.update_layout(**layout(height=380, dark=dark, show_legend=False, hovermode="closest"))
    return fig


# Part 4 — smoothing window.
#
# Chosen by measuring, not by assumption. The monthly median-rate series has a
# month-on-month standard deviation of 7.61%. Centred rolling medians give:
#
#     window   3 →  4.36%   (43% calmer)
#     window   5 →  2.61%   (66% calmer)
#     window   7 →  2.27%   (70% calmer)
#     window  12 →  1.46%   (81% calmer)
#
# Twelve is used: it is one full year, so it removes the seasonal swing as well
# as the noise, and the trend still sits on the data (median deviation from the
# actual line is 2.75%). A rolling MEDIAN rather than a mean, because a single
# unusual month should not bend the trend. Every monthly observation is kept and
# remains selectable and tabulated — nothing is aggregated away.
SMOOTH_LABEL = "LOWESS"


def price_rate_trend(df: pd.DataFrame, dark: bool = False,
                     mode: str = "Both") -> tuple[go.Figure, pd.DataFrame]:
    """
    Monthly median sale price and median rate per m².

    `mode` is one of "Actual monthly", "Smoothed trend" or "Both".

    Smoothing is **LOWESS** — locally weighted regression, centred, three
    robustifying iterations. It was chosen over exponential smoothing on
    measured evidence from this dataset: it is both calmer (1.38% vs 3.82%
    month-on-month movement in the trend) and closer to the observations
    (2.61% vs 3.51% median deviation), because being centred it can use the
    months on either side of a point while exponential smoothing only looks
    backwards and must trail every turn. See `metrics.lowess_trend`.

    Two properties this implementation guarantees:

      * **No future values.** LOWESS is only defined over observed months, so
        the trend cannot extend past the last one. Nothing is extrapolated.
      * **The partial final month does not bend the trend.** A month the
        dataset ends part-way through carries a fraction of a normal month's
        transactions; it is excluded from the fit, and the trend line stops at
        the last complete month rather than diving toward an artefact.

    The span is re-selected from the length of the series, so the trend
    responds to the sidebar filters instead of being fixed to the unfiltered
    data. The actual monthly observations are never replaced or discarded.
    """
    m = monthly_series(df).copy()
    partial = partial_tail_months(m)
    m["smooth_price"] = lowess_trend(m["median_price"], exclude_tail=partial)
    m["smooth_rate"] = lowess_trend(m["median_rate"], exclude_tail=partial)

    show_actual = mode in ("Actual monthly", "Both")
    show_smooth = mode in ("Smoothed trend", "Both")
    faint = mode == "Both"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if show_actual:
        fig.add_trace(go.Scatter(
            x=m["_sort"], y=m["median_price"],
            name="Median sale price — actual" if faint else "Median sale price (AED)",
            mode="lines", line=dict(color=PRIMARY, width=1.0 if faint else 2.2),
            opacity=0.35 if faint else 1.0,
            hovertemplate="%{x|%b %Y}<br>Median price: AED %{y:,.0f}<extra></extra>"),
            secondary_y=False)
        fig.add_trace(go.Scatter(
            x=m["_sort"], y=m["median_rate"],
            name="Median rate — actual" if faint else "Median rate (AED/m²)",
            mode="lines", line=dict(color=SECONDARY, width=1.0 if faint else 2.2),
            opacity=0.35 if faint else 1.0,
            hovertemplate="%{x|%b %Y}<br>Median rate: AED %{y:,.0f}/m²<extra></extra>"),
            secondary_y=True)

    if show_smooth:
        fig.add_trace(go.Scatter(
            x=m["_sort"], y=m["smooth_price"],
            name=f"Median sale price — {SMOOTH_LABEL} smoothed trend",
            mode="lines", line=dict(color=PRIMARY, width=2.6),
            hovertemplate="%{x|%b %Y}<br>Trend price: AED %{y:,.0f}<extra></extra>"),
            secondary_y=False)
        fig.add_trace(go.Scatter(
            x=m["_sort"], y=m["smooth_rate"],
            name=f"Median rate — {SMOOTH_LABEL} smoothed trend",
            mode="lines", line=dict(color=SECONDARY, width=2.6),
            hovertemplate="%{x|%b %Y}<br>Trend rate: AED %{y:,.0f}/m²<extra></extra>"),
            secondary_y=True)

    # Shade the incomplete tail. This uses the SAME rule that excluded those
    # months from the LOWESS fit, so the shaded region and the point where the
    # trend line stops always agree.
    if partial:
        fig.add_vrect(
            x0=m["_sort"].iloc[-partial], x1=m["_sort"].iloc[-1] + pd.Timedelta(days=20),
            fillcolor="rgba(217,119,6,0.10)", line_width=0,
            annotation_text="partial month", annotation_position="top left",
            annotation_font_size=10)

    fig.update_layout(**layout(height=430, dark=dark))
    fig.update_yaxes(title_text="Median sale price (AED)", secondary_y=False)
    fig.update_yaxes(title_text="Median rate (AED/m²)", secondary_y=True, showgrid=False)
    return fig, m


def yoy_growth(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    t = yoy_table(df).dropna(subset=["Rate YoY (%)"])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=t["Year"], y=t["Volume YoY (%)"], name="Volume growth (%)",
        marker_color=[SECONDARY if v >= 0 else CHART_COLORS[4] for v in t["Volume YoY (%)"]],
        opacity=0.7, hovertemplate="%{x}<br>Volume: %{y:+.1f}%<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=t["Year"], y=t["Rate YoY (%)"], name="Rate growth (%)",
        mode="lines+markers", line=dict(color=PRIMARY, width=2.4, dash="dot"),
        hovertemplate="%{x}<br>Rate: %{y:+.1f}%<extra></extra>"), secondary_y=True)
    fig.update_layout(**layout(height=400, dark=dark))
    fig.update_xaxes(type="category", title_text="Year")
    fig.update_yaxes(title_text="Volume growth (%)", secondary_y=False)
    fig.update_yaxes(title_text="Rate growth (%)", secondary_y=True, showgrid=False)
    return fig


def seasonality(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m = df.groupby(COL["month"], observed=True).size().reindex(range(1, 13)).fillna(0)
    fig = go.Figure(go.Bar(
        x=names, y=m.values, marker_color=PRIMARY,
        hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>"))
    fig.add_hline(y=float(m.mean()), line_dash="dot", line_color=AMBER,
                  annotation_text="monthly average", annotation_position="top left")
    fig.update_layout(**layout(height=340, dark=dark, show_legend=False))
    fig.update_yaxes(title_text="Transactions (all years)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# GEOGRAPHY
# ─────────────────────────────────────────────────────────────────────────────


def top_areas_volume(df: pd.DataFrame, n: int = 15, dark: bool = False) -> go.Figure:
    s = df[COL["area"]].value_counts().head(n).sort_values()
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index.astype(str), orientation="h", marker_color=PRIMARY,
        text=[f"{v:,}" for v in s.values], textposition="outside",
        hovertemplate="%{y}<br>Transactions: %{x:,}<extra></extra>"))
    fig.update_layout(**layout(height=max(360, 26 * len(s)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Transactions")
    return fig


def top_areas_rate(df: pd.DataFrame, n: int = 15, min_n: int = 300, dark: bool = False) -> go.Figure:
    g = (df.groupby(COL["area"], observed=True)
           .agg(n=(COL["rate"], "size"), rate=(COL["rate"], "median"))
           .query(f"n >= {min_n}")
           .nlargest(n, "rate")
           .sort_values("rate"))
    fig = go.Figure(go.Bar(
        x=g["rate"], y=g.index.astype(str), orientation="h", marker_color=SECONDARY,
        text=[f"{v:,.0f}" for v in g["rate"]], textposition="outside",
        customdata=g["n"],
        hovertemplate="%{y}<br>Median rate: AED %{x:,.0f}/m²<br>Based on %{customdata:,} deals<extra></extra>"))
    fig.update_layout(**layout(height=max(360, 26 * len(g)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Median rate (AED/m²)")
    return fig


def area_treemap(df: pd.DataFrame, n: int = 25, dark: bool = False) -> go.Figure:
    g = (df.groupby(COL["area"], observed=True)
           .agg(value=(COL["price"], "sum"), n=(COL["price"], "size"),
                rate=(COL["rate"], "median"))
           .nlargest(n, "value").reset_index())
    fig = px.treemap(g, path=[COL["area"]], values="value", color="rate",
                     color_continuous_scale=SEQUENTIAL,
                     custom_data=["n", "rate"])
    fig.update_traces(hovertemplate=(
        "<b>%{label}</b><br>Total value: AED %{value:,.0f}"
        "<br>Transactions: %{customdata[0]:,}"
        "<br>Median rate: AED %{customdata[1]:,.0f}/m²<extra></extra>"))
    fig.update_layout(**layout(height=470, dark=dark, show_legend=False, hovermode="closest"))
    fig.update_layout(coloraxis_colorbar=dict(title="Rate<br>AED/m²"))
    return fig


def area_bubble(df: pd.DataFrame, n: int = 30, dark: bool = False) -> go.Figure:
    g = (df.groupby(COL["area"], observed=True)
           .agg(n=(COL["price"], "size"), med_price=(COL["price"], "median"),
                value=(COL["price"], "sum"), rate=(COL["rate"], "median"))
           .nlargest(n, "n").reset_index())
    fig = px.scatter(g, x="n", y="med_price", size="value", color="rate",
                     hover_name=COL["area"], size_max=52,
                     color_continuous_scale=SEQUENTIAL,
                     labels={"n": "Transactions", "med_price": "Median sale price (AED)",
                             "rate": "Median rate (AED/m²)"})
    fig.update_traces(hovertemplate=(
        "<b>%{hovertext}</b><br>Transactions: %{x:,}"
        "<br>Median price: AED %{y:,.0f}<extra></extra>"))
    fig.update_layout(**layout(height=460, dark=dark, show_legend=False, hovermode="closest"))
    fig.update_layout(coloraxis_colorbar=dict(title="Rate<br>AED/m²"))
    return fig


def zone_comparison(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    g = (df[df[COL["zone"]] != "Unknown"]
         .groupby(COL["zone"], observed=True)
         .agg(n=(COL["rate"], "size"), rate=(COL["rate"], "median"),
              price=(COL["price"], "median"))
         .query("n >= 100").sort_values("rate"))
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=g.index.astype(str), y=g["rate"], name="Median rate (AED/m²)",
        marker_color=PRIMARY, hovertemplate="%{x}<br>Rate: AED %{y:,.0f}/m²<extra></extra>"),
        secondary_y=False)
    fig.add_trace(go.Scatter(
        x=g.index.astype(str), y=g["n"], name="Transactions", mode="lines+markers",
        line=dict(color=AMBER, width=2, dash="dot"),
        hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>"), secondary_y=True)
    fig.update_layout(**layout(height=390, dark=dark))
    fig.update_yaxes(title_text="Median rate (AED/m²)", secondary_y=False)
    fig.update_yaxes(title_text="Transactions", secondary_y=True, showgrid=False)
    return fig


def metro_effect(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    g = (df.groupby(COL["metro_station"], observed=True)
           .agg(n=(COL["rate"], "size"), rate=(COL["rate"], "median"))
           .query("n >= 500").nlargest(15, "rate").sort_values("rate"))
    fig = go.Figure(go.Bar(
        x=g["rate"], y=g.index.astype(str), orientation="h", marker_color=VIOLET,
        customdata=g["n"], text=[f"{v:,.0f}" for v in g["rate"]], textposition="outside",
        hovertemplate="%{y}<br>Median rate: AED %{x:,.0f}/m²<br>%{customdata:,} deals<extra></extra>"))
    fig.update_layout(**layout(height=max(340, 26 * len(g)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Median rate (AED/m²)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PROPERTY
# ─────────────────────────────────────────────────────────────────────────────


def layout_mix(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    s = df[COL["rooms"]].value_counts()
    order = [r for r in _order_rooms(s.index) if r in s.index]
    s = s.reindex(order)
    fig = go.Figure(go.Bar(
        x=s.index.astype(str), y=s.values,
        marker_color=CHART_COLORS[: len(s)],
        text=[f"{v:,}" for v in s.values], textposition="outside",
        hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>"))
    fig.update_layout(**layout(height=380, dark=dark, show_legend=False))
    fig.update_yaxes(title_text="Transactions")
    return fig


def rate_by_layout(df: pd.DataFrame, dark: bool = False, min_n: int = 100):
    """
    Small-multiples box plot — one panel per layout.

    A single combined box plot stacked nine layouts on one x-position and was
    unreadable. Each layout now gets its own panel on a shared y-scale, so the
    distributions can actually be compared.

    Returns (figure, stats_frame, excluded_frame). No transaction is deleted:
    layouts below `min_n` are reported in `excluded` rather than silently
    dropped, and values beyond the whiskers are summarised in `stats`.
    """
    order = _order_rooms(df[COL["rooms"]].dropna().unique())
    counts = df[COL["rooms"]].value_counts()

    kept = [r for r in order if counts.get(r, 0) >= min_n]
    dropped = [r for r in order if 0 < counts.get(r, 0) < min_n]

    excluded = pd.DataFrame(
        [{"Layout": r, "Transactions": int(counts.get(r, 0)),
          "Median rate (AED/m²)": float(df.loc[df[COL["rooms"]] == r, COL["rate"]].median())}
         for r in dropped]
    )

    if not kept:
        return go.Figure(), pd.DataFrame(), excluded

    stats = _box_stats(df[df[COL["rooms"]].isin(kept)], COL["rooms"], COL["rate"], kept)

    fig = make_subplots(rows=1, cols=len(kept), shared_yaxes=True,
                        horizontal_spacing=0.012,
                        subplot_titles=[f"{r}<br><span style='font-size:0.72em;opacity:.65'>"
                                        f"{int(stats.loc[r, 'n']):,} deals</span>" for r in kept])
    for i, name in enumerate(kept, start=1):
        row = stats.loc[name]
        fig.add_trace(
            go.Box(x=[name], q1=[row["q1"]], median=[row["med"]], q3=[row["q3"]],
                   lowerfence=[row["lower"]], upperfence=[row["upper"]],
                   name=str(name), marker_color=CHART_COLORS[(i - 1) % len(CHART_COLORS)],
                   width=0.55, showlegend=False,
                   hovertemplate=(f"<b>{name}</b><br>Upper whisker: %{{upperfence:,.0f}}"
                                  "<br>75th pct: %{q3:,.0f}<br>Median: %{median:,.0f}"
                                  "<br>25th pct: %{q1:,.0f}"
                                  "<br>Lower whisker: %{lowerfence:,.0f}<extra></extra>")),
            row=1, col=i)
        fig.add_hline(y=row["med"], line_dash="dot", line_width=1,
                      line_color="rgba(128,128,128,0.35)", row=1, col=i)

    fig.update_layout(**layout(height=430, dark=dark, show_legend=False, hovermode="closest"))
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_yaxes(title_text="Rate per m² (AED)", row=1, col=1)
    for ann in fig.layout.annotations:
        ann.font.size = 11
    return fig, stats, excluded


def layout_stats_table(stats: pd.DataFrame) -> pd.DataFrame:
    """Readable companion table for the layout panels."""
    if stats.empty:
        return pd.DataFrame()
    t = stats.reset_index()
    t.columns = ["Layout", "25th pct", "Median", "75th pct",
                 "Lower whisker", "Upper whisker", "Transactions"]
    t["IQR"] = t["75th pct"] - t["25th pct"]
    return t[["Layout", "Transactions", "Lower whisker", "25th pct", "Median",
              "75th pct", "Upper whisker", "IQR"]]


def reg_type_split(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    s = df[COL["reg_type"]].value_counts()
    fig = go.Figure(go.Pie(
        labels=s.index.astype(str), values=s.values, hole=0.55,
        marker=dict(colors=[PRIMARY, SECONDARY, AMBER, VIOLET][: len(s)]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:,} deals (%{percent})<extra></extra>"))
    fig.update_layout(**layout(height=360, dark=dark, show_legend=False, hovermode="closest"))
    return fig


def procedure_split(df: pd.DataFrame, n: int = 6, dark: bool = False) -> go.Figure:
    s = df[COL["procedure"]].value_counts().head(n)
    fig = go.Figure(go.Pie(
        labels=s.index.astype(str), values=s.values, hole=0.55,
        marker=dict(colors=CHART_COLORS[: len(s)]), textinfo="percent",
        hovertemplate="%{label}<br>%{value:,} deals (%{percent})<extra></extra>"))
    fig.update_layout(**layout(height=360, dark=dark, hovermode="closest"))
    return fig


def size_vs_price(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    sample = df if len(df) <= SCATTER_SAMPLE else df.sample(SCATTER_SAMPLE, random_state=42)
    order = _order_rooms(sample[COL["rooms"]].dropna().unique())
    fig = px.scatter(sample, x=COL["area_sqm"], y=COL["price"], color=COL["rooms"],
                     category_orders={COL["rooms"]: order},
                     color_discrete_sequence=CHART_COLORS, opacity=0.45,
                     labels={COL["area_sqm"]: "Unit size (m²)", COL["price"]: "Sale price (AED)",
                             COL["rooms"]: "Layout"})
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(**layout(height=460, dark=dark, hovermode="closest"))
    return fig


def size_by_layout(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    order = _order_rooms(df[COL["rooms"]].dropna().unique())
    g = (df.groupby(COL["rooms"], observed=True)[COL["area_sqm"]]
           .median().reindex(order).dropna())
    fig = go.Figure(go.Bar(
        x=g.index.astype(str), y=g.values, marker_color=SECONDARY,
        text=[f"{v:,.0f} m²" for v in g.values], textposition="outside",
        hovertemplate="%{x}<br>Median size: %{y:,.0f} m²<extra></extra>"))
    fig.update_layout(**layout(height=360, dark=dark, show_legend=False))
    fig.update_yaxes(title_text="Median unit size (m²)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PRICE
# ─────────────────────────────────────────────────────────────────────────────


def price_histogram(df: pd.DataFrame, column: str, title: str, unit: str,
                    dark: bool = False, nbins: int = 60) -> go.Figure:
    """
    Histogram with the binning done in numpy rather than in the browser.

    `go.Histogram` ships every raw value to the client — several megabytes per
    chart at this row count. Binning server-side produces the identical chart
    from a few dozen numbers.
    """
    s = df[column].dropna().to_numpy(dtype="float64")
    if s.size == 0:
        return go.Figure()
    lo, hi = np.quantile(s, [0.005, 0.995])
    trimmed = s[(s >= lo) & (s <= hi)]
    counts, edges = np.histogram(trimmed, bins=nbins)
    centres = (edges[:-1] + edges[1:]) / 2
    width = float(edges[1] - edges[0])
    median = float(np.median(s))

    fig = go.Figure(go.Bar(
        x=centres, y=counts, width=width, marker_color=PRIMARY, opacity=0.9,
        hovertemplate=f"{unit} %{{x:,.0f}}<br>Transactions: %{{y:,}}<extra></extra>"))
    fig.add_vline(x=median, line_dash="dash", line_color=AMBER,
                  annotation_text=f"median {median:,.0f}", annotation_position="top right")
    fig.update_layout(**layout(title=title, height=380, dark=dark,
                               show_legend=False, hovermode="closest"), bargap=0.02)
    fig.update_yaxes(title_text="Transactions")
    return fig


def rate_by_reg_type_over_time(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    g = (df.groupby([COL["year"], COL["reg_type"]], observed=True)[COL["rate"]]
           .median().reset_index())
    fig = px.line(g, x=COL["year"], y=COL["rate"], color=COL["reg_type"],
                  markers=True, color_discrete_sequence=[PRIMARY, SECONDARY, AMBER],
                  labels={COL["year"]: "Year", COL["rate"]: "Median rate (AED/m²)",
                          COL["reg_type"]: ""})
    fig.update_layout(**layout(height=400, dark=dark))
    return fig


def offplan_premium(premium: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Off-plan premium (or discount) against existing property, per year."""
    if premium.empty:
        return go.Figure()
    colors = [SECONDARY if v >= 0 else CHART_COLORS[4] for v in premium["Premium (%)"]]
    fig = go.Figure(go.Bar(
        x=premium["Year"], y=premium["Premium (%)"], marker_color=colors,
        text=[f"{v:+.0f}%" for v in premium["Premium (%)"]], textposition="outside",
        customdata=premium[["Off-plan deals", "Existing deals"]],
        hovertemplate=("%{x}<br>Premium: %{y:+.1f}%"
                       "<br>%{customdata[0]:,} off-plan vs %{customdata[1]:,} existing"
                       "<extra></extra>")))
    fig.add_hline(y=0, line_color="rgba(128,128,128,0.6)")
    fig.update_traces(cliponaxis=False)
    fig.update_layout(**layout(height=380, dark=dark, show_legend=False))
    fig.update_xaxes(type="category", title_text="Year")
    fig.update_yaxes(title_text="Off-plan premium vs existing (%)")
    return fig


def amenity_bar(effects: list[dict], dark: bool = False) -> go.Figure:
    if not effects:
        return go.Figure()
    labels = [e["label"] for e in effects]
    deltas = [e["rate_delta_pct"] for e in effects]
    colors = [SECONDARY if d >= 0 else CHART_COLORS[4] for d in deltas]
    counts = [e["n_with"] for e in effects]
    fig = go.Figure(go.Bar(
        x=deltas, y=labels, orientation="h", marker_color=colors,
        text=[f"{d:+.1f}%" for d in deltas], textposition="outside",
        customdata=counts,
        hovertemplate="%{y}<br>Median rate difference: %{x:+.1f}%<br>%{customdata:,} units with it<extra></extra>"))
    fig.add_vline(x=0, line_color="rgba(128,128,128,0.5)")
    fig.update_traces(cliponaxis=False)
    span = max(abs(min(deltas)), abs(max(deltas))) * 1.28 or 1
    fig.update_layout(**layout(height=max(320, 46 * len(labels)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Median rate difference vs units without it (%)",
                     range=[min(min(deltas), 0) - span * 0.12, max(max(deltas), 0) + span * 0.18])
    return fig


def amenity_like_for_like_bar(table: pd.DataFrame, dark: bool = False) -> go.Figure:
    if table.empty:
        return go.Figure()
    t = table.sort_values("Median rate difference (%)")
    colors = [SECONDARY if d >= 0 else CHART_COLORS[4] for d in t["Median rate difference (%)"]]
    fig = go.Figure(go.Bar(
        x=t["Median rate difference (%)"], y=t["Amenity"], orientation="h",
        marker_color=colors, customdata=t[["Groups", "Deals"]],
        text=[f"{d:+.1f}%" for d in t["Median rate difference (%)"]], textposition="outside",
        hovertemplate=("%{y}<br>Difference: %{x:+.1f}%"
                       "<br>%{customdata[0]} area × layout groups"
                       "<br>%{customdata[1]:,} transactions<extra></extra>")))
    fig.add_vline(x=0, line_color="rgba(128,128,128,0.5)")
    fig.update_traces(cliponaxis=False)
    d = t["Median rate difference (%)"]
    span = max(abs(d.min()), abs(d.max())) * 1.28 or 1
    fig.update_layout(**layout(height=max(320, 46 * len(t)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Like-for-like median rate difference (%)",
                     range=[min(d.min(), 0) - span * 0.22, max(d.max(), 0) + span * 0.18])
    return fig


def control_ladder(ladder: pd.DataFrame, label: str, dark: bool = False) -> go.Figure:
    """
    A price gap, measured under progressively fairer comparisons.

    Read top to bottom. The top bar is the straight comparison — everything on
    one side against everything on the other, whatever kind of property they
    are. Each bar below it compares only properties that match on one more
    characteristic, and the bottom bar is the fair one. A gap that collapses on
    the way down was describing the property mix, not the thing being measured.

    Used by both the amenity section and the off-plan section, so the two make
    the same argument in the same shape.
    """
    if ladder.empty:
        return go.Figure()

    # Plotly draws the first category at the bottom of a horizontal bar chart,
    # so reversing here puts the raw comparison at the TOP and the fair one at
    # the bottom — the order the caption asks the reader to follow.
    t = ladder.iloc[::-1]
    gaps = t["Gap (%)"]
    fairest = ladder["Held constant"].max()
    colors, opacity = [], []
    for _, row in t.iterrows():
        if row["Held constant"] == fairest:
            colors.append(SECONDARY if row["Gap (%)"] >= 0 else CHART_COLORS[4])
            opacity.append(1.0)
        elif row["Held constant"] == 0:
            colors.append("#B45309")         # the raw number — amber, handle with care
            opacity.append(0.95)
        else:
            colors.append("#94A3B8")
            opacity.append(0.85)

    fig = go.Figure(go.Bar(
        x=gaps, y=t["Comparison"], orientation="h",
        marker=dict(color=colors, opacity=opacity),
        customdata=t[["Groups", "Deals"]],
        text=[f"{g:+.1f}%" for g in gaps], textposition="outside",
        hovertemplate=("%{y}<br>Gap: %{x:+.1f}%"
                       "<br>%{customdata[0]:,} comparable groups"
                       "<br>%{customdata[1]:,} transactions<extra></extra>")))
    fig.add_vline(x=0, line_color="rgba(128,128,128,0.55)")
    fig.update_traces(cliponaxis=False)

    span = max(abs(gaps.min()), abs(gaps.max())) or 1
    fig.update_layout(**layout(height=max(300, 64 * len(t)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text=f"Difference in median rate per m² — {label} (%)",
                     range=[min(gaps.min(), 0) - span * 0.30,
                            max(gaps.max(), 0) + span * 0.22])
    fig.update_yaxes(automargin=True)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# v1.3 — RAW transaction volume · amenity within property type · building height
# ═════════════════════════════════════════════════════════════════════════════


def raw_transaction_volume(years: pd.DataFrame, partial: dict,
                           dark: bool = False) -> go.Figure:
    """
    Recorded transactions per year from the RAW registry, with year-over-year
    growth on a secondary axis.

    DATA SOURCE: RAW. Completed years carry a growth point. The latest year is
    plotted as a count only unless its like-for-like growth is strictly
    positive — an incomplete year compared against a full one is not a decline,
    it is an artefact of the calendar, so no negative percentage is drawn.
    """
    if years.empty:
        return go.Figure()

    t = years.copy()
    latest = int(t["year"].max())
    period = (partial or {}).get("period_label", "part year")

    # Two bar series rather than one. Splitting the incomplete year into its own
    # series gives it its own legend entry naming the period it covers and its
    # own hover text, so a shorter bar can never be read as a fall.
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    done, todo = t[t["complete"]], t[~t["complete"]]

    fig.add_trace(
        go.Bar(x=done["year"], y=done["transactions"], name="Transactions recorded",
               marker_color=PRIMARY,
               text=[f"{v:,}" for v in done["transactions"]], textposition="outside",
               customdata=done["all_transactions"],
               hovertemplate=("<b>%{x}</b><br>Transactions recorded: %{y:,}"
                              "<br>All registry transactions: %{customdata:,}"
                              "<extra></extra>")),
        secondary_y=False)

    if not todo.empty:
        fig.add_trace(
            go.Bar(x=todo["year"], y=todo["transactions"],
                   name=f"{int(todo['year'].iloc[0])} — {period} only (in progress)",
                   marker_color=AMBER,
                   text=[f"{v:,}" for v in todo["transactions"]], textposition="outside",
                   customdata=todo["all_transactions"],
                   hovertemplate=("<b>%{x} — " + period + " only</b>"
                                  "<br>Transactions recorded so far: %{y:,}"
                                  "<br>All registry transactions: %{customdata:,}"
                                  "<br><i>Part year — not comparable with a full year"
                                  "</i><extra></extra>")),
            secondary_y=False)

    # Growth line: completed years only. The incomplete year is deliberately
    # absent unless the caller supplied a strictly positive figure.
    line = t[["year", "yoy_pct"]].copy()
    display_growth = partial.get("display_growth") if partial else None
    if display_growth is not None:
        line.loc[line["year"] == latest, "yoy_pct"] = display_growth
    line = line.dropna(subset=["yoy_pct"])

    if not line.empty:
        fig.add_trace(
            go.Scatter(x=line["year"], y=line["yoy_pct"],
                       name="Year-over-year growth (%)", mode="lines+markers",
                       line=dict(color=SECONDARY, width=2.2, dash="dot"),
                       marker=dict(size=7),
                       hovertemplate="<b>%{x}</b><br>Growth vs previous year: %{y:+.1f}%"
                                     "<extra></extra>"),
            secondary_y=True)
        fig.add_hline(y=0, line_color="rgba(128,128,128,0.45)", line_width=1,
                      secondary_y=True)

    fig.update_layout(**layout(height=440, dark=dark, show_legend=True))
    fig.update_yaxes(title_text="Transactions recorded", secondary_y=False)
    fig.update_yaxes(title_text="Year-over-year growth (%)", secondary_y=True, showgrid=False)
    fig.update_xaxes(title_text="Year", type="category")
    fig.update_traces(cliponaxis=False, selector=dict(type="bar"))
    fig.update_layout(barmode="group")
    return fig


def amenity_within_property_type(result: dict, dark: bool = False) -> go.Figure:
    """
    Median rate per m² for units recorded WITH and WITHOUT one amenity, inside a
    single property type.

    Two bars, each labelled with its own transaction count. The quartile range
    is drawn as an error bar so the reader can see how much the two groups
    overlap before reading anything into the gap between the medians.
    """
    if not result or not result.get("enough"):
        return go.Figure()

    names = [f"With {result['amenity'].lower()}", f"Without {result['amenity'].lower()}"]
    medians = [result["median_rate_with"], result["median_rate_without"]]
    p25 = [result["p25_rate_with"], result["p25_rate_without"]]
    p75 = [result["p75_rate_with"], result["p75_rate_without"]]
    counts = [result["n_with"], result["n_without"]]
    sizes = [result["median_size_with"], result["median_size_without"]]

    fig = go.Figure()
    for i, (name, med) in enumerate(zip(names, medians)):
        fig.add_trace(go.Bar(
            x=[name], y=[med], name=name,
            marker_color=SECONDARY if i == 0 else CHART_COLORS[3],
            error_y=dict(type="data", symmetric=False,
                         array=[p75[i] - med], arrayminus=[med - p25[i]],
                         color="rgba(100,116,139,0.75)", thickness=1.4, width=8),
            text=[f"AED {med:,.0f}"], textposition="outside",
            customdata=[[counts[i], p25[i], p75[i], sizes[i]]],
            hovertemplate=("<b>%{x}</b><br>Median rate: AED %{y:,.0f}/m²"
                           "<br>Transactions: %{customdata[0]:,}"
                           "<br>Middle half of sales: AED %{customdata[1]:,.0f}"
                           " – %{customdata[2]:,.0f}/m²"
                           "<br>Median unit size: %{customdata[3]:,.0f} m²<extra></extra>")))

    top = max(p75) * 1.16
    fig.update_layout(**layout(height=420, dark=dark, show_legend=True))
    fig.update_yaxes(title_text="Median rate (AED/m²)", range=[0, top])
    fig.update_xaxes(title_text=f"{result['label']} — recorded amenity status")
    fig.update_traces(cliponaxis=False)
    return fig


def rate_by_building_height(frame: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Median rate per m² by building-height band, one series per property type.

    The legend is the property type, which is the point of the chart: it lets
    the reader see whether height moves price the same way for a studio as for
    a three-bedroom.
    """
    if frame.empty:
        return go.Figure()

    order = [l for l in PROPERTY_TYPE_LABELS.values()
             if l in set(frame["Property type"])]
    fig = go.Figure()
    for i, ptype in enumerate(order):
        d = frame[frame["Property type"] == ptype]
        fig.add_trace(go.Bar(
            x=d["height_band"].astype(str), y=d["median_rate"], name=ptype,
            marker_color=CHART_COLORS[i % len(CHART_COLORS)],
            customdata=d[["transactions", "mean_rate"]],
            hovertemplate=(f"<b>{ptype}</b><br>%{{x}}"
                           "<br>Median rate: AED %{y:,.0f}/m²"
                           "<br>Mean rate: AED %{customdata[1]:,.0f}/m²"
                           "<br>Transactions: %{customdata[0]:,}<extra></extra>")))

    fig.update_layout(**layout(height=470, dark=dark, show_legend=True), barmode="group")
    fig.update_yaxes(title_text="Median rate (AED/m²)")
    fig.update_xaxes(title_text="Building height band")
    return fig


def amenity_share_bar(table: pd.DataFrame, highlight: str, title_axis: str,
                      dark: bool = False) -> go.Figure:
    """
    Share of recorded transactions associated with each amenity.

    A share of completed transactions — not a purchase probability. The selected
    amenity is drawn in the accent colour so the two filters visibly interact.
    """
    if table.empty:
        return go.Figure()
    t = table.iloc[::-1]
    colors = [SECONDARY if a == highlight else "#94A3B8" for a in t["Amenity"]]
    fig = go.Figure(go.Bar(
        x=t["Share of recorded transactions (%)"], y=t["Amenity"], orientation="h",
        marker_color=colors,
        customdata=t[["Transactions with amenity recorded", "Transactions without"]],
        text=[f"{v:.1f}%" for v in t["Share of recorded transactions (%)"]],
        textposition="outside",
        hovertemplate=("%{y}<br>Share of recorded transactions: %{x:.1f}%"
                       "<br>Recorded with: %{customdata[0]:,}"
                       "<br>Recorded without: %{customdata[1]:,}<extra></extra>")))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(**layout(height=360, dark=dark, show_legend=False))
    fig.update_xaxes(title_text=title_axis, range=[0, 112])
    return fig

def amenity_share_grouped(table: pd.DataFrame, highlight: str, scope_label: str,
                          dark: bool = False) -> go.Figure:
    """
    Amenity analysis: the selected slice beside the Dubai-wide baseline.

    A grouped bar — two plain bars per amenity, side by side. Not stacked, and
    not a ranking of raw shares.

    The previous version ranked amenities by raw recorded share. Parking is
    recorded on 88.9%-100.0% of transactions in every property type, so it won
    that ranking every time and read as "parking matters most" — which was a
    statement about which field the registry fills in, not about the market.
    Here a near-constant sits level with its own baseline and shows no gap,
    while a genuine difference stands out.

    Height is how often a feature appears ON THE RECORD. It is not value, not
    demand, not price, and not an effect.
    """
    if table.empty:
        return go.Figure()

    order = list(table["Amenity"])
    sel_colour = [SECONDARY if a == highlight else "#7DD3C0" for a in order]
    base_colour = ["#64748B" if a == highlight else "#CBD5E1" for a in order]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=order, y=table["Share in selection (%)"], name=scope_label,
        marker_color=sel_colour,
        text=[f"{v:.1f}%" for v in table["Share in selection (%)"]],
        textposition="outside", cliponaxis=False,
        customdata=table[["Recorded with (selection)", "Transactions (selection)",
                          "Difference (pp)"]],
        hovertemplate="<b>%{x}</b><br>" + scope_label + ": %{y:.1f}%"
                      "<br>Recorded with: %{customdata[0]:,} of %{customdata[1]:,}"
                      "<br>Difference vs Dubai: %{customdata[2]:+.1f} pp<extra></extra>"))
    fig.add_trace(go.Bar(
        x=order, y=table["Share across Dubai (%)"], name="All Dubai (current filters)",
        marker_color=base_colour,
        text=[f"{v:.1f}%" for v in table["Share across Dubai (%)"]],
        textposition="outside", cliponaxis=False,
        customdata=table[["Recorded with (Dubai)", "Transactions (Dubai)"]],
        hovertemplate="<b>%{x}</b><br>All Dubai: %{y:.1f}%"
                      "<br>Recorded with: %{customdata[0]:,} of %{customdata[1]:,}"
                      "<extra></extra>"))

    fig.update_layout(**layout(height=430, dark=dark, show_legend=True,
                               hovermode="x unified"), barmode="group", bargap=0.28)
    fig.update_yaxes(title_text="Share of recorded transactions (%)", range=[0, 118])
    fig.update_xaxes(title_text="Amenity")
    return fig


def amenity_share_by_type_bar(table: pd.DataFrame, amenity: str,
                              dark: bool = False) -> go.Figure:
    """The same share for one amenity, across property types."""
    if table.empty:
        return go.Figure()
    fig = go.Figure(go.Bar(
        x=table["Property type"], y=table["Share of recorded transactions (%)"],
        marker_color=PRIMARY,
        customdata=table[["Transactions", "With amenity recorded"]],
        text=[f"{v:.1f}%" for v in table["Share of recorded transactions (%)"]],
        textposition="outside",
        hovertemplate=("%{x}<br>Share of recorded transactions: %{y:.1f}%"
                       "<br>Transactions of this type: %{customdata[0]:,}"
                       "<br>Recorded with " + amenity.lower() + ": %{customdata[1]:,}"
                       "<extra></extra>")))
    fig.update_traces(cliponaxis=False)
    fig.update_layout(**layout(height=360, dark=dark, show_legend=False))
    fig.update_yaxes(title_text=f"Share recorded with {amenity.lower()} (%)", range=[0, 112])
    fig.update_xaxes(title_text="Property type")
    return fig


def volume_vs_mean_rate(table: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Transaction volume (RAW) against MEAN rate per m² (CLEANED), by year.

    Volume as bars on the left axis, mean rate as a line on the right. Mean
    rather than median on purpose — see `metrics.volume_vs_mean_rate`.
    """
    if table.empty:
        return go.Figure()

    t = table.copy()
    done, todo = t[t["complete"]], t[~t["complete"]]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=done["year"], y=done["transactions"], name="Transaction volume (raw)",
               marker_color=PRIMARY, opacity=0.85,
               hovertemplate="<b>%{x}</b><br>Transaction volume: %{y:,}<extra></extra>"),
        secondary_y=False)
    if not todo.empty:
        fig.add_trace(
            go.Bar(x=todo["year"], y=todo["transactions"],
                   name=f"{int(todo['year'].iloc[0])} — part year (in progress)",
                   marker_color=AMBER, opacity=0.9,
                   hovertemplate="<b>%{x} — part year</b><br>Transaction volume so far: "
                                 "%{y:,}<extra></extra>"),
            secondary_y=False)

    fig.add_trace(
        go.Scatter(x=t["year"], y=t["mean_rate"], name="Mean rate per m² (cleaned)",
                   mode="lines+markers", line=dict(color=SECONDARY, width=2.6),
                   marker=dict(size=7),
                   hovertemplate="<b>%{x}</b><br>Mean rate: AED %{y:,.0f}/m²<extra></extra>"),
        secondary_y=True)

    fig.update_layout(**layout(height=440, dark=dark, show_legend=True), barmode="group")
    fig.update_yaxes(title_text="Transaction volume (raw registry)", secondary_y=False)
    fig.update_yaxes(title_text="Mean rate per m² (AED/m²)", secondary_y=True, showgrid=False)
    fig.update_xaxes(title_text="Year", type="category")
    return fig


def forecast_chart(quarterly: pd.DataFrame, area: str, dark: bool = False) -> go.Figure:
    """Published ARIMA quarterly fit + forecast with confidence band, for one area."""
    d = quarterly[quarterly["area_name_en"] == area].copy()
    d["ds"] = pd.to_datetime(d["ds"])
    d = d.sort_values("ds")
    fc = d[d["type"] != "fitted"]

    fig = go.Figure()
    if not fc.empty:
        fig.add_trace(go.Scatter(
            x=list(fc["ds"]) + list(fc["ds"][::-1]),
            y=list(fc["yhat_upper"]) + list(fc["yhat_lower"][::-1]),
            fill="toself", fillcolor="rgba(37,99,235,0.13)",
            line=dict(color="rgba(0,0,0,0)"), name="Confidence band", hoverinfo="skip"))
    actual = d[d["actual"].notna()]
    fig.add_trace(go.Scatter(
        x=actual["ds"], y=actual["actual"], name="Actual", mode="lines+markers",
        line=dict(color="#64748B", width=2),
        hovertemplate="%{x|%Y Q%q}<br>Actual: AED %{y:,.0f}/m²<extra></extra>"))
    fitted = d[d["type"] == "fitted"]
    if not fitted.empty:
        fig.add_trace(go.Scatter(
            x=fitted["ds"], y=fitted["yhat"], name="Model fit", mode="lines",
            line=dict(color=SECONDARY, width=1.8, dash="dot"),
            hovertemplate="%{x|%Y Q%q}<br>Fitted: AED %{y:,.0f}/m²<extra></extra>"))
    if not fc.empty:
        fig.add_trace(go.Scatter(
            x=fc["ds"], y=fc["yhat"], name="Forecast", mode="lines+markers",
            line=dict(color=PRIMARY, width=2.6),
            hovertemplate="%{x|%Y Q%q}<br>Forecast: AED %{y:,.0f}/m²<extra></extra>"))
    fig.update_layout(**layout(height=430, dark=dark))
    fig.update_yaxes(title_text="Rate (AED/m²)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# DISTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────


def rate_violin_by_year(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    sample = df if len(df) <= 45_000 else df.sample(45_000, random_state=42)
    fig = px.violin(sample, x=COL["year"], y=COL["rate"], color=COL["year"],
                    color_discrete_sequence=CHART_COLORS, box=True, points=False,
                    labels={COL["year"]: "Year", COL["rate"]: "Rate (AED/m²)"})
    fig.update_layout(**layout(height=440, dark=dark, show_legend=False, hovermode="closest"))
    fig.update_xaxes(type="category")
    return fig


def price_box_by_reg_type(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    stats = _box_stats(df, COL["reg_type"], COL["price"])
    fig = go.Figure()
    for i, (name, row) in enumerate(stats.iterrows()):
        fig.add_trace(go.Box(
            name=str(name), q1=[row["q1"]], median=[row["med"]], q3=[row["q3"]],
            lowerfence=[row["lower"]], upperfence=[row["upper"]],
            marker_color=[PRIMARY, SECONDARY][i % 2],
            hovertext=f"{int(row['n']):,} transactions"))
    fig.update_layout(**layout(height=400, dark=dark, show_legend=False, hovermode="closest"))
    fig.update_yaxes(type="log", title_text="Sale price (AED, log scale)")
    return fig


def band_bar(bands: pd.DataFrame, dark: bool = False) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=bands["Price band (AED)"], y=bands["Transactions"], marker_color=PRIMARY,
        text=[f"{v:.1f}%" for v in bands["Share (%)"]], textposition="outside",
        hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>"))
    fig.update_layout(**layout(height=380, dark=dark, show_legend=False))
    fig.update_yaxes(title_text="Transactions")
    return fig


def pareto(df: pd.DataFrame, column: str, dark: bool = False, top_n: int = 25) -> go.Figure:
    """Cumulative share of transaction value by group — the classic ABC view."""
    g = (df.groupby(column, observed=True)[COL["price"]].sum()
           .sort_values(ascending=False))
    total = g.sum()
    head = g.head(top_n)
    cum = head.cumsum() / total * 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=head.index.astype(str), y=head.values, name="Total value (AED)",
        marker_color=PRIMARY, hovertemplate="%{x}<br>Value: AED %{y:,.0f}<extra></extra>"),
        secondary_y=False)
    fig.add_trace(go.Scatter(
        x=cum.index.astype(str), y=cum.values, name="Cumulative share (%)",
        mode="lines+markers", line=dict(color=AMBER, width=2.2),
        hovertemplate="%{x}<br>Cumulative: %{y:.1f}%<extra></extra>"), secondary_y=True)
    fig.add_hline(y=80, line_dash="dot", line_color="rgba(128,128,128,0.6)", secondary_y=True)
    fig.update_layout(**layout(height=430, dark=dark))
    fig.update_yaxes(title_text="Total value (AED)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative share (%)", secondary_y=True,
                     range=[0, 105], showgrid=False)
    return fig


def tier_rate_bar(df: pd.DataFrame, column: str, dark: bool = False, min_n: int = 200) -> go.Figure:
    g = (df[df[column] != "Unknown"]
         .groupby(column, observed=True)
         .agg(n=(COL["rate"], "size"), rate=(COL["rate"], "median"))
         .query(f"n >= {min_n}").sort_values("rate"))
    if g.empty:
        return go.Figure()
    fig = go.Figure(go.Bar(
        x=g["rate"], y=g.index.astype(str), orientation="h", marker_color=PRIMARY,
        customdata=g["n"], text=[f"{v:,.0f}" for v in g["rate"]], textposition="outside",
        hovertemplate="%{y}<br>Median rate: AED %{x:,.0f}/m²<br>%{customdata:,} deals<extra></extra>"))
    fig.update_layout(**layout(height=max(300, 34 * len(g)), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Median rate (AED/m²)")
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# v1.4 — top areas inside a price bracket, and the smoothing method review
# ═════════════════════════════════════════════════════════════════════════════


def top_areas_in_band(table: pd.DataFrame, band: str, dark: bool = False) -> go.Figure:
    """
    Horizontal ranked bar of the busiest areas inside one sale-price bracket.

    Rank 1 is drawn at the top. The area names come from the data — nothing
    about this chart is hard-coded.
    """
    t = table[table["Price band (AED)"] == band].sort_values("Rank")
    fig = go.Figure()
    if t.empty:
        fig.update_layout(**layout(height=260, dark=dark, show_legend=False))
        return fig

    # Plotly draws the first category at the bottom, so reverse to put rank 1 on top.
    r = t.iloc[::-1]
    fig.add_trace(go.Bar(
        x=r["Transactions"], y=[f"{int(k)}. {a}" for k, a in zip(r["Rank"], r["Area"])],
        orientation="h", marker_color=PRIMARY,
        text=[f"{v:,}" for v in r["Transactions"]], textposition="outside",
        customdata=r[["Share of band (%)"]],
        hovertemplate="%{y}<br>Transactions: %{x:,}"
                      "<br>Share of this bracket: %{customdata[0]:.1f}%<extra></extra>",
        name="Transactions"))
    fig.update_layout(**layout(height=max(240, 52 * len(t) + 90), dark=dark,
                               show_legend=False, hovermode="closest"))
    fig.update_xaxes(title_text="Transactions in this price bracket")
    fig.update_yaxes(title_text="")
    return fig


def smoothing_experiment_chart(frame: pd.DataFrame, report: dict, view: str = "Both",
                               dark: bool = False) -> go.Figure:
    """
    Version A (LOWESS) and Version B (exponential smoothing) over one identical
    actual series. Research material for the Experimental Analysis environment.

    Both are smoothers of observed months. Neither continues past the last
    observation, and neither is a forecast.
    """
    fig = go.Figure()
    if frame.empty:
        fig.update_layout(**layout(height=320, dark=dark, show_legend=False))
        return fig

    fig.add_trace(go.Scatter(
        x=frame["_sort"], y=frame["actual"], name="Actual monthly median (shared source)",
        mode="lines", line=dict(color="#94A3B8", width=1.0), opacity=0.8,
        hovertemplate="%{x|%b %Y}<br>Actual: AED %{y:,.0f}/m²<extra></extra>"))

    if view in ("Both", "Version A — LOWESS"):
        fig.add_trace(go.Scatter(
            x=frame["_sort"], y=frame["lowess"],
            name=f"Version A — LOWESS (span ≈{report['lowess']['window_months']:.0f} months)",
            mode="lines", line=dict(color=PRIMARY, width=2.8),
            hovertemplate="%{x|%b %Y}<br>LOWESS: AED %{y:,.0f}/m²<extra></extra>"))

    if view in ("Both", "Version B — Exponential smoothing"):
        fig.add_trace(go.Scatter(
            x=frame["_sort"], y=frame["exponential"],
            name=f"Version B — Exponential smoothing (α {report['exponential']['alpha']:.2f})",
            mode="lines", line=dict(color=AMBER, width=2.8, dash="dot"),
            hovertemplate="%{x|%b %Y}<br>Exponential: AED %{y:,.0f}/m²<extra></extra>"))

    fig.update_layout(**layout(height=470, dark=dark, show_legend=True))
    fig.update_yaxes(title_text="Median rate per m² (AED/m²)")
    fig.update_xaxes(title_text="Month")
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# FORECAST API — the live TruEstate forecast endpoint
#
# Everything drawn below is a value returned by the API. Nothing on this chart
# is smoothed, interpolated, extrapolated or padded here:
#
#   * `before_prediction` arrives already LOWESS-smoothed (frac = 0.10). No
#     second smoother is applied to it.
#   * The "Now" marker and the divider both sit on `prediction_point`'s own
#     timestamp. No date is hard-coded and today's date is never used.
#   * The macro and news-adjusted lines start at the prediction point because
#     the API states both are propagated from that same baseline.
#   * There is no confidence interval, because the response carries none. The
#     shaded region — drawn only when both trajectories are returned — is the
#     span *between the two returned forecasts*, which is a range that exists
#     in the data rather than an uncertainty estimate invented here.
# ═════════════════════════════════════════════════════════════════════════════

FC_HISTORY = "#94A3B8"      # recorded market history — muted slate
FC_MODEL_HISTORY = "#64748B"  # the API's own smoothed history
FC_NOW = "#B8731B"          # the anchor point — brand bronze
FC_MACRO = "#10B981"        # macro forecast — green, dashed
FC_NEWS = "#F87171"         # news-adjusted forecast — coral


def _month_axis(fig, x_values, dark: bool = False) -> None:
    """
    Put months on the x axis, at a spacing that stays readable.

    Plotly falls back to year ticks once a series spans several years, which is
    what happened here: the API returns far more history than its documentation
    suggests. The tick interval is chosen from the actual span so every point is
    still a labelled month rather than a mark between two year gridlines.
    """
    xs = [pd.Timestamp(x) for x in x_values if x is not None and not pd.isna(x)]
    if not xs:
        return
    lo, hi = min(xs), max(xs)
    months = max(1, (hi.year - lo.year) * 12 + (hi.month - lo.month) + 1)

    if months <= 20:
        step, fmt, angle = 1, "%b %Y", -45
    elif months <= 40:
        step, fmt, angle = 2, "%b %Y", -45
    elif months <= 80:
        step, fmt, angle = 3, "%b %Y", -45
    else:
        step, fmt, angle = 6, "%b %Y", -45

    fig.update_xaxes(
        type="date", tickmode="linear",
        tick0=lo.strftime("%Y-%m-01"), dtick=f"M{step}",
        tickformat=fmt, tickangle=angle, ticklabelmode="period",
        # A little breathing room so the first and last month are not clipped
        # by the plot edge.
        range=[(lo - pd.DateOffset(days=20)).isoformat(),
               (hi + pd.DateOffset(days=20)).isoformat()],
    )


def api_forecast_chart(result, local_history=None, dark: bool = False,
                       show_band: bool = True, window_start=None) -> go.Figure:
    """
    The forecast chart.

    `result` is a `forecast_api.ForecastResult`. `local_history` is optional and,
    when given, is the area's genuine recorded monthly median rate per m² from
    the cleaned dataset — a separate, separately-labelled trace, never spliced
    onto the API series, and used only so the historical-window control has real
    data behind it. It is drawn under everything else.

    `window_start` trims the **history** shown to months at or after that date.
    It never touches the forecast: the projection is always drawn in full, for
    exactly as many months as the response contains.
    """
    fig = go.Figure()

    history = result.history
    if window_start is not None and not history.empty:
        history = history[history["timestamp"] >= pd.Timestamp(window_start)]

    # ── recorded market history (local dataset, clearly its own trace) ───────
    if local_history is not None and not local_history.empty:
        fig.add_trace(go.Scatter(
            x=local_history["timestamp"], y=local_history["value"],
            name="Recorded market history — area median",
            mode="lines", line=dict(color=FC_HISTORY, width=1.6),
            fill="tozeroy",
            fillcolor="rgba(148,163,184,0.10)" if not dark else "rgba(148,163,184,0.07)",
            hovertemplate="%{x|%b %Y}<br>Area median AED %{y:,.0f}/m²<extra></extra>",
        ))

    # ── the API's own smoothed history for this property profile ────────────
    if not history.empty:
        fig.add_trace(go.Scatter(
            x=history["timestamp"], y=history["value"],
            name="Model history — smoothed by the API",
            mode="lines+markers",
            line=dict(color=FC_MODEL_HISTORY, width=2.6),
            marker=dict(size=6, color=FC_MODEL_HISTORY),
            hovertemplate="%{x|%b %Y}<br>AED %{y:,.0f}/m²<extra></extra>",
        ))

    macro = result.anchored("macro")
    news = result.anchored("news")

    # ── the range between the two returned trajectories ─────────────────────
    if show_band and result.has_news and not macro.empty and not news.empty:
        joined = macro.merge(news, on="timestamp", suffixes=("_macro", "_news"))
        if not joined.empty:
            upper = joined[["value_macro", "value_news"]].max(axis=1)
            lower = joined[["value_macro", "value_news"]].min(axis=1)
            fig.add_trace(go.Scatter(
                x=joined["timestamp"], y=upper, mode="lines",
                line=dict(width=0), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(
                x=joined["timestamp"], y=lower, mode="lines",
                line=dict(width=0), fill="tonexty",
                fillcolor="rgba(16,185,129,0.14)",
                name="Range between the two forecasts",
                hoverinfo="skip"))

    # ── macro forecast ──────────────────────────────────────────────────────
    if not macro.empty:
        fig.add_trace(go.Scatter(
            x=macro["timestamp"], y=macro["value"],
            name="Macro forecast", mode="lines+markers",
            line=dict(color=FC_MACRO, width=2.6, dash="dash"),
            marker=dict(size=7, color=FC_MACRO),
            hovertemplate="%{x|%b %Y}<br>Macro AED %{y:,.0f}/m²<extra></extra>",
        ))

    # ── news-adjusted forecast ──────────────────────────────────────────────
    if result.has_news and not news.empty:
        fig.add_trace(go.Scatter(
            x=news["timestamp"], y=news["value"],
            name="News-adjusted forecast", mode="lines+markers",
            line=dict(color=FC_NEWS, width=2.6),
            marker=dict(size=7, color=FC_NEWS),
            hovertemplate="%{x|%b %Y}<br>News-adjusted AED %{y:,.0f}/m²<extra></extra>",
        ))

    # ── the anchor: "Now" ───────────────────────────────────────────────────
    # Position comes from prediction_point's timestamp. Never from date.today().
    now_ts = result.now_timestamp
    if now_ts is not None:
        fig.add_vline(x=now_ts, line=dict(color=FC_NOW, width=1.4, dash="dot"))
        fig.add_annotation(
            x=now_ts, yref="paper", y=1.02, text="Now", showarrow=False,
            font=dict(size=11, color=FC_NOW), xanchor="center", yanchor="bottom")
        fig.add_trace(go.Scatter(
            x=[now_ts], y=[result.now_value],
            name="Current valuation point", mode="markers",
            marker=dict(size=13, color=FC_NOW, line=dict(width=2, color="#FFFFFF")),
            hovertemplate="%{x|%b %Y}<br>Valuation point AED %{y:,.0f}/m²<extra></extra>",
        ))

    fig.update_layout(**layout(height=500, dark=dark, show_legend=True))
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.42,
                                  xanchor="left", x=0),
                      margin={"l": 60, "r": 25, "t": 55, "b": 90})
    fig.update_yaxes(title_text="AED per m²", rangemode="tozero")

    # Every month labelled, at a readable spacing for the span actually drawn.
    all_x = list(history["timestamp"]) + list(macro["timestamp"]) + list(news["timestamp"])
    if local_history is not None and not local_history.empty:
        all_x += list(local_history["timestamp"])
    _month_axis(fig, all_x, dark=dark)
    fig.update_xaxes(title_text="Month", title_standoff=18)
    return fig
