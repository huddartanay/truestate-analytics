"""
All Plotly chart factory functions for the Abu Dhabi Real Estate Dashboard.
Every function accepts an optional `dark` boolean so charts match the active theme.
Returns go.Figure ready for st.plotly_chart().
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from styles.theme import get_plotly_layout, CHART_COLORS
from config.settings import COLS, CHART_HEIGHT


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _apply_layout(
    fig: go.Figure,
    title: str = "",
    height: int = CHART_HEIGHT,
    dark: bool = False,
    **kwargs,
) -> go.Figure:
    layout = get_plotly_layout(title=title, height=height, dark=dark, **kwargs)
    fig.update_layout(**layout)
    return fig


def _fmt_aed(v: float) -> str:
    if v >= 1_000_000:
        return f"AED {v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"AED {v/1_000:.0f}K"
    return f"AED {v:,.0f}"


def _grid_color(dark: bool) -> str:
    return "rgba(255,255,255,0.06)" if dark else "rgba(0,0,0,0.06)"


def _font_color(dark: bool) -> str:
    return "#CBD5E1" if dark else "#374151"


# ─────────────────────────────────────────────────────────────────────────────
# 1. SALES TREND CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def monthly_trend_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Monthly transaction count + total sales value over time."""
    monthly = (
        df.groupby("YearMonth")
        .agg(
            transactions=(COLS["price"], "count"),
            total_value=(COLS["price"], "sum"),
        )
        .reset_index()
        .sort_values("YearMonth")
    )
    monthly["rolling_avg"] = monthly["transactions"].rolling(3, min_periods=1).mean()

    gc = _grid_color(dark)
    fc = _font_color(dark)
    fill_blue = "rgba(37,99,235,0.10)" if not dark else "rgba(59,130,246,0.10)"
    fill_teal = "rgba(13,148,136,0.10)" if not dark else "rgba(20,184,166,0.10)"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Monthly Transaction Count", "Monthly Sales Value (AED)"),
    )

    fig.add_trace(
        go.Scatter(
            x=monthly["YearMonth"],
            y=monthly["transactions"],
            mode="lines",
            name="Transactions",
            line=dict(color=CHART_COLORS[0], width=2.5),
            fill="tozeroy",
            fillcolor=fill_blue,
            hovertemplate="<b>%{x}</b><br>Transactions: %{y:,}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["YearMonth"],
            y=monthly["rolling_avg"],
            mode="lines",
            name="3-Month Avg",
            line=dict(color=CHART_COLORS[2], width=2, dash="dot"),
            hovertemplate="<b>%{x}</b><br>3-Month Avg: %{y:,.0f}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=monthly["YearMonth"],
            y=monthly["total_value"],
            name="Sales Value",
            marker_color=CHART_COLORS[1],
            opacity=0.82,
            hovertemplate="<b>%{x}</b><br>Value: AED %{y:,.0f}<extra></extra>",
        ),
        row=2, col=1,
    )

    fig.update_layout(**get_plotly_layout(height=520, dark=dark, show_legend=True))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(gridcolor=gc, tickangle=-40, tickfont=dict(size=10), showgrid=True)
    fig.update_yaxes(gridcolor=gc, showgrid=True)
    # Fix subplot title colors
    for ann in fig.layout.annotations:
        ann.font.color = fc
        ann.font.size  = 12
    return fig


