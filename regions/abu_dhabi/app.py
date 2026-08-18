"""
Abu Dhabi Real Estate Market Intelligence Dashboard
====================================================
Production-grade Streamlit application — premium enterprise UI.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import io

# ── Path Setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── UNIFIED PLATFORM INTEGRATION ─────────────────────────────────────────────
# Added so this dashboard can run either standalone or embedded in the unified
# UAE Real Estate Analytics shell. See docs/INTEGRATION_CHANGES.md — AD-1.
_PLATFORM_ROOT = BASE_DIR.parent.parent
if str(_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_ROOT))
from platform_core.region_bridge import (
    page_config as _platform_page_config,
    render_region_brand as _platform_region_brand,
    render_theme_toggle as _platform_theme_toggle,
)

# ── Imports ───────────────────────────────────────────────────────────────────
from config.settings import COLS, CHART_HEIGHT, PLOTLY_CONFIG
from styles.theme import build_css, get_plotly_layout, CHART_COLORS
from utils.data_loader import (
    load_data,
    get_apartments_df,
    get_cleaned_apartments_df,
    apply_filters,
    format_currency,
    format_number,
)
from components.ui_components import (
    kpi_card,
    section_header,
    insight_card,
    chart_description,
    hero_section,
    render_top_table,
    info_box,
)
from charts.plotly_charts import (
    monthly_trend_chart,
    yearly_trend_chart,
    quarterly_trend_chart,
    price_trend_line,
    price_distribution_chart,
    price_box_by_layout,
    price_scatter,
    top_areas_price,
    district_treemap,
    community_sunburst,
    top_communities_bar,
    property_type_donut,
    layout_bar_chart,
    sale_type_pie,
    sale_sequence_pie,
    correlation_heatmap,
    violin_plot,
    density_plot,
    outlier_boxplot,
    monthly_seasonality_chart,
    yoy_growth_chart,
    apt_yoy_growth_chart,
    missing_values_chart,
    district_bubble_chart,
    apt_rate_volume_chart,
    premium_vs_affordable_communities_chart,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

# AD-2: the unified platform owns the single global page configuration.
# Standalone, this behaves exactly as st.set_page_config() did before.
_platform_page_config(
    page_title="Abu Dhabi Real Estate Intelligence",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# THEME STATE
# ─────────────────────────────────────────────────────────────────────────────

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Inject CSS for the current theme
st.markdown(build_css(dark=st.session_state.dark_mode), unsafe_allow_html=True)

DARK = st.session_state.dark_mode
PC   = PLOTLY_CONFIG


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load():
    raw     = load_data()
    apt     = get_apartments_df(raw)
    cleaned = get_cleaned_apartments_df(raw)
    return raw, apt, cleaned


with st.spinner("🔄 Loading market data…"):
    df_raw, df_apt, df_apt_cleaned = _load()

df_all = df_raw.copy()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:

    # ── Logo ──────────────────────────────────────────────────────────────────
    # AD-3: suppressed when embedded (the platform rail already shows the brand).
    _platform_region_brand(
        '<div class="sidebar-logo"><div style="font-size:2rem">🏙️</div><p class="sidebar-logo-title">Abu Dhabi RE Intelligence</p><p class="sidebar-logo-sub">Market Analytics Platform</p></div>'
    )


    # ── Theme Toggle ──────────────────────────────────────────────────────────
    # AD-4: embedded, appearance is a platform-level control writing to the same
    # `dark_mode` session key; standalone, the original toggle is rendered.
    _platform_theme_toggle(DARK)

    # ── Dataset scope ─────────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">📦 Data Scope</p>', unsafe_allow_html=True)
    dataset_scope = st.selectbox(
        "Dataset",
        ["All Properties", "Residential Apartments Only"],
        help="Choose whether to analyse all property types or apartments only.",
    )
    df_working = df_all if dataset_scope == "All Properties" else df_apt


    # ── Year filter ───────────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">📅 Time Period</p>', unsafe_allow_html=True)
    all_years = sorted(df_working["Year"].dropna().unique().astype(int).tolist())
    sel_years = st.multiselect("Year(s)", all_years, default=all_years)

    # ── Property filters ──────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">🏘️ Property</p>', unsafe_allow_html=True)
    all_types = sorted(df_working[COLS["property_type"]].dropna().unique().tolist())
    sel_types = st.multiselect("Property Type", all_types)

    all_layouts = sorted(df_working[COLS["layout"]].dropna().unique().tolist())
    sel_layouts = st.multiselect("Property Layout", all_layouts)

    # ── Location filters ──────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">📍 Location</p>', unsafe_allow_html=True)
    all_districts = sorted(df_working[COLS["district"]].dropna().unique().tolist())
    sel_districts = st.multiselect("District", all_districts)

    # ── Transaction filters ───────────────────────────────────────────────────
    st.markdown('<p class="filter-header">💼 Transaction</p>', unsafe_allow_html=True)
    all_sale_types = sorted(df_working[COLS["sale_type"]].dropna().unique().tolist())
    sel_sale_types = st.multiselect("Sale Type", all_sale_types)

    all_sale_seq = sorted(df_working[COLS["sale_sequence"]].dropna().unique().tolist())
    sel_sale_seq = st.multiselect("Market (Primary / Secondary)", all_sale_seq)

    # ── Price range ───────────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">💰 Price Range</p>', unsafe_allow_html=True)
    p1_price  = float(df_working[COLS["price"]].quantile(0.01))
    p99_price = float(df_working[COLS["price"]].quantile(0.99))
    price_range = st.slider(
        "Sale Price (AED)",
        min_value=p1_price,
        max_value=p99_price,
        value=(p1_price, p99_price),
        format="%.0f",
    )

    # ── Area range ────────────────────────────────────────────────────────────
    st.markdown('<p class="filter-header">📐 Area Range</p>', unsafe_allow_html=True)
    valid_areas = df_working[COLS["area_sqm"]].dropna()
    p1_area  = float(valid_areas.quantile(0.01))
    p99_area = float(valid_areas.quantile(0.99))
    area_range = st.slider(
        "Sold Area (SQM)",
        min_value=p1_area,
        max_value=p99_area,
        value=(p1_area, p99_area),
        format="%.0f",
    )

    st.markdown("---")

    # ── Reset Button ──────────────────────────────────────────────────────────
    if st.button("🔄 Reset All Filters", use_container_width=True):
        for key in ["years", "prop_types", "layouts", "districts", "sale_types", "sale_seq"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown(
        f'<p style="font-size:0.68rem; color:#9CA3AF; text-align:center; margin-top:0.75rem;">Refreshed: {datetime.now().strftime("%d %b %Y %H:%M")}</p>',
        unsafe_allow_html=True,
    )




# ── Apartments flag (used to gate apartments-only UI sections) ──────────────────
IS_APARTMENTS = (dataset_scope == "Residential Apartments Only")

# ── Apply Filters ─────────────────────────────────────────────────────────────

df = apply_filters(
    df_working,
    years=sel_years       if sel_years       else None,
    property_types=sel_types    if sel_types    else None,
    districts=sel_districts if sel_districts  else None,
    layouts=sel_layouts   if sel_layouts      else None,
    sale_types=sel_sale_types if sel_sale_types else None,
    sale_sequences=sel_sale_seq  if sel_sale_seq  else None,
    price_range=price_range,
    area_range=area_range,
)

if df.empty:
    st.error("⚠️ No data matches the current filters. Please adjust your selections.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# PRE-COMPUTE KPIs
# ─────────────────────────────────────────────────────────────────────────────

total_records  = len(df)
total_sales    = df[COLS["price"]].sum()
avg_price      = df[COLS["price"]].mean()
median_price   = df[COLS["price"]].median()
avg_rate       = df[COLS["rate"]].mean()
median_rate    = df[COLS["rate"]].median()
max_price      = df[COLS["price"]].max()
min_price      = df[COLS["price"]].min()
n_districts    = df[COLS["district"]].nunique()
n_communities  = df[COLS["community"]].nunique()
n_projects     = df[COLS["project"]].nunique()
n_property_types = df[COLS["property_type"]].nunique()
years_range    = f"{int(df['Year'].min())}–{int(df['Year'].max())}"
last_refresh   = datetime.now().strftime("%d %b %Y")


# ─────────────────────────────────────────────────────────────────────────────
# HERO SECTION
# ─────────────────────────────────────────────────────────────────────────────

hero_section(
    total_records=total_records,
    total_value=total_sales,
    avg_price_sqm=median_rate,
    years_range=years_range,
    last_refresh=last_refresh,
)


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTIVE KPI CARDS  (3 rows × 4 cards)
# ─────────────────────────────────────────────────────────────────────────────

section_header("Executive KPIs", "Real-time key performance indicators", "📊")

kpi_data = [
    # Row 1
    dict(label="Total Transactions", value=f"{total_records:,}",          icon="🔢", color_class="blue",   tooltip="Total property deals in the filtered period."),
    dict(label="Total Market Value",  value=format_currency(total_sales),  icon="💰", color_class="teal",   tooltip="Aggregate value of all filtered sales (AED)."),
    dict(label="Median Sale Price",   value=format_currency(median_price), icon="🏷️", color_class="amber",  tooltip="Midpoint price — 50% of sales above and below."),
    dict(label="Average Sale Price",  value=format_currency(avg_price),    icon="📈", color_class="blue",   tooltip="Mean (average) sale price across all transactions."),
    # Row 2
    dict(label="Median Rate / SQM",  value=format_currency(median_rate, 0), icon="📐", color_class="teal",  tooltip="Best apples-to-apples value benchmark."),
    dict(label="Average Rate / SQM", value=format_currency(avg_rate, 0),    icon="📏", color_class="green",  tooltip="Mean price per square metre."),
    dict(label="Highest Sale",        value=format_currency(max_price),     icon="🏆", color_class="amber",  tooltip="Single highest property transaction."),
    dict(label="Lowest Sale",         value=format_currency(min_price),     icon="📉", color_class="rose",   tooltip="Single lowest property transaction."),
    # Row 3
    dict(label="Active Districts",   value=f"{n_districts}",        icon="🗺️", color_class="violet", tooltip="Unique districts in filtered data."),
    dict(label="Communities",        value=f"{n_communities}",      icon="🏘️", color_class="sky",    tooltip="Unique communities in filtered data."),
    dict(label="Projects",           value=f"{n_projects}",         icon="🏗️", color_class="teal",   tooltip="Unique development projects."),
    dict(label="Property Types",     value=f"{n_property_types}",   icon="🏠", color_class="blue",   tooltip="Distinct property categories."),
]

for row_start in range(0, len(kpi_data), 4):
    cols = st.columns(4)
    for i, col in enumerate(cols):
        idx = row_start + i
        if idx < len(kpi_data):
            k = kpi_data[idx]
            with col:
                st.markdown(
                    kpi_card(
                        label=k["label"],
                        value=k["value"],
                        icon=k["icon"],
                        color_class=k["color_class"],
                        tooltip=k.get("tooltip"),
                    ),
                    unsafe_allow_html=True,
                )
    st.markdown("<div style='margin-bottom:0.75rem'></div>", unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "💡 Insights",
    "📈 Trends",
    "🗺️ Geographic",
    "🏠 Property",
    "💵 Price",
    "📊 Distribution",
    "🕐 Time Series",
    "🔗 Correlations",
    "⚠️ Outliers",
    "🔍 Data Quality",
    "⬇️ Download",
    "ℹ️ About",
])

(
    tab_insights, tab_trends, tab_geo, tab_property, tab_price,
    tab_dist, tab_time, tab_corr, tab_outlier, tab_quality,
    tab_download, tab_about,
) = tabs


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — BUSINESS INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────

with tab_insights:
    section_header("Smart Business Insights", "Automatically derived from the filtered market data", "💡")

    # ── Compute insight metrics ────────────────────────────────────────────────
    top_dist_txn       = df.groupby(COLS["district"])[COLS["price"]].count().idxmax()
    top_dist_txn_count = df.groupby(COLS["district"])[COLS["price"]].count().max()
    top_dist_txn_pct   = round(top_dist_txn_count / total_records * 100, 1)

    dist_prices = (
        df.groupby(COLS["district"])
        .agg(count=(COLS["price"], "count"), median_price=(COLS["price"], "median"))
        .query("count >= 30")
    )
    top_dist_price     = dist_prices["median_price"].idxmax() if not dist_prices.empty else "N/A"
    top_dist_price_val = dist_prices["median_price"].max()    if not dist_prices.empty else 0

    if len(df["Year"].unique()) > 1:
        top_year       = df.groupby("Year")[COLS["price"]].count().idxmax()
        top_year_count = df.groupby("Year")[COLS["price"]].count().max()
    else:
        top_year       = int(df["Year"].iloc[0])
        top_year_count = total_records

    if COLS["sale_type"] in df.columns:
        sc = df[COLS["sale_type"]].value_counts(normalize=True)
        offplan_pct = round(sc.get("off-plan", 0) * 100, 1)
        ready_pct   = round(sc.get("ready",    0) * 100, 1)
    else:
        offplan_pct = ready_pct = "N/A"

    valid_layouts = df[df[COLS["layout"]] != "unclassified"][COLS["layout"]]
    top_layout     = valid_layouts.value_counts().idxmax()      if not valid_layouts.empty else "N/A"
    top_layout_pct = round(valid_layouts.value_counts(normalize=True).max() * 100, 1) if not valid_layouts.empty else 0

    if len(df["Year"].unique()) >= 2:
        yp          = df.groupby("Year")[COLS["price"]].median()
        ys          = sorted(yp.index)
        latest_y, prev_y = ys[-1], ys[-2]
        yoy_change  = round((yp[latest_y] - yp[prev_y]) / yp[prev_y] * 100, 1)
        yoy_dir     = "increased" if yoy_change > 0 else "decreased"
        yoy_abs     = abs(yoy_change)
    else:
        yoy_change = 0; yoy_dir = "unchanged"; yoy_abs = 0
        latest_y = int(df["Year"].iloc[0]); prev_y = latest_y - 1

    comm_rates = (
        df.groupby(COLS["community"])
        .agg(count=(COLS["rate"], "count"), median_rate=(COLS["rate"], "median"))
        .query("count >= 20")
    )
    top_comm_rate     = comm_rates["median_rate"].idxmax() if not comm_rates.empty else "N/A"
    top_comm_rate_val = comm_rates["median_rate"].max()    if not comm_rates.empty else 0

    if COLS["sale_sequence"] in df.columns:
        primary_pct = round(df[COLS["sale_sequence"]].value_counts(normalize=True).get("primary", 0) * 100, 1)
    else:
        primary_pct = "N/A"

    # ── Render insight cards ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        insight_card("🏆", f"<span class='insight-highlight'>{top_dist_txn.title()}</span> is the most active district — <span class='insight-highlight'>{top_dist_txn_pct}%</span> of all transactions ({top_dist_txn_count:,} deals). Strong buyer demand and developer presence characterise this area.")
        insight_card("💎", f"<span class='insight-highlight'>{top_dist_price.title()}</span> commands the highest median price at <span class='insight-highlight'>AED {top_dist_price_val:,.0f}</span>, representing the premium tier of the Abu Dhabi market.")
        insight_card("📅", f"<span class='insight-highlight'>{top_year}</span> recorded the peak annual volume with <span class='insight-highlight'>{top_year_count:,}</span> transactions — the busiest market year in the dataset.")
        insight_card("📉", f"Median prices <span class='insight-highlight'>{yoy_dir}</span> by <span class='insight-highlight'>{yoy_abs}%</span> from {prev_y} to {latest_y} — signalling a {'strengthening' if yoy_change > 0 else 'softening'} market trend.")

    with col2:
        insight_card("🏗️", f"<span class='insight-highlight'>{offplan_pct}%</span> of transactions are off-plan (under construction); <span class='insight-highlight'>{ready_pct}%</span> are ready-to-occupy — indicating {'strong' if offplan_pct > 50 else 'moderate'} confidence in future developments.")
        insight_card("🛏️", f"The most popular layout is <span class='insight-highlight'>{top_layout.title()}</span>, accounting for <span class='insight-highlight'>{top_layout_pct}%</span> of classified deals — highlighting buyer preference.")
        insight_card("⭐", f"<span class='insight-highlight'>{top_comm_rate.title()}</span> achieves the highest rate/SQM at <span class='insight-highlight'>AED {top_comm_rate_val:,.0f}/SQM</span> — the most premium community in the filtered dataset.")
        insight_card("🔑", f"<span class='insight-highlight'>{primary_pct}%</span> of sales are primary market (developer direct) — a {'developer-driven' if isinstance(primary_pct, float) and primary_pct > 50 else 'resale-dominated'} marketplace.")

    st.markdown("---")

    # Market snapshot metrics
    section_header("Market Snapshot", "Quick-reference summary statistics", "📋")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Median Sale Price",  format_currency(median_price))
        st.metric("Median Rate / SQM",  format_currency(median_rate, 0))
    with c2:
        st.metric("Total Market Value", format_currency(total_sales))
        st.metric("Active Districts",   str(n_districts))
    with c3:
        st.metric("Total Transactions", f"{total_records:,}")
        st.metric("Active Communities", str(n_communities))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SALES TRENDS
# ─────────────────────────────────────────────────────────────────────────────

with tab_trends:
    section_header("Sales Trends & Market Dynamics", "Transaction volume and value over time", "📈")

    st.markdown("#### 📅 Monthly Transaction Trend")
    with st.spinner("Building chart…"):
        st.plotly_chart(monthly_trend_chart(df, dark=DARK), use_container_width=True, config=PC)
    chart_description(
        "Blue area = monthly transaction count. Dotted line = 3-month rolling average (smoothed trend). "
        "Green bars = total sales value. Peaks indicate periods of peak market activity."
    )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📆 Annual Volume")
        with st.spinner():
            st.plotly_chart(yearly_trend_chart(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Annual transaction count 2019–present. Taller bars = more deals = higher market activity.")

    with c2:
        st.markdown("#### 🗓️ Quarterly Heatmap")
        with st.spinner():
            st.plotly_chart(quarterly_trend_chart(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Brighter cells = more transactions. Reveals seasonal and cyclical patterns across quarters.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — GEOGRAPHIC
# ─────────────────────────────────────────────────────────────────────────────

with tab_geo:
    section_header("Geographic Market Analysis", "Where transactions happen across Abu Dhabi", "🗺️")

    st.markdown("#### 🗺️ District Transaction Volume — Treemap")
    with st.spinner():
        st.plotly_chart(district_treemap(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("Larger box = more transactions. Hover for deal count and combined value per district.")

    st.markdown("---")
    # District → Community Hierarchy removed to keep the view clean and focused.
    if not IS_APARTMENTS:
        st.markdown("#### 🏘️ Top 15 Communities by Volume")
        with st.spinner():
            st.plotly_chart(top_communities_bar(df, n=15, dark=DARK), use_container_width=True, config=PC)
        chart_description("The 15 most active communities ranked by number of transactions.")

    else:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### ⚖️ Premium vs Affordable Communities")
            with st.spinner():
                st.plotly_chart(premium_vs_affordable_communities_chart(df, dark=DARK), use_container_width=True, config=PC)
            chart_description("Comparison of top 5 premium and top 5 affordable communities by average Rate (AED/SQM).")

        with c2:
            st.markdown("#### 🏘️ Top 15 Communities by Volume")
            with st.spinner():
                st.plotly_chart(top_communities_bar(df, n=15, dark=DARK), use_container_width=True, config=PC)
            chart_description("The 15 most active communities ranked by number of transactions.")


    st.markdown("---")
    st.markdown("#### 🔮 District Volume vs Median Price — Bubble Chart")
    with st.spinner():
        st.plotly_chart(district_bubble_chart(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("X = volume, Y = median price, bubble size = total market value. Top-right = active AND expensive districts.")

    st.markdown("---")
    st.markdown("#### 💎 Most Expensive Districts by Rate / SQM")
    with st.spinner():
        st.plotly_chart(top_areas_price(df, n=15, dark=DARK), use_container_width=True, config=PC)
    chart_description("Districts ranked by median price per SQM — the best indicator of true property value.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — PROPERTY
# ─────────────────────────────────────────────────────────────────────────────

with tab_property:
    section_header("Property Type & Characteristics", "Breakdown by type, layout and sale category", "🏠")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏘️ Property Type Mix")
        with st.spinner():
            st.plotly_chart(property_type_donut(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("How the market is split by property category. Hover for count and share.")

    with c2:
        st.markdown("#### 🛏️ Layout Distribution")
        with st.spinner():
            st.plotly_chart(layout_bar_chart(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Most popular bedroom configurations — reveals what buyers are choosing.")

    st.markdown("---")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 🏗️ Off-Plan vs Ready")
        with st.spinner():
            st.plotly_chart(sale_type_pie(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Off-plan = under construction (lower price, higher risk). Ready = immediate occupation.")

    with c4:
        st.markdown("#### 🔄 Primary vs Secondary Market")
        with st.spinner():
            st.plotly_chart(sale_sequence_pie(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Primary = direct from developer. Secondary = resale from prior owner.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — PRICE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

with tab_price:
    section_header("Price Analysis", "Pricing trends, distributions and comparisons", "💵")

    st.markdown("#### 📈 Median Price & Rate / SQM — Monthly Trend")
    with st.spinner():
        st.plotly_chart(price_trend_line(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("Left = median sale price monthly trend. Right = median rate/SQM. Rising lines indicate property value appreciation.")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📊 Sale Price Distribution")
        with st.spinner():
            st.plotly_chart(price_distribution_chart(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Tallest bars = where most transactions occur. Right-skew is normal — a few luxury sales pull the average upward.")

    with c2:
        st.markdown("#### 📦 Price by Layout — Box Plot")
        with st.spinner():
            st.plotly_chart(price_box_by_layout(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Box = middle 50% of prices. Line = median. Whiskers = typical range. Dots = unusual sales (outliers).")

    st.markdown("---")
    st.markdown("#### 🔵 Property Area vs Sale Price — Scatter")
    with st.spinner():
        st.plotly_chart(price_scatter(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("Each dot = one transaction. Trend line = overall size-price relationship. Points far from line = premium or discounted deals.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — DISTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────

with tab_dist:
    section_header("Statistical Distribution Analysis", "Shape and spread of key market variables", "📊")

    st.markdown("#### 🎻 Rate / SQM Distribution by Year — Violin Plot")
    with st.spinner():
        st.plotly_chart(violin_plot(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("Wider = more transactions at that price level. Each violin = one year. Reveals how the price distribution evolves annually.")

    st.markdown("---")

    if IS_APARTMENTS:
        # ── Apartments view: professional text summary (replaces both density charts) ──
        _apt = df_apt_cleaned  # already p1-p99 treated
        _price_med   = _apt[COLS["price"]].median()
        _price_mean  = _apt[COLS["price"]].mean()
        _price_p25   = _apt[COLS["price"]].quantile(0.25)
        _price_p75   = _apt[COLS["price"]].quantile(0.75)
        _price_skew  = _apt[COLS["price"]].skew()
        _rate_med    = _apt[COLS["rate"]].median()
        _rate_mean   = _apt[COLS["rate"]].mean()
        _rate_p25    = _apt[COLS["rate"]].quantile(0.25)
        _rate_p75    = _apt[COLS["rate"]].quantile(0.75)
        _rate_skew   = _apt[COLS["rate"]].skew()

        section_header("Distribution Summary", "Statistical profile of the cleaned Residential Apartments dataset", "📋")

        _c1, _c2 = st.columns(2)
        with _c1:
            st.markdown("##### 💰 Sale Price Distribution")
            st.markdown(
                f"""
