"""
Reusable UI component renderers — premium dual-mode design.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import format_currency, format_number


# ─────────────────────────────────────────────────────────────────────────────
# KPI Card
# ─────────────────────────────────────────────────────────────────────────────

def kpi_card(
    label: str,
    value: str,
    icon: str = "📊",
    delta: str = None,
    delta_positive: bool = True,
    color_class: str = "blue",
    tooltip: str = None,
) -> str:
    """Return HTML for a single KPI card (premium flat design)."""

    delta_html = ""
    if delta:
        arrow = "↑" if delta_positive else "↓"
        cls   = "positive" if delta_positive else "negative"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {delta}</div>'

    tip = f'title="{tooltip}"' if tooltip else ""

    html = f"""
    <div class="kpi-card {color_class}" {tip}>
        <div class="kpi-icon-box">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """
    return " ".join(html.split())



# ─────────────────────────────────────────────────────────────────────────────
# Section Header
# ─────────────────────────────────────────────────────────────────────────────

def section_header(
    title: str,
    subtitle: str = "",
    icon: str = "📊",
    color_class: str = "blue",   # kept for compat, not used visually now
):
    """Render a styled section header with icon (stripped of newlines to avoid markdown parsing bugs)."""
    subtitle_html = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    html = f"""
    <div class="section-header">
        <div class="section-icon">{icon}</div>
        <div>
            <h3 class="section-title">{title}</h3>
            {subtitle_html}
        </div>
    </div>
    """
    # Strip newlines and extra spaces to ensure Streamlit's markdown parser doesn't split on blank lines
    clean_html = " ".join(html.split())
    st.markdown(clean_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Insight Card
# ─────────────────────────────────────────────────────────────────────────────

def insight_card(emoji: str, text: str):
    """Render a single insight row."""
    html = f"""
    <div class="insight-card">
        <span class="insight-emoji">{emoji}</span>
        <p class="insight-text">{text}</p>
    </div>
    """
    clean_html = " ".join(html.split())
    st.markdown(clean_html, unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────────────────────────
# Chart Description
# ─────────────────────────────────────────────────────────────────────────────

def chart_description(text: str):
    """Blue-left-bordered explanatory note beneath a chart."""
    st.markdown(
        f'<p class="chart-description">💡 {text}</p>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Info Box
# ─────────────────────────────────────────────────────────────────────────────

def info_box(text: str):
    """Light blue informational callout box."""
    st.markdown(
        f'<div class="info-box"><p>{text}</p></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Hero Section
# ─────────────────────────────────────────────────────────────────────────────

def hero_section(
    total_records: int,
    total_value: float,
    avg_price_sqm: float,
    years_range: str,
    last_refresh: str,
):
    """Landing hero block with title, subtitle, and headline KPIs."""
    total_val_str = format_currency(total_value)
    avg_rate_str  = format_currency(avg_price_sqm)

    html = f"""
    <div class="hero-container">
        <div class="hero-eyebrow">🏙️ Live Market Intelligence</div>
        <h1 class="hero-title">Abu Dhabi <span>Real Estate</span> Market Dashboard</h1>
        <p class="hero-subtitle">
            Enterprise analytics platform for the Abu Dhabi residential property market.
            Covering {years_range} — powered by official transaction data.
        </p>
        <div class="hero-stats">
            <div>
                <div class="hero-stat-value">{total_records:,}</div>
                <div class="hero-stat-label">Total Transactions</div>
            </div>
            <div>
                <div class="hero-stat-value">{total_val_str}</div>
                <div class="hero-stat-label">Total Market Value</div>
            </div>
            <div>
                <div class="hero-stat-value">{avg_rate_str}</div>
                <div class="hero-stat-label">Median Rate / SQM</div>
            </div>
            <div>
                <div class="hero-stat-value">{last_refresh}</div>
                <div class="hero-stat-label">Last Refreshed</div>
            </div>
        </div>
    </div>
    """
    clean_html = " ".join(html.split())
    st.markdown(clean_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Ranked Table
# ─────────────────────────────────────────────────────────────────────────────

def render_top_table(
    df_top: pd.DataFrame,
    rank_col: str,
    value_col: str,
    value_label: str,
):
    """Render a clean HTML ranked table."""
    rows = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, (_, row) in enumerate(df_top.iterrows(), 1):
        medal = medals[i - 1] if i <= 3 else f"#{i}"
        rows += f"""
            <tr>
                <td><span class="rank-number">{medal}</span></td>
                <td>{row[rank_col]}</td>
                <td style="text-align:right; font-weight:700; color:#2563EB;">{row[value_col]}</td>
            </tr>
        """

    html = f"""
    <div style="overflow-x:auto;">
    <table class="rank-table">
        <thead>
            <tr>
                <th>#</th>
                <th>{rank_col}</th>
                <th style="text-align:right">{value_label}</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    </div>
    """
    clean_html = " ".join(html.split())
    st.markdown(clean_html, unsafe_allow_html=True)