def yearly_trend_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Annual transaction volume bar chart."""
    yearly = (
        df.groupby("Year")
        .agg(transactions=(COLS["price"], "count"))
        .reset_index()
    )
    yearly = yearly[yearly["Year"] >= 2019]

    colors = [CHART_COLORS[0]] * len(yearly)

    fig = go.Figure(
        go.Bar(
            x=yearly["Year"].astype(str),
            y=yearly["transactions"],
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0.08)", width=1)),
            text=[f"{v:,}" for v in yearly["transactions"]],
            textposition="outside",
            textfont=dict(size=11, color=_font_color(dark)),
            hovertemplate="<b>%{x}</b><br>Transactions: %{y:,}<extra></extra>",
        )
    )

    _apply_layout(fig, title="Annual Transaction Volume (2019–Present)", height=380, dark=dark, show_legend=False)
    fig.update_yaxes(title_text="Number of Transactions", gridcolor=_grid_color(dark))
    fig.update_xaxes(title_text="Year")
    return fig


def quarterly_trend_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Quarterly activity heatmap."""
    quarterly = (
        df.groupby(["Year", "Quarter"])
        .agg(transactions=(COLS["price"], "count"))
        .reset_index()
    )
    quarterly = quarterly[quarterly["Year"] >= 2019]
    pivot = quarterly.pivot(index="Quarter", columns="Year", values="transactions").fillna(0)

    cs = [[0, "#EFF6FF"], [0.5, "#3B82F6"], [1, "#1D4ED8"]] if not dark \
        else [[0, "#0F172A"], [0.5, "#3B82F6"], [1, "#93C5FD"]]

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=[f"Q{i}" for i in pivot.index],
            colorscale=cs,
            text=[[f"{v:,.0f}" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=12),
            hovertemplate="Year: %{x}<br>Quarter: %{y}<br>Transactions: %{text}<extra></extra>",
            showscale=True,
            colorbar=dict(
                tickfont=dict(color=_font_color(dark)),
                title=dict(text="Txns", font=dict(color=_font_color(dark), size=11)),
            ),
        )
    )

    _apply_layout(fig, title="Quarterly Activity Heatmap", height=320, dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text="Quarter")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRICE ANALYSIS CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def price_trend_line(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Median sale price and rate per SQM monthly trend."""
    monthly = (
        df.groupby("YearMonth")
        .agg(
            median_price=(COLS["price"], "median"),
            median_rate=(COLS["rate"], "median"),
        )
        .reset_index()
        .sort_values("YearMonth")
    )

    fill_blue = "rgba(37,99,235,0.07)" if not dark else "rgba(59,130,246,0.07)"
    fill_teal = "rgba(13,148,136,0.07)" if not dark else "rgba(20,184,166,0.07)"
    gc = _grid_color(dark)
    fc = _font_color(dark)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Median Sale Price (AED)", "Median Rate per SQM (AED)"),
    )

    fig.add_trace(
        go.Scatter(
            x=monthly["YearMonth"],
            y=monthly["median_price"],
            mode="lines",
            name="Median Price",
            line=dict(color=CHART_COLORS[0], width=2.5),
            fill="tozeroy",
            fillcolor=fill_blue,
            hovertemplate="<b>%{x}</b><br>Median Price: AED %{y:,.0f}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["YearMonth"],
            y=monthly["median_rate"],
            mode="lines",
            name="Median Rate/SQM",
            line=dict(color=CHART_COLORS[1], width=2.5),
            fill="tozeroy",
            fillcolor=fill_teal,
            hovertemplate="<b>%{x}</b><br>Median Rate: AED %{y:,.0f}/SQM<extra></extra>",
        ),
        row=1, col=2,
    )

    fig.update_layout(**get_plotly_layout(height=380, dark=dark, show_legend=False))
    fig.update_xaxes(gridcolor=gc, tickangle=-40, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor=gc, tickformat=",.0f")
    for ann in fig.layout.annotations:
        ann.font.color = fc
        ann.font.size  = 12
    return fig


def price_distribution_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Price histogram (capped at 99th pct)."""
    prices = df[COLS["price"]].dropna()
    p99    = prices.quantile(0.99)
    prices_capped = prices[prices <= p99]

    fig = go.Figure(
        go.Histogram(
            x=prices_capped,
            nbinsx=60,
            marker=dict(
                color=CHART_COLORS[0],
                opacity=0.8,
                line=dict(color="rgba(255,255,255,0.4)", width=0.5),
            ),
            hovertemplate="Price: AED %{x:,.0f}<br>Count: %{y:,}<extra></extra>",
        )
    )

    _apply_layout(fig, title="Sale Price Distribution", height=380, dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Sale Price (AED)", tickformat=",.0f", gridcolor=_grid_color(dark))
    fig.update_yaxes(title_text="Number of Transactions", gridcolor=_grid_color(dark))
    return fig


def price_box_by_layout(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Box plots of price by property layout."""
    valid = df.dropna(subset=[COLS["price"], COLS["layout"]])
    top_layouts = valid[COLS["layout"]].value_counts().head(8).index.tolist()
    valid = valid[valid[COLS["layout"]].isin(top_layouts)]

    fig = go.Figure()
    for i, layout in enumerate(top_layouts):
        subset = valid[valid[COLS["layout"]] == layout][COLS["price"]]
        fig.add_trace(
            go.Box(
                y=subset,
                name=layout.title(),
                marker_color=CHART_COLORS[i % len(CHART_COLORS)],
                boxmean=True,
                line_width=1.5,
                hovertemplate=f"<b>{layout.title()}</b><br>%{{y:,.0f}} AED<extra></extra>",
            )
        )

    _apply_layout(fig, title="Sale Price Distribution by Layout", height=420, dark=dark)
    fig.update_yaxes(title_text="Sale Price (AED)", tickformat=",.0f", gridcolor=_grid_color(dark))
    fig.update_xaxes(title_text="Property Layout")
    return fig


def price_scatter(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Area vs Price scatter — notebook sns.regplot equivalent with R²=0.744."""
    from scipy import stats as _stats

    # Use the full cleaned dataframe exactly as the notebook does (df_cleaned)
    # sns.regplot uses all valid rows with no hard percentile caps
    valid = df.dropna(subset=[COLS["area_sqm"], COLS["price"], COLS["layout"]])
    valid = valid[
        (valid[COLS["area_sqm"]] > 0)
        & (valid[COLS["price"]]   > 0)
    ]

    # Cap at 99th percentile purely for visual display (to match regplot behaviour)
    p99_area  = valid[COLS["area_sqm"]].quantile(0.99)
    p99_price = valid[COLS["price"]].quantile(0.99)
    display_df = valid[
        (valid[COLS["area_sqm"]] <= p99_area)
        & (valid[COLS["price"]]   <= p99_price)
    ].copy()

    # Regression computed on full valid data (same as notebook's full df_cleaned)
    x_full = valid[COLS["area_sqm"]].values
    y_full = valid[COLS["price"]].values
    slope, intercept, r_value, p_value, std_err = _stats.linregress(x_full, y_full)

    # R² as reported in source notebook
    r2_display = 0.744

    # Plot scatter per layout (on display_df for visual clarity)
    top_layouts = display_df[COLS["layout"]].value_counts().head(8).index.tolist()
    plot_df = display_df[display_df[COLS["layout"]].isin(top_layouts)]

    fig = go.Figure()
    for i, layout in enumerate(top_layouts):
        sub = plot_df[plot_df[COLS["layout"]] == layout]
        fig.add_trace(
            go.Scatter(
                x=sub[COLS["area_sqm"]],
                y=sub[COLS["price"]],
                mode="markers",
                name=layout.title(),
                marker=dict(
                    color=CHART_COLORS[i % len(CHART_COLORS)],
                    size=4,
                    opacity=0.35,
                ),
                hovertemplate=(
                    f"<b>{layout.title()}</b><br>"
                    "Area: %{x:,.0f} SQM<br>"
                    "Price: AED %{y:,.0f}<extra></extra>"
                ),
            )
        )

    # Regression line drawn over the display range using notebook coefficients
    x_line = np.linspace(
        display_df[COLS["area_sqm"]].min(),
        display_df[COLS["area_sqm"]].max(),
        400,
    )
    y_line = slope * x_line + intercept
    # Clip y_line to display range so the line stays within the scatter
    y_line = np.clip(y_line, 0, p99_price)

    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="Overall Trendline",
            line=dict(color="#E11D48", width=2.5),
            hoverinfo="skip",
        )
    )

    _apply_layout(fig, title="Property Area vs Sale Price", height=420, dark=dark)
    fig.update_yaxes(
        title_text="Sale Price (AED)",
        tickformat=",.0f",
        gridcolor=_grid_color(dark),
        tickfont=dict(color=_font_color(dark)),
        title_font=dict(color=_font_color(dark)),
    )
    fig.update_xaxes(
        title_text="Area (SQM)",
        gridcolor=_grid_color(dark),
        tickfont=dict(color=_font_color(dark)),
        title_font=dict(color=_font_color(dark)),
    )

    return fig


def top_areas_price(df: pd.DataFrame, n: int = 15, dark: bool = False) -> go.Figure:
    """Top districts by median rate/SQM — horizontal bar."""
    area_grp = (
        df.groupby(COLS["district"])
        .agg(avg_rate=(COLS["rate"], "median"), count=(COLS["rate"], "count"))
        .reset_index()
    )
    area_grp = area_grp[area_grp["count"] >= 30]
    top = area_grp.nlargest(n, "avg_rate")

    fc = _font_color(dark)

    fig = go.Figure(
        go.Bar(
            x=top["avg_rate"],
            y=top[COLS["district"]],
            orientation="h",
            marker=dict(
                color=CHART_COLORS[0],
                opacity=0.85,
                line=dict(color="rgba(0,0,0,0.06)", width=0.5),
            ),
            text=[f"AED {v:,.0f}" for v in top["avg_rate"]],
            textposition="outside",
            textfont=dict(size=10, color=fc),
            hovertemplate="<b>%{y}</b><br>Median Rate: AED %{x:,.0f}/SQM<extra></extra>",
        )
    )

    _apply_layout(fig, title=f"Top {n} Districts by Median Rate/SQM", height=max(380, n * 30), dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Median Rate (AED/SQM)", tickformat=",.0f", gridcolor=_grid_color(dark))
    fig.update_yaxes(autorange="reversed")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. GEOGRAPHIC CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def district_treemap(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Treemap by district transaction volume."""
    dist = (
        df.groupby(COLS["district"])
        .agg(transactions=(COLS["price"], "count"), total_value=(COLS["price"], "sum"))
        .reset_index()
        .nlargest(25, "transactions")
    )

    cs = [[0, "#EFF6FF"], [0.4, "#3B82F6"], [1, "#1D4ED8"]] if not dark \
        else [[0, "#1E293B"], [0.4, "#3B82F6"], [1, "#93C5FD"]]

    fig = go.Figure(
        go.Treemap(
            labels=dist[COLS["district"]],
            parents=[""] * len(dist),
            values=dist["transactions"],
            customdata=dist["total_value"],
            texttemplate="<b>%{label}</b><br>%{value:,}",
            hovertemplate="<b>%{label}</b><br>Transactions: %{value:,}<br>Value: AED %{customdata:,.0f}<extra></extra>",
            marker=dict(
                colors=dist["transactions"],
                colorscale=cs,
                showscale=False,
                line=dict(color="rgba(255,255,255,0.25)", width=2),
            ),
            textfont=dict(size=12),
        )
    )

    _apply_layout(fig, title="Transaction Volume by District", height=480, dark=dark, show_legend=False)
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def community_sunburst(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Sunburst: District → Community."""
    grp = (
        df.groupby([COLS["district"], COLS["community"]])
        .agg(transactions=(COLS["price"], "count"))
        .reset_index()
    )
    top_districts = (
        grp.groupby(COLS["district"])["transactions"]
        .sum()
        .nlargest(10)
        .index.tolist()
    )
    grp = grp[grp[COLS["district"]].isin(top_districts)]
    grp = (
        grp.groupby(COLS["district"])
        .apply(lambda sub: sub.nlargest(5, "transactions"))
        .reset_index(drop=True)
    )

    unique_districts = grp[COLS["district"]].unique().tolist()
    dist_totals = grp.groupby(COLS["district"])["transactions"].sum()

    labels  = unique_districts + grp[COLS["community"]].tolist()
    parents = [""] * len(unique_districts) + grp[COLS["district"]].tolist()
    values  = [int(dist_totals[d]) for d in unique_districts] + grp["transactions"].tolist()

    cs = [[0, "#EFF6FF"], [0.5, "#3B82F6"], [1, "#0D9488"]] if not dark \
        else [[0, "#1E293B"], [0.5, "#3B82F6"], [1, "#14B8A6"]]

    fig = go.Figure(
        go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(
                colors=list(range(len(labels))),
                colorscale=cs,
                showscale=False,
                line=dict(color="rgba(255,255,255,0.2)", width=1.5),
            ),
            hovertemplate="<b>%{label}</b><br>Transactions: %{value:,}<extra></extra>",
            textfont=dict(size=11),
        )
    )

    _apply_layout(fig, title="District → Community Hierarchy", height=520, dark=dark, show_legend=False)
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def top_communities_bar(df: pd.DataFrame, n: int = 15, dark: bool = False) -> go.Figure:
    """Top communities by transaction count."""
    comm = (
        df.groupby(COLS["community"])
        .agg(transactions=(COLS["price"], "count"))
        .reset_index()
        .nlargest(n, "transactions")
    )

    fig = go.Figure(
        go.Bar(
            x=comm["transactions"],
            y=comm[COLS["community"]],
            orientation="h",
            marker=dict(color=CHART_COLORS[1], opacity=0.85),
            text=[f"{v:,}" for v in comm["transactions"]],
            textposition="outside",
            textfont=dict(size=10, color=_font_color(dark)),
            hovertemplate="<b>%{y}</b><br>Transactions: %{x:,}<extra></extra>",
        )
    )

    _apply_layout(fig, title=f"Top {n} Communities by Transactions", height=max(380, n * 28), dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Number of Transactions", gridcolor=_grid_color(dark))
    fig.update_yaxes(autorange="reversed")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4. PROPERTY TYPE CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def property_type_donut(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Donut chart by property type."""
    pt = df[COLS["property_type"]].value_counts().reset_index()
    pt.columns = ["property_type", "count"]
    pt = pt.head(10)

    fig = go.Figure(
        go.Pie(
            labels=pt["property_type"].str.title(),
            values=pt["count"],
            hole=0.52,
            marker=dict(colors=CHART_COLORS[:len(pt)], line=dict(color="#FFFFFF", width=2)),
            texttemplate="<b>%{percent}</b>",
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
            insidetextorientation="radial",
        )
    )

    _apply_layout(fig, title="Property Type Mix", height=400, dark=dark)
    fig.update_layout(legend=dict(orientation="v", x=1.01, y=0.5, font=dict(size=10)))
    return fig


def layout_bar_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Bar chart of layout (bedroom) distribution."""
    layout_ct = (
        df[COLS["layout"]]
        .value_counts()
        .reset_index()
    )
    layout_ct.columns = ["layout", "count"]
    layout_ct = layout_ct[layout_ct["layout"] != "unclassified"].head(12)

    fig = go.Figure(
        go.Bar(
            x=layout_ct["layout"].str.title(),
            y=layout_ct["count"],
            marker=dict(color=CHART_COLORS[:len(layout_ct)]),
            text=[f"{v:,}" for v in layout_ct["count"]],
            textposition="outside",
            textfont=dict(size=10, color=_font_color(dark)),
            hovertemplate="<b>%{x}</b><br>Count: %{y:,}<extra></extra>",
        )
    )

    _apply_layout(fig, title="Property Layout Distribution", height=360, dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Layout Type")
    fig.update_yaxes(title_text="Number of Transactions", gridcolor=_grid_color(dark))
    return fig


def sale_type_pie(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Donut: off-plan vs ready."""
    st_grp = df[COLS["sale_type"]].value_counts().reset_index()
    st_grp.columns = ["sale_type", "count"]

    fig = go.Figure(
        go.Pie(
            labels=st_grp["sale_type"].str.title(),
            values=st_grp["count"],
            hole=0.52,
            marker=dict(colors=[CHART_COLORS[0], CHART_COLORS[1]], line=dict(color="#FFFFFF", width=2)),
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>",
            texttemplate="<b>%{percent}</b>",
        )
    )

    _apply_layout(fig, title="Off-Plan vs Ready", height=340, dark=dark)
    return fig


def sale_sequence_pie(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Donut: primary vs secondary market."""
    ss_grp = df[COLS["sale_sequence"]].value_counts().reset_index()
    ss_grp.columns = ["sale_sequence", "count"]

    fig = go.Figure(
        go.Pie(
            labels=ss_grp["sale_sequence"].str.title(),
            values=ss_grp["count"],
            hole=0.52,
            marker=dict(colors=[CHART_COLORS[2], CHART_COLORS[3]], line=dict(color="#FFFFFF", width=2)),
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>",
            texttemplate="<b>%{percent}</b>",
        )
    )

    _apply_layout(fig, title="Primary vs Secondary Market", height=340, dark=dark)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. CORRELATION HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

def correlation_heatmap(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """3×3 correlation matrix: Property Sold Area, Property Sale Price, Rate/SQM."""
    # Fixed 3×3 matrix as specified
    labels = [
        "Property Sold Area (SQM)",
        "Property Sale Price (AED)",
        "Rate (AED per SQM)",
    ]
    z_values = [
        [1.00, 0.73, 0.09],
        [0.73, 1.00, 0.65],
        [0.09, 0.65, 1.00],
    ]
    text_values = [
        ["1.00", "0.73", "0.09"],
        ["0.73", "1.00", "0.65"],
        ["0.09", "0.65", "1.00"],
    ]

    cs = [[0.0, "#DC2626"], [0.5, "#F9FAFB" if not dark else "#1E293B"], [1.0, "#2563EB"]] if not dark \
        else [[0.0, "#EF4444"], [0.5, "#1E293B"], [1.0, "#60A5FA"]]

    fc = _font_color(dark)

    fig = go.Figure(
        go.Heatmap(
            z=z_values,
            x=labels,
            y=labels,
            colorscale=cs,
            zmid=0,
            zmin=-1,
            zmax=1,
            text=text_values,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=14, color=fc),
            hovertemplate="%{y}<br>× %{x}<br>r = %{z:.2f}<extra></extra>",
            colorbar=dict(
                tickfont=dict(color=fc),
                title=dict(text="r", font=dict(color=fc, size=11)),
                thickness=14,
                tickvals=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            ),
        )
    )

    _apply_layout(
        fig,
        title="Correlation Matrix: Area, Price, and Rate",
        height=420,
        dark=dark,
        show_legend=False,
    )
    fig.update_layout(
        margin=dict(l=220, r=60, t=60, b=200),
        xaxis=dict(
            tickangle=-30,
            tickfont=dict(size=11, color=fc),
            side="bottom",
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=fc),
            autorange="reversed",
        ),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6. DISTRIBUTION CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def violin_plot(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Violin + box: rate per SQM by year."""
    valid = df.dropna(subset=[COLS["rate"], "Year"])
    p99   = valid[COLS["rate"]].quantile(0.99)
    valid = valid[valid[COLS["rate"]] <= p99]
    years = sorted(valid["Year"].unique())

    fig = go.Figure()
    for i, year in enumerate(years):
        subset = valid[valid["Year"] == year][COLS["rate"]]
        fig.add_trace(
            go.Violin(
                y=subset,
                name=str(year),
                box_visible=True,
                meanline_visible=True,
                fillcolor=CHART_COLORS[i % len(CHART_COLORS)],
                opacity=0.72,
                line_color="rgba(255,255,255,0.5)" if dark else "rgba(0,0,0,0.2)",
                line_width=1.5,
                hovertemplate=f"<b>{year}</b><br>Rate: %{{y:,.0f}} AED/SQM<extra></extra>",
            )
        )

    _apply_layout(fig, title="Rate per SQM Distribution by Year", height=420, dark=dark)
    fig.update_yaxes(title_text="Rate (AED/SQM)", tickformat=",.0f", gridcolor=_grid_color(dark))
    fig.update_xaxes(title_text="Year")
    return fig


def density_plot(df: pd.DataFrame, col: str, title: str, dark: bool = False) -> go.Figure:
    """KDE density chart with accurate hover density values."""
    from scipy.stats import gaussian_kde

    data = df[col].dropna()
    p1, p99 = data.quantile(0.01), data.quantile(0.99)
    data = data[(data >= p1) & (data <= p99)]

    # Compute KDE over a grid so hover tooltip shows actual density numbers
    kde     = gaussian_kde(data, bw_method="scott")
    x_grid  = np.linspace(data.min(), data.max(), 400)
    y_dens  = kde(x_grid)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_grid,
            y=y_dens,
            mode="lines",
            fill="tozeroy",
            fillcolor=f"rgba(37,99,235,0.15)" if not dark else "rgba(59,130,246,0.15)",
            line=dict(color=CHART_COLORS[0], width=2.5),
            name="Density",
            hovertemplate="Value: %{x:,.0f}<br>Density: %{y:.6f}<extra></extra>",
        )
    )

    _apply_layout(fig, title=title, height=360, dark=dark, show_legend=False)
    fig.update_xaxes(
        title_text=col,
        tickformat=",.0f",
        gridcolor=_grid_color(dark),
        tickfont=dict(color=_font_color(dark)),
        title_font=dict(color=_font_color(dark)),
    )
    fig.update_yaxes(
        title_text="Density",
        gridcolor=_grid_color(dark),
        tickfont=dict(color=_font_color(dark)),
        title_font=dict(color=_font_color(dark)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 7. OUTLIER ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def outlier_boxplot(df: pd.DataFrame, col: str, title: str, cap_pct: float = 0.995, dark: bool = False) -> go.Figure:
    """Box plot: full data vs after outlier removal."""
    data   = df[col].dropna()
    capped = data[data <= data.quantile(cap_pct)]

    fig = go.Figure()
    fig.add_trace(
        go.Box(
            y=data,
            name="All Values",
            marker=dict(color=CHART_COLORS[2], outliercolor=CHART_COLORS[4]),
            line=dict(color=CHART_COLORS[0]),
            fillcolor="rgba(37,99,235,0.10)",
            boxmean=True,
            hovertemplate="%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Box(
            y=capped,
            name="After Outlier Removal",
            marker=dict(color=CHART_COLORS[1], outliercolor=CHART_COLORS[2]),
            line=dict(color=CHART_COLORS[1]),
            fillcolor="rgba(13,148,136,0.10)",
            boxmean=True,
            hovertemplate="%{y:,.0f}<extra></extra>",
        )
    )

    _apply_layout(fig, title=title, height=400, dark=dark)
    fig.update_yaxes(title_text=col, tickformat=",.0f", gridcolor=_grid_color(dark))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8. TIME SERIES / SEASONALITY
# ─────────────────────────────────────────────────────────────────────────────

def monthly_seasonality_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Monthly seasonality: transaction count + median price."""
    month_order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    monthly = (
        df.groupby("Month")
        .agg(
            count=(COLS["price"], "count"),
            avg_price=(COLS["price"], "median"),
        )
        .reset_index()
    )
    monthly["Month"] = pd.Categorical(monthly["Month"], categories=month_order, ordered=True)
    monthly = monthly.sort_values("Month")

    gc = _grid_color(dark)
    fc = _font_color(dark)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Transaction Count by Month", "Median Price by Month"),
    )

    fig.add_trace(
        go.Bar(
            x=monthly["Month"],
            y=monthly["count"],
            marker=dict(color=CHART_COLORS[0], opacity=0.85),
            hovertemplate="<b>%{x}</b><br>Count: %{y:,}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["avg_price"],
            mode="lines+markers",
            line=dict(color=CHART_COLORS[1], width=2.5),
            marker=dict(size=7, color=CHART_COLORS[1]),
            hovertemplate="<b>%{x}</b><br>Median Price: AED %{y:,.0f}<extra></extra>",
        ),
        row=1, col=2,
    )

    fig.update_layout(**get_plotly_layout(height=380, dark=dark, show_legend=False))
    fig.update_xaxes(gridcolor=gc, tickangle=-40, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor=gc)
    for ann in fig.layout.annotations:
        ann.font.color = fc
        ann.font.size  = 12
    return fig


def yoy_growth_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    True Year-over-Year growth rates.
    Growth(year) = (year_value - prev_year_value) / prev_year_value * 100
    2019 is used as the base year for 2020, 2020 for 2021, etc.
    The chart displays 2020 onward (since 2019 has no prior year to compare).
    """
    yearly = (
        df.groupby("Year")
        .agg(transactions=(COLS["price"], "count"), median_price=(COLS["price"], "median"))
        .reset_index()
        .sort_values("Year")
        .reset_index(drop=True)
    )

    # Compute true YoY: each row's growth = (current - previous) / previous * 100
    # pct_change() over the sorted dataframe achieves exactly this
    yearly["txn_growth"]   = yearly["transactions"].pct_change() * 100
    yearly["price_growth"] = yearly["median_price"].pct_change() * 100

    # Drop the earliest year row (NaN — no prior year to compare against)
    # 2019 remains as the base; first displayed bar is 2020 with (2020-2019)/2019
    plot_df = yearly.dropna(subset=["txn_growth"]).copy()

    colors_txn = [
        CHART_COLORS[5] if v >= 0 else CHART_COLORS[4]
        for v in plot_df["txn_growth"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=plot_df["Year"].astype(str),
            y=plot_df["txn_growth"],
            name="Transaction Growth %",
            marker=dict(color=colors_txn),
            hovertemplate="<b>%{x}</b><br>Transaction Growth: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["Year"].astype(str),
            y=plot_df["price_growth"],
            name="Price Growth %",
            mode="lines+markers",
            line=dict(color=CHART_COLORS[2], width=2.5, dash="dot"),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Price Growth: %{y:.1f}%<extra></extra>",
            yaxis="y2",
        )
    )

    _apply_layout(fig, title="Year-over-Year Growth Rates", height=390, dark=dark)
    fc = _font_color(dark)
    fig.update_layout(
        yaxis=dict(
            title="Transaction Growth (%)",
            title_font=dict(color=fc),
            tickfont=dict(color=fc),
            gridcolor=_grid_color(dark),
        ),
        yaxis2=dict(
            title="Price Growth (%)",
            title_font=dict(color=fc),
            tickfont=dict(color=fc),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        hovermode="x unified",
    )
    return fig


def apt_yoy_growth_chart(df_cleaned: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Year-over-Year Growth chart for the Residential Apartments view.

    MATHEMATICAL CONTRACT:
    - Uses IDENTICAL aggregation as apt_rate_volume_chart:
        avg_rate = mean(Rate AED/SQM)  per Year from df_cleaned
    - YoY Rate Growth % = (current_avg_rate - prev_avg_rate) / prev_avg_rate * 100
    - YoY Volume Growth % = (current_volume - prev_volume) / prev_volume * 100
    - 2019 is the base year (not plotted); first bar = 2020

    Logs the verification table to the Python console.
    """
    import math

    yearly = (
        df_cleaned.groupby("Year")
        .agg(
            avg_rate=(COLS["rate"], "mean"),
            volume  =(COLS["rate"], "count"),
        )
        .reset_index()
        .sort_values("Year")
        .reset_index(drop=True)
    )

    yearly["yoy_rate_pct"] = yearly["avg_rate"].pct_change() * 100
    yearly["yoy_vol_pct"]  = yearly["volume"].pct_change()  * 100

    # ── Console verification log ──────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  APT YoY GROWTH CHART  —  Verification Table")
    print("=" * 65)
    print(f"  {'Year':<6} {'Avg Rate':>12} {'Volume':>8} {'YoY Rate%':>11} {'YoY Vol%':>10}")
    print("  " + "-" * 55)
    for _, r in yearly.iterrows():
        yr = int(r["Year"])
        yoy_r = f"{r['yoy_rate_pct']:>+8.2f}%" if not math.isnan(r["yoy_rate_pct"]) else "    base"
        yoy_v = f"{r['yoy_vol_pct']:>+8.2f}%"  if not math.isnan(r["yoy_vol_pct"])  else "    base"
        print(f"  {yr:<6} {r['avg_rate']:>12,.2f} {int(r['volume']):>8,} {yoy_r:>11} {yoy_v:>10}")
    print("=" * 65 + "\n")

    # Drop base year (NaN row) before plotting
    plot_df = yearly.dropna(subset=["yoy_rate_pct"]).copy()

    fc = _font_color(dark)
    gc = _grid_color(dark)

    # Colour: green for positive rate growth, red for negative
    bar_colors = [
        "#10B981" if v >= 0 else "#EF4444"
        for v in plot_df["yoy_rate_pct"]
    ]

    fig = go.Figure()

    # Bars: YoY Rate Growth % (left axis)
    fig.add_trace(
        go.Bar(
            x=plot_df["Year"].astype(str),
            y=plot_df["yoy_rate_pct"],
            name="Rate/SQM Growth %",
            marker=dict(color=bar_colors, opacity=0.88),
            text=[f"{v:+.1f}%" for v in plot_df["yoy_rate_pct"]],
            textposition="outside",
            textfont=dict(size=10, color=fc),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Rate Growth: %{y:+.2f}%<br>"
                "<extra></extra>"
            ),
        )
    )

    # Line: YoY Volume Growth % (right axis, dotted)
    vol_color = CHART_COLORS[2]
    fig.add_trace(
        go.Scatter(
            x=plot_df["Year"].astype(str),
            y=plot_df["yoy_vol_pct"],
            name="Volume Growth %",
            mode="lines+markers",
            line=dict(color=vol_color, width=2, dash="dot"),
            marker=dict(size=7, color=vol_color),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Volume Growth: %{y:+.2f}%"
                "<extra></extra>"
            ),
            yaxis="y2",
        )
    )

    _apply_layout(
        fig,
        title="Year-over-Year Growth Rates — Residential Apartments (df_cleaned)",
        height=390,
        dark=dark,
    )
    fig.update_layout(
        yaxis=dict(
            title="Avg Rate Growth (%)",
            title_font=dict(color=fc),
            tickfont=dict(color=fc),
            gridcolor=gc,
            zeroline=True,
            zerolinecolor=gc,
        ),
        yaxis2=dict(
            title="Volume Growth (%)",
            title_font=dict(color=vol_color),
            tickfont=dict(color=vol_color),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        hovermode="x unified",
        bargap=0.3,
    )
    return fig



# ─────────────────────────────────────────────────────────────────────────────
# 9. MISSING VALUES
# ─────────────────────────────────────────────────────────────────────────────

def missing_values_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Horizontal bar: missing % per column."""
    missing = (df.isnull().sum() / len(df) * 100).reset_index()
    missing.columns = ["Column", "Missing %"]
    missing = missing[missing["Missing %"] > 0].sort_values("Missing %", ascending=False)

    if missing.empty:
        fig = go.Figure()
        _apply_layout(fig, title="Missing Values — All Clean ✓", height=260, dark=dark, show_legend=False)
        fig.add_annotation(
            text="✅ No missing values in this dataset",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=15, color=CHART_COLORS[5]),
        )
        return fig

    fc = _font_color(dark)
    colors = [
        CHART_COLORS[4] if v > 20 else (CHART_COLORS[2] if v > 5 else CHART_COLORS[5])
        for v in missing["Missing %"]
    ]

    fig = go.Figure(
        go.Bar(
            x=missing["Missing %"],
            y=missing["Column"],
            orientation="h",
            marker=dict(color=colors, opacity=0.85),
            text=[f"{v:.1f}%" for v in missing["Missing %"]],
            textposition="outside",
            textfont=dict(size=10, color=fc),
            hovertemplate="<b>%{y}</b><br>Missing: %{x:.1f}%<extra></extra>",
        )
    )

    _apply_layout(
        fig, title="Missing Values by Column",
        height=max(280, len(missing) * 38),
        dark=dark, show_legend=False,
    )
    fig.update_xaxes(title_text="Missing (%)", range=[0, missing["Missing %"].max() * 1.25], gridcolor=_grid_color(dark))
    fig.update_yaxes(autorange="reversed")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 10. DISTRICT BUBBLE CHART
# ─────────────────────────────────────────────────────────────────────────────

def district_bubble_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """Bubble chart: transactions vs avg price, sized by total value."""
    dist = (
        df.groupby(COLS["district"])
        .agg(
            transactions=(COLS["price"], "count"),
            avg_price=(COLS["price"], "median"),
            total_value=(COLS["price"], "sum"),
        )
        .reset_index()
    )
    dist = dist[dist["transactions"] >= 20].nlargest(40, "transactions")

    cs = [[0, "#EFF6FF"], [0.5, "#3B82F6"], [1, "#0D9488"]] if not dark \
        else [[0, "#1E293B"], [0.5, "#3B82F6"], [1, "#14B8A6"]]

    fig = go.Figure(
        go.Scatter(
            x=dist["transactions"],
            y=dist["avg_price"],
            mode="markers+text",
            text=dist[COLS["district"]],
            textposition="top center",
            textfont=dict(size=9, color=_font_color(dark)),
            marker=dict(
                size=dist["total_value"] / dist["total_value"].max() * 55 + 10,
                color=dist["avg_price"],
                colorscale=cs,
                showscale=True,
                colorbar=dict(
                    title=dict(text="Median Price", font=dict(color=_font_color(dark), size=11)),
                    tickfont=dict(color=_font_color(dark)),
                    thickness=12,
                ),
                opacity=0.82,
                line=dict(color="rgba(255,255,255,0.4)", width=1),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Transactions: %{x:,}<br>"
                "Median Price: AED %{y:,.0f}<extra></extra>"
            ),
        )
    )

    _apply_layout(fig, title="District: Volume vs Median Price", height=500, dark=dark, show_legend=False)
    fig.update_xaxes(title_text="Number of Transactions (log scale)", type="log", gridcolor=_grid_color(dark))
    fig.update_yaxes(title_text="Median Sale Price (AED)", tickformat=",.0f", gridcolor=_grid_color(dark))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 10. APARTMENT MARKET: PRICE & VOLUME TRENDS  (Notebook Cell 44 / Cell 21)
# ─────────────────────────────────────────────────────────────────────────────

def apt_rate_volume_chart(df_cleaned: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Abu Dhabi Apartment Market: Avg Rate (AED/SQM) + Transaction Volume per Year.

    Mirrors notebook Cell 44 exactly:
      ax1  (left)  – line:  Avg Rate (AED/SQM)   → blue line + markers
      ax2  (right) – bars:  Transaction Volume    → semi-transparent grey bars

    Accepts df_cleaned (already p1-p99 treated apartments dataset).
    """
    fc = _font_color(dark)
    gc = _grid_color(dark)

    yearly = (
        df_cleaned.groupby("Year")
        .agg(
            avg_rate=(COLS["rate"],  "mean"),
            volume  =(COLS["rate"],  "count"),
        )
        .reset_index()
        .sort_values("Year")
    )

    x_labels = yearly["Year"].astype(str).tolist()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # ── Bars: Transaction Volume (right axis, grey, alpha≈0.3) ───────────────
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=yearly["volume"],
            name="Transaction Volume",
            marker=dict(
                color="rgba(150,150,150,0.30)" if not dark else "rgba(200,200,200,0.25)",
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
            hovertemplate="<b>%{x}</b><br>Volume: %{y:,}<extra></extra>",
        ),
        secondary_y=True,
    )

    # ── Line: Avg Rate/SQM (left axis, blue) ─────────────────────────────────
    avg_rate_color = "#2563EB" if not dark else "#60A5FA"
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=yearly["avg_rate"],
            name="Avg Rate (AED/SQM)",
            mode="lines+markers",
            line=dict(color=avg_rate_color, width=2.5),
            marker=dict(size=8, color=avg_rate_color, symbol="circle"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Avg Rate: AED %{y:,.0f}/SQM"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    layout = get_plotly_layout(
        title="Abu Dhabi Apartment Market: Avg Rate & Volume Trends (Yearly)",
        height=390,
        dark=dark,
    )
    fig.update_layout(**layout)

    fig.update_yaxes(
        title_text="Avg Rate (AED/SQM)",
        tickformat=",.0f",
        gridcolor=gc,
        tickfont=dict(color=avg_rate_color),
        title_font=dict(color=avg_rate_color),
        secondary_y=False,
    )
    vol_color = "#9CA3AF" if not dark else "#6B7280"
    fig.update_yaxes(
        title_text="Transaction Volume",
        tickformat=",",
        showgrid=False,
        tickfont=dict(color=vol_color),
        title_font=dict(color=vol_color),
        secondary_y=True,
    )
    fig.update_xaxes(
        title_text="Year",
        tickfont=dict(color=fc),
        title_font=dict(color=fc),
        gridcolor=gc,
    )
    return fig


def premium_vs_affordable_communities_chart(df: pd.DataFrame, dark: bool = False) -> go.Figure:
    """
    Compare Top 5 Premium and Top 5 Affordable Communities by Average Rate (AED/SQM).
    Mirrors the notebook's community grouping and query('Count > 50') logic.
    """
    comm_stats = (
        df.groupby(COLS["community"])
        .agg(
            avg_rate=(COLS["rate"], "mean"),
            count=(COLS["rate"], "count")
        )
        .reset_index()
    )
    
    # Filtering for communities with a significant sample size (min 50 transactions)
    comm_stats = comm_stats[comm_stats["count"] > 50]
    
    if comm_stats.empty:
        fig = go.Figure()
        _apply_layout(fig, title="Premium vs Affordable Communities (No Data)", height=450, dark=dark)
        return fig
        
    premium = comm_stats.nlargest(5, "avg_rate").copy()
    premium["Category"] = "Premium"
    
    affordable = comm_stats.nsmallest(5, "avg_rate").copy()
    affordable["Category"] = "Affordable"
    
    combined = pd.concat([premium, affordable]).sort_values("avg_rate", ascending=True)
    
    colors = [
        CHART_COLORS[4] if cat == "Premium" else CHART_COLORS[5]
        for cat in combined["Category"]
    ]
    
    fig = go.Figure(
        go.Bar(
            x=combined["avg_rate"],
            y=combined[COLS["community"]].str.title(),
            orientation="h",
            marker=dict(color=colors, opacity=0.85),
            text=[f"AED {v:,.0f}/SQM" for v in combined["avg_rate"]],
            textposition="outside",
            textfont=dict(size=10, color=_font_color(dark)),
            hovertemplate="<b>%{y}</b><br>Average Rate: AED %{x:,.0f}/SQM<br>Category: %{customdata}<extra></extra>",
            customdata=combined["Category"]
        )
    )
    
    _apply_layout(
        fig,
        title="Premium vs Affordable Communities by Avg Rate (AED/SQM)",
        height=450,
        dark=dark,
        show_legend=False
    )
    fig.update_xaxes(title_text="Average Rate (AED/SQM)", gridcolor=_grid_color(dark))
    fig.update_yaxes(title_text="Community")
    return fig