**The Sale Price distribution is right-skewed** (skewness ≈ {_price_skew:.2f}), meaning a majority of \
apartment transactions cluster at lower price points with a long tail of high-value deals.

| Statistic | Value |
|---|---|
| **Median** | AED {_price_med:,.0f} |
| **Mean** | AED {_price_mean:,.0f} |
| **25th Percentile** | AED {_price_p25:,.0f} |
| **75th Percentile** | AED {_price_p75:,.0f} |

**Business Insight:** The median sale price of **AED {_price_med/1e6:.2f}M** is the most reliable benchmark \
for the Abu Dhabi apartment market. The gap between mean and median (AED {(_price_mean-_price_med)/1e3:,.0f}K) \
confirms the influence of premium deals on the average. The interquartile range \
(AED {_price_p25/1e3:,.0f}K – AED {_price_p75/1e6:.2f}M) captures the core market where 50% of \
transactions are priced.
"""
            )

        with _c2:
            st.markdown("##### 📐 Rate / SQM Distribution")
            st.markdown(
                f"""
**The Rate per SQM distribution is moderately right-skewed** (skewness ≈ {_rate_skew:.2f}), \
reflecting a diverse market ranging from affordable community apartments to premium branded residences.

| Statistic | Value |
|---|---|
| **Median** | AED {_rate_med:,.0f} / SQM |
| **Mean** | AED {_rate_mean:,.0f} / SQM |
| **25th Percentile** | AED {_rate_p25:,.0f} / SQM |
| **75th Percentile** | AED {_rate_p75:,.0f} / SQM |

**Business Insight:** The median Rate of **AED {_rate_med:,.0f}/SQM** is the industry-standard \
comparator for apartment value across layouts and locations. Studios and 1-bedroom units \
typically achieve a premium Rate/SQM relative to larger units due to higher \
rental yield efficiency. The spread from AED {_rate_p25:,.0f} to AED {_rate_p75:,.0f}/SQM \
represents the mid-market band where the majority of transactions occur.
"""
            )

        st.info(
            "📊 **Note:** These statistics are computed on the fully cleaned Residential Apartments dataset "
            f"({len(_apt):,} transactions after 1st–99th percentile outlier treatment on Rate, Price, and Area), "
            "matching the source notebook's `df_cleaned` pipeline."
        )

    else:
        # ── All Properties view: show density charts as before ────────────────
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📈 Sale Price Density")
            with st.spinner():
                st.plotly_chart(density_plot(df, COLS["price"], "Sale Price Density", dark=DARK), use_container_width=True, config=PC)
            chart_description("Peak of the curve = where most transactions are concentrated.")

        with c2:
            if df[COLS["rate"]].notna().sum() > 100:
                st.markdown("#### 📈 Rate / SQM Density")
                with st.spinner():
                    st.plotly_chart(density_plot(df, COLS["rate"], "Rate per SQM Density", dark=DARK), use_container_width=True, config=PC)
                chart_description("Multiple peaks suggest distinct pricing tiers (e.g. luxury vs affordable segments).")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — TIME SERIES
# ─────────────────────────────────────────────────────────────────────────────

with tab_time:
    section_header("Time Series & Seasonality", "Seasonal patterns and year-over-year growth", "🕐")

    st.markdown("#### 🌊 Monthly Seasonal Patterns")
    with st.spinner():
        st.plotly_chart(monthly_seasonality_chart(df, dark=DARK), use_container_width=True, config=PC)
    chart_description("How market activity varies by calendar month across all years. Common seasonal peaks relate to school year and holidays.")

    st.markdown("---")
    if IS_APARTMENTS:
        # ── Apartments view: YoY (cleaned data) side-by-side with Actual Trends ──
        _tc1, _tc2 = st.columns(2)
        with _tc1:
            st.markdown("#### 📊 Year-over-Year Growth Rates")
            with st.spinner():
                st.plotly_chart(
                    apt_yoy_growth_chart(df_apt_cleaned, dark=DARK),
                    use_container_width=True, config=PC
                )
            chart_description(
                "Green bars = Rate/SQM growth vs. prior year. "
                "Dotted line = Volume growth %. Both computed from df_cleaned — "
                "mathematically consistent with the Actual Trends chart."
            )
        with _tc2:
            st.markdown("#### 📈 Avg Rate & Transaction Volume (Annual)")
            with st.spinner():
                st.plotly_chart(
                    apt_rate_volume_chart(df_apt_cleaned, dark=DARK),
                    use_container_width=True, config=PC
                )
            chart_description(
                "Blue line = Avg Rate (AED/SQM) on left axis. "
                "Grey bars = Transaction Volume on right axis. "
                "Source: notebook df_cleaned — 1st–99th percentile filtered."
            )

        # ── Business Interpretation ─────────────────────────────────────────
        import math as _math
        _yly = (
            df_apt_cleaned.groupby("Year")
            .agg(avg_rate=(COLS["rate"], "mean"), volume=(COLS["rate"], "count"))
            .reset_index().sort_values("Year")
        )
        _yly["yoy_rate"] = _yly["avg_rate"].pct_change() * 100
        _yly["yoy_vol"]  = _yly["volume"].pct_change()  * 100
        _plot_yly = _yly.dropna(subset=["yoy_rate"])
        _best  = _plot_yly.loc[_plot_yly["yoy_rate"].idxmax()]
        _worst = _plot_yly.loc[_plot_yly["yoy_rate"].idxmin()]
        _first_rate = _yly["avg_rate"].iloc[0]
        _last_rate  = _yly["avg_rate"].iloc[-1]
        _total_apprec = ((_last_rate / _first_rate) - 1) * 100
        _first_yr = int(_yly["Year"].iloc[0])
        _last_yr  = int(_yly["Year"].iloc[-1])
        _pos_years = (_plot_yly["yoy_rate"] > 0).sum()
        _neg_years = (_plot_yly["yoy_rate"] < 0).sum()
        _avg_growth = _plot_yly["yoy_rate"].mean()

        st.markdown("---")
        st.markdown("#### 🔍 Business Interpretation")
        st.markdown(
            f"""
**Overall Market Trend:** The Abu Dhabi Residential Apartment market has shown sustained \
price appreciation from {_first_yr} to {_last_yr}. The average Rate per SQM rose from \
**AED {_first_rate:,.0f}** to **AED {_last_rate:,.0f}** — a total appreciation of \
**{_total_apprec:.1f}%** over this period, representing a compound market re-rating.

**Year-over-Year Performance:**

| Metric | Value |
|---|---|
| **Average Annual Rate Growth** | {_avg_growth:+.1f}% per year |
| **Best YoY Year** | {int(_best['Year'])} (+{_best['yoy_rate']:.1f}% rate growth) |
| **Slowest YoY Year** | {int(_worst['Year'])} ({_worst['yoy_rate']:+.1f}% rate growth) |
| **Growth Years** | {_pos_years} out of {len(_plot_yly)} years post-base |

**Key Observations:**
- **{int(_best['Year'])}** delivered the strongest annual appreciation (+**{_best['yoy_rate']:.1f}%**), \
likely driven by post-pandemic demand recovery, infrastructure milestones, and strong off-plan sales momentum.
- **{int(_worst['Year'])}** saw the lowest growth rate ({_worst['yoy_rate']:+.1f}%), reflecting temporary \
market consolidation rather than fundamental weakness — base rates remained resilient.
- Transaction volume and price growth are not always correlated: high-volume years can \
coexist with moderate price growth (supply absorption), while low-volume years sometimes \
drive sharper price moves as supply tightens.

**Business Implications:** The consistent positive rate trajectory signals a fundamentally \
strong market with durable demand drivers — tourism growth, population influx, Expo legacy, \
and UAE's safe-haven investment appeal. Investors entering at trough-volume years \
(e.g., {int(_worst['Year'])}) and holding multi-year have captured significantly above-average returns.
"""
        )
    else:
        st.markdown("#### 📊 Year-over-Year Growth Rates")
        with st.spinner():
            st.plotly_chart(yoy_growth_chart(df, dark=DARK), use_container_width=True, config=PC)
        chart_description("Green bars = growth year. Red = contraction. Dotted line = price growth. Rising dotted line indicates property value appreciation.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — CORRELATIONS
# ─────────────────────────────────────────────────────────────────────────────

with tab_corr:
    section_header("Correlation Analysis", "Statistical relationships between market variables", "🔗")

    info_box(
        "📚 <b>How to read:</b> Each cell shows correlation between two variables. "
        "<b>+1.0</b> (dark blue) = move perfectly together. "
        "<b>−1.0</b> (dark red) = opposite directions. "
        "<b>Near 0</b> = no relationship. Stronger colour = stronger link."
    )

    with st.spinner():
        st.plotly_chart(correlation_heatmap(df, dark=DARK), use_container_width=True, config=PC)

    st.markdown("---")
    section_header("Key Relationships Explained", "What the correlations mean in plain English", "💡")

    insight_card("📐", "Property Sold Area (SQM) and Property Sale Price (AED) have a <span class='insight-highlight'>strong positive correlation (0.73)</span>, indicating that larger properties tend to have higher sale prices.")
    insight_card("💰", "Property Sale Price (AED) and Rate (AED per SQM) also show a <span class='insight-highlight'>moderate to strong positive correlation (0.65)</span>, meaning higher total price is associated with higher price per square metre.")
    insight_card("🔗", "Property Sold Area (SQM) and Rate (AED per SQM) have a <span class='insight-highlight'>very weak positive correlation (0.09)</span>, suggesting little to no direct relationship between property area and rate.")
    insight_card("⬛", "The <span class='insight-highlight'>diagonal values are 1.00</span>, as each variable is perfectly correlated with itself.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 9 — OUTLIERS
# ─────────────────────────────────────────────────────────────────────────────

with tab_outlier:
    section_header("Outlier Analysis", "Identifying and contextualising extreme values", "⚠️")

    info_box(
        "📚 <b>What are outliers?</b> Transactions with unusually high or low values. "
        "They may be genuine ultra-luxury deals, data anomalies, or unique property types. "
        "Understanding them ensures analysis accuracy."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💰 Sale Price Outliers")
        with st.spinner():
            st.plotly_chart(outlier_boxplot(df, COLS["price"], "Sale Price — Before vs After Outlier Removal", dark=DARK), use_container_width=True, config=PC)
        chart_description("Blue box = full data. Teal box = after removing top 0.5%. Dots above whiskers = extreme transactions.")

    with c2:
        if df[COLS["rate"]].notna().sum() > 100:
            st.markdown("#### 📐 Rate / SQM Outliers")
            with st.spinner():
                st.plotly_chart(outlier_boxplot(df, COLS["rate"], "Rate/SQM — Before vs After Outlier Removal", dark=DARK), use_container_width=True, config=PC)
            chart_description("Extreme rates may indicate very small properties, data entry errors, or ultra-premium branded residences.")

    st.markdown("---")
    section_header("Outlier Summary", icon="📋")

    p99 = df[COLS["price"]].quantile(0.99)
    out_count = (df[COLS["price"]] > p99).sum()
    out_pct   = round(out_count / total_records * 100, 2)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Outlier Threshold", format_currency(p99))
    with c2: st.metric("Outlier Transactions", f"{out_count:,}")
    with c3: st.metric("Outlier Share", f"{out_pct}%")
    with c4: st.metric("Max Sale Price",  format_currency(df[COLS["price"]].max()))

    if out_count > 0:
        st.markdown("---")
        st.markdown("#### 🔍 Top Outlier Transactions")
        top_out = (
            df[df[COLS["price"]] > p99]
            [[COLS["district"], COLS["community"], COLS["property_type"], COLS["price"], COLS["rate"], "Year"]]
            .sort_values(COLS["price"], ascending=False)
            .head(20)
        ).copy()
        top_out[COLS["price"]] = top_out[COLS["price"]].apply(lambda x: f"AED {x:,.0f}")
        if COLS["rate"] in top_out.columns:
            top_out[COLS["rate"]] = top_out[COLS["rate"]].apply(lambda x: f"AED {x:,.0f}/SQM" if pd.notna(x) else "N/A")
        st.dataframe(top_out, use_container_width=True, height=340)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 10 — DATA QUALITY
# ─────────────────────────────────────────────────────────────────────────────

with tab_quality:
    section_header("Data Quality Report", "Dataset structure, completeness and column overview", "🔍")

    if IS_APARTMENTS:
        # Apartments view: 3-metric row (no Missing Columns card)
        _qc1, _qc2, _qc3 = st.columns(3)
        with _qc1: st.metric("Total Rows",    f"{len(df_raw):,}")
        with _qc2: st.metric("Total Columns", f"{len(df_raw.columns)}")
        with _qc3: st.metric("Memory Usage", f"{df_raw.memory_usage(deep=True).sum() / 1_048_576:.1f} MB")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Total Rows",    f"{len(df_raw):,}")
        with c2: st.metric("Total Columns", f"{len(df_raw.columns)}")
        with c3: st.metric("Duplicate Rows", f"{df_raw.duplicated().sum():,}")
        with c4: st.metric("Memory Usage", f"{df_raw.memory_usage(deep=True).sum() / 1_048_576:.1f} MB")

    st.markdown("---")
    section_header("Missing Values by Column", icon="❓")
    with st.spinner():
        st.plotly_chart(missing_values_chart(df_raw, dark=DARK), use_container_width=True, config=PC)
    chart_description("Green = &lt;5% missing (acceptable). Amber = 5–20% (review). Red = &gt;20% (high concern).")

    st.markdown("---")
    section_header("Column Quality Details", icon="📋")

    quality_rows = []
    for col in df_raw.columns:
        n_missing  = df_raw[col].isnull().sum()
        pct_missing = round(n_missing / len(df_raw) * 100, 1)
        n_unique   = df_raw[col].nunique()
        dtype      = str(df_raw[col].dtype)

        if pct_missing < 5:
            badge = '<span class="quality-badge excellent">✓ Excellent</span>'
        elif pct_missing < 20:
            badge = '<span class="quality-badge good">⚠ Review</span>'
        else:
            badge = '<span class="quality-badge poor">✗ Concern</span>'

        quality_rows.append({
            "Column": col, "Type": dtype,
            "Non-Null": f"{len(df_raw) - n_missing:,}",
            "Missing": f"{n_missing:,} ({pct_missing}%)",
            "Unique": f"{n_unique:,}",
            "Quality": badge,
        })

    table_rows = "".join(
        f"""<tr>
            <td style="font-weight:600;">{r['Column']}</td>
            <td style="color:#9CA3AF;">{r['Type']}</td>
            <td style="color:#059669;">{r['Non-Null']}</td>
            <td style="color:#DC2626;">{r['Missing']}</td>
            <td>{r['Unique']}</td>
            <td>{r['Quality']}</td>
        </tr>"""
        for r in quality_rows
    )

    st.markdown(
        f"""
        <div style="overflow-x:auto; border:1px solid var(--card-border, #E2E8F0); border-radius:10px; padding:0.5rem;">
        <table class="rank-table" style="width:100%;">
            <thead><tr>
                <th>Column</th><th>Type</th><th>Non-Null</th>
                <th>Missing</th><th>Unique</th><th>Quality</th>
            </tr></thead>
            <tbody>{table_rows}</tbody>
        </table></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    section_header("Data Type Breakdown", icon="📐")

    import plotly.express as _px
    type_counts = df_raw.dtypes.astype(str).value_counts().reset_index()
    type_counts.columns = ["Data Type", "Count"]
    fig_types = _px.bar(
        type_counts, x="Data Type", y="Count",
        color="Data Type", color_discrete_sequence=CHART_COLORS,
        text="Count",
    )
    fig_types.update_layout(**get_plotly_layout(height=280, dark=DARK, show_legend=False))
    fig_types.update_traces(textposition="outside", textfont=dict(size=11))
    st.plotly_chart(fig_types, use_container_width=True, config=PC)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 11 — DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

with tab_download:
    section_header("Download Center", "Export filtered data and summary reports", "⬇️")

    info_box(
        "📦 All exports reflect the <b>current sidebar filter selection</b>. "
        f"Ready to export: <b>{len(df):,} rows</b>."
    )

    export_df = df.copy()
    if COLS["date"] in export_df.columns:
        export_df[COLS["date"]] = export_df[COLS["date"]].astype(str)
    drop_cols = ["YearMonth", "YearQuarter", "Month_Num"]
    export_df = export_df.drop(columns=[c for c in drop_cols if c in export_df.columns])

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 📄 CSV")
        st.markdown(f"**{len(export_df):,}** rows · all columns")
        csv_buf = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv_buf,
            file_name=f"abu_dhabi_re_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    with c2:
        st.markdown("### 📊 Excel")
        st.markdown(f"**{len(export_df):,}** rows · Transactions + Summary sheets")

        @st.cache_data
        def _to_excel(df_export: pd.DataFrame) -> bytes:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Transactions")
                summary = pd.DataFrame({
                    "Metric": ["Total Records", "Total Value (AED)", "Median Price (AED)",
                               "Median Rate/SQM", "Unique Districts", "Unique Communities"],
                    "Value": [
                        len(df_export), df_export[COLS["price"]].sum(),
                        df_export[COLS["price"]].median(),
                        df_export[COLS["rate"]].median() if COLS["rate"] in df_export else "N/A",
                        df_export[COLS["district"]].nunique(),
                        df_export[COLS["community"]].nunique(),
                    ],
                })
                summary.to_excel(writer, index=False, sheet_name="Summary")
            return buf.getvalue()

        st.download_button(
            "⬇️ Download Excel",
            data=_to_excel(export_df),
            file_name=f"abu_dhabi_re_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with c3:
        st.markdown("### 🔢 Summary Stats")
        st.markdown("Key metrics in CSV format")
        summary_df = pd.DataFrame({
            "Metric": ["Total Records", "Total Sales (AED)", "Avg Price (AED)", "Median Price (AED)",
                       "Avg Rate/SQM", "Median Rate/SQM", "Highest Sale", "Lowest Sale",
                       "Districts", "Communities", "Projects"],
            "Value": [total_records, round(total_sales,2), round(avg_price,2), round(median_price,2),
                      round(avg_rate,2) if not np.isnan(avg_rate) else "N/A",
                      round(median_rate,2) if not np.isnan(median_rate) else "N/A",
                      round(max_price,2), round(min_price,2), n_districts, n_communities, n_projects],
        })
        st.download_button(
            "⬇️ Download Summary",
            data=summary_df.to_csv(index=False).encode("utf-8"),
            file_name=f"abu_dhabi_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.markdown(f"#### 👀 Data Preview — first 100 of {len(export_df):,} rows")
    st.dataframe(export_df.head(100), use_container_width=True, height=400)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 12 — ABOUT
# ─────────────────────────────────────────────────────────────────────────────

with tab_about:
    section_header("About This Dashboard", "Dataset, definitions and methodology", "ℹ️")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📦 Dataset Overview")
        st.markdown("""
        Built on the **Abu Dhabi Sales Dataset** — official property transaction records from Abu Dhabi's real estate market.

        | Attribute | Detail |
        |---|---|
        | **Source** | Abu Dhabi DMT |
        | **Coverage** | 2019–2026 |
        | **Records** | 109,097+ transactions |
        | **Update** | As per the cleaned CSV |
        """)

        st.markdown("### 🏗️ Architecture")
        st.code("""
abu dhabi dashboard/
├── app.py              ← Main application
├── config/settings.py  ← Configuration
├── utils/data_loader.py← Data pipeline
├── styles/theme.py     ← Dual-mode CSS
├── components/         ← UI components
├── charts/             ← Plotly charts
└── requirements.txt
        """, language="text")

    with c2:
        st.markdown("### 📖 Column Definitions")
        defs = {
            "Asset Class": "Broad property category (residential, commercial, etc.)",
            "Property Type": "Specific type (apartment, villa, townhouse, etc.)",
            "Sale Application Date": "Date when the sale application was submitted.",
            "Property Sold Area (SQM)": "Usable floor area of the property sold.",
            "Land Plot Ground Area (SQM)": "Total land area of the building / plot.",
            "Property Layout": "Bedroom configuration (studio, 1 bed, 2 bed, etc.)",
            "District": "High-level geographic zone within Abu Dhabi.",
            "Community": "Sub-area / neighbourhood within a district.",
            "Project Name": "Development or building project name.",
            "Property Sale Price (AED)": "Total agreed sale price in UAE Dirhams.",
            "Rate (AED per SQM)": "Price per SQM — key value indicator.",
            "Sale Application Type": "Off-plan or ready at time of sale.",
            "Sale Sequence": "Primary (developer) or secondary (resale) transaction.",
        }
        for col_name, definition in defs.items():
            with st.expander(f"📌 {col_name}"):
                st.caption(definition)

    st.markdown("---")
    st.markdown("### ⚠️ Disclaimers")
    st.info(
        "This dashboard is for **analytical and informational purposes only**. "
        "It does not constitute financial, legal, or investment advice. "
        "Past market trends do not guarantee future performance. "
        "Rows with missing values in Rate or Area columns are excluded from relevant aggregations."
    )


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="footer-container">
        <p class="footer-text">
            🏙️ <strong>Abu Dhabi Real Estate Market Intelligence</strong>
            &nbsp;·&nbsp; Streamlit + Plotly
            &nbsp;·&nbsp; Data: Abu Dhabi DMT
            &nbsp;·&nbsp; v1.0
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
