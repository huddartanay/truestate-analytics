"""
Premium Dual-Mode Theme System
Light (default) and Dark mode with consistent color palette.
Abu Dhabi Real Estate Market Intelligence Dashboard.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CHART COLOR PALETTE  (consistent across both themes)
# ─────────────────────────────────────────────────────────────────────────────

CHART_COLORS = [
    "#2563EB",  # Blue-600      (primary)
    "#0D9488",  # Teal-600      (secondary)
    "#D97706",  # Amber-600     (warning)
    "#7C3AED",  # Violet-600
    "#DC2626",  # Red-600
    "#059669",  # Emerald-600
    "#DB2777",  # Pink-600
    "#0891B2",  # Cyan-600
    "#65A30D",  # Lime-600
    "#9333EA",  # Purple-600
    "#EA580C",  # Orange-600
    "#0284C7",  # Sky-600
    "#16A34A",  # Green-600
    "#CA8A04",  # Yellow-600
    "#E11D48",  # Rose-600
    "#6366F1",  # Indigo-500
]

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_plotly_layout(
    title: str = "",
    height: int = 420,
    show_legend: bool = True,
    dark: bool = False,
) -> dict:
    """Return standard Plotly layout dict adjusted for light or dark mode."""

    if dark:
        paper_bg    = "rgba(15,23,42,0)"
        plot_bg     = "rgba(15,23,42,0)"
        font_color  = "#CBD5E1"
        grid_color  = "rgba(255,255,255,0.06)"
        zero_color  = "rgba(255,255,255,0.12)"
        legend_bg   = "rgba(30,41,59,0.8)"
        legend_border = "rgba(255,255,255,0.08)"
        hover_bg    = "rgba(15,23,42,0.96)"
        hover_border = "rgba(37,99,235,0.7)"
        title_color  = "#F1F5F9"
    else:
        paper_bg    = "rgba(0,0,0,0)"
        plot_bg     = "rgba(0,0,0,0)"
        font_color  = "#374151"
        grid_color  = "rgba(0,0,0,0.06)"
        zero_color  = "rgba(0,0,0,0.15)"
        legend_bg   = "rgba(255,255,255,0.95)"
        legend_border = "rgba(0,0,0,0.08)"
        hover_bg    = "rgba(255,255,255,0.98)"
        hover_border = "rgba(37,99,235,0.5)"
        title_color  = "#111827"

    return {
        "height": height,
        "title": {
            "text": title,
            "font": {"size": 15, "color": title_color, "family": "Inter, sans-serif"},
            "x": 0.01,
            "xanchor": "left",
            "pad": {"t": 4, "b": 8},
        },
        "paper_bgcolor": paper_bg,
        "plot_bgcolor":  plot_bg,
        "font": {"color": font_color, "family": "Inter, sans-serif", "size": 12},
        "legend": {
            "bgcolor": legend_bg,
            "bordercolor": legend_border,
            "borderwidth": 1,
            "font": {"size": 11, "color": font_color},
            "orientation": "v",
        } if show_legend else {"visible": False},
        "xaxis": {
            "gridcolor": grid_color,
            "zerolinecolor": zero_color,
            "tickfont": {"size": 11, "color": font_color},
            "title_font": {"size": 12, "color": font_color},
            "showline": True,
            "linecolor": grid_color,
            "linewidth": 1,
        },
        "yaxis": {
            "gridcolor": grid_color,
            "zerolinecolor": zero_color,
            "tickfont": {"size": 11, "color": font_color},
            "title_font": {"size": 12, "color": font_color},
            "showline": False,
        },
        "margin": {"l": 55, "r": 25, "t": 55, "b": 45},
        "hovermode": "x unified",
        "hoverlabel": {
            "bgcolor": hover_bg,
            "bordercolor": hover_border,
            "font": {"size": 12, "color": title_color, "family": "Inter, sans-serif"},
            "namelength": -1,
        },
        "separators": ".,",
    }


# ─────────────────────────────────────────────────────────────────────────────
# CSS GENERATOR  (called at runtime so theme toggle works)
# ─────────────────────────────────────────────────────────────────────────────

def build_css(dark: bool = False) -> str:
    """Return the full CSS string for the chosen theme."""

    if dark:
        # ── Dark palette ──────────────────────────────────────────────────────
        app_bg          = "#0F172A"
        sidebar_bg      = "#0F172A"
        sidebar_border  = "rgba(37,99,235,0.18)"
        card_bg         = "#1E293B"
        card_border     = "#334155"
        card_shadow     = "0 1px 4px rgba(0,0,0,0.5), 0 4px 16px rgba(0,0,0,0.3)"
        card_hover_shadow = "0 4px 24px rgba(37,99,235,0.25), 0 1px 6px rgba(0,0,0,0.5)"
        text_primary    = "#F1F5F9"
        text_secondary  = "#94A3B8"
        text_muted      = "#64748B"
        accent          = "#3B82F6"   # blue-500
        accent_hover    = "#2563EB"
        accent_light    = "rgba(59,130,246,0.12)"
        accent_border   = "rgba(59,130,246,0.35)"
        teal            = "#14B8A6"
        teal_light      = "rgba(20,184,166,0.12)"
        success_light   = "rgba(16,185,129,0.12)"
        success_color   = "#10B981"
        warning_light   = "rgba(245,158,11,0.12)"
        warning_color   = "#F59E0B"
        section_border  = "rgba(51,65,85,0.8)"
        input_bg        = "#1E293B"
        input_border    = "#334155"
        tab_active_bg   = "rgba(59,130,246,0.18)"
        tab_active_color = "#60A5FA"
        divider         = "rgba(51,65,85,0.6)"
        badge_bg        = "rgba(59,130,246,0.15)"
        badge_border    = "rgba(59,130,246,0.35)"
        badge_color     = "#93C5FD"
        hero_bg         = "linear-gradient(135deg, #1E293B 0%, #0F172A 100%)"
        hero_border     = "rgba(59,130,246,0.2)"
        metric_bg       = "#1E293B"
        metric_border   = "#334155"
        insight_bg      = "rgba(59,130,246,0.06)"
        insight_border  = "rgba(59,130,246,0.2)"
        table_stripe    = "rgba(255,255,255,0.03)"
        scrollbar_track = "rgba(255,255,255,0.03)"
        scrollbar_thumb = "rgba(59,130,246,0.4)"
        kpi_label_color = "#64748B"
        kpi_val_color   = "#F1F5F9"
        sidebar_label   = "#CBD5E1"
        expander_bg     = "#1E293B"
        quality_excellent_bg = "rgba(16,185,129,0.12)"
        quality_excellent_color = "#34D399"
        quality_good_bg = "rgba(245,158,11,0.12)"
        quality_good_color = "#FCD34D"
        quality_poor_bg = "rgba(239,68,68,0.12)"
        quality_poor_color = "#F87171"
        footer_color    = "#475569"
        section_icon_bg = "rgba(59,130,246,0.15)"
    else:
        # ── Light palette ─────────────────────────────────────────────────────
        app_bg          = "#F8FAFC"
        sidebar_bg      = "#FFFFFF"
        sidebar_border  = "rgba(37,99,235,0.12)"
        card_bg         = "#FFFFFF"
        card_border     = "#E2E8F0"
        card_shadow     = "0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)"
        card_hover_shadow = "0 4px 20px rgba(37,99,235,0.15), 0 1px 4px rgba(0,0,0,0.08)"
        text_primary    = "#111827"
        text_secondary  = "#4B5563"
        text_muted      = "#9CA3AF"
        accent          = "#2563EB"   # blue-600
        accent_hover    = "#1D4ED8"
        accent_light    = "#EFF6FF"
        accent_border   = "#BFDBFE"
        teal            = "#0D9488"
        teal_light      = "#F0FDFA"
        success_light   = "#ECFDF5"
        success_color   = "#059669"
        warning_light   = "#FFFBEB"
        warning_color   = "#D97706"
        section_border  = "#E5E7EB"
        input_bg        = "#FFFFFF"
        input_border    = "#D1D5DB"
        tab_active_bg   = "#EFF6FF"
        tab_active_color = "#1D4ED8"
        divider         = "#E5E7EB"
        badge_bg        = "#EFF6FF"
        badge_border    = "#BFDBFE"
        badge_color     = "#1E40AF"
        hero_bg         = "linear-gradient(135deg, #EFF6FF 0%, #F0FDFA 100%)"
        hero_border     = "#BFDBFE"
        metric_bg       = "#FFFFFF"
        metric_border   = "#E2E8F0"
        insight_bg      = "#EFF6FF"
        insight_border  = "#BFDBFE"
        table_stripe    = "#F8FAFC"
        scrollbar_track = "#F1F5F9"
        scrollbar_thumb = "#CBD5E1"
        kpi_label_color = "#6B7280"
        kpi_val_color   = "#111827"
        sidebar_label   = "#374151"
        expander_bg     = "#F8FAFC"
        quality_excellent_bg = "#ECFDF5"
        quality_excellent_color = "#059669"
        quality_good_bg = "#FFFBEB"
        quality_good_color = "#D97706"
        quality_poor_bg = "#FEF2F2"
        quality_poor_color = "#DC2626"
        footer_color    = "#9CA3AF"
        section_icon_bg = "#EFF6FF"

    return f"""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   GOOGLE FONTS
═══════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   GLOBAL RESET & BASE
═══════════════════════════════════════════════════════════════════════════ */
*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

/* ── App background ── */
.stApp {{
    background-color: {app_bg} !important;
    transition: background-color 0.3s ease;
}}

.main .block-container {{
    padding: 1.5rem 2rem 3rem 2rem !important;
    max-width: 1500px !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {sidebar_bg} !important;
    border-right: 1px solid {sidebar_border} !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.05) !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1rem;
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {{
    color: {text_primary} !important;
    font-weight: 600 !important;
}}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{
    color: {sidebar_label} !important;
    font-size: 0.82rem !important;
}}

/* Sidebar inputs */
[data-testid="stSidebar"] .stMultiSelect > div > div,
[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: {input_bg} !important;
    border: 1px solid {input_border} !important;
    border-radius: 8px !important;
    color: {text_primary} !important;
    font-size: 0.82rem !important;
}}

[data-testid="stSidebar"] .stMultiSelect > div > div:focus-within,
[data-testid="stSidebar"] .stSelectbox > div > div:focus-within {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px {accent_light} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════════════════════════════════════════ */
h1, h2, h3, h4, h5, h6 {{
    color: {text_primary} !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}}

p, li, span {{
    color: {text_secondary};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   HERO SECTION
═══════════════════════════════════════════════════════════════════════════ */
.hero-container {{
    background: {hero_bg};
    border: 1px solid {hero_border};
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
}}

.hero-container::after {{
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 300px;
    height: 100%;
    background: url("data:image/svg+xml,%3Csvg width='300' height='200' viewBox='0 0 300 200' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='250' cy='50' r='120' fill='%232563EB' fill-opacity='0.05'/%3E%3Ccircle cx='200' cy='160' r='80' fill='%230D9488' fill-opacity='0.05'/%3E%3C/svg%3E") no-repeat right center;
    pointer-events: none;
}}

.hero-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {badge_bg};
    border: 1px solid {badge_border};
    border-radius: 50px;
    padding: 4px 12px;
    font-size: 0.72rem;
    font-weight: 600;
    color: {badge_color} !important;
    margin-bottom: 0.85rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}

.hero-title {{
    font-size: 2.1rem;
    font-weight: 800;
    color: {text_primary} !important;
    line-height: 1.2;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.02em;
}}

.hero-title span {{
    color: {accent} !important;
}}

.hero-subtitle {{
    font-size: 0.95rem;
    color: {text_secondary} !important;
    margin-bottom: 1.5rem;
    max-width: 640px;
    line-height: 1.6;
}}

.hero-stats {{
    display: flex;
    gap: 2.5rem;
    flex-wrap: wrap;
    padding-top: 1rem;
    border-top: 1px solid {divider};
    margin-top: 0.5rem;
}}

.hero-stat-value {{
    font-size: 1.5rem;
    font-weight: 800;
    color: {text_primary} !important;
    line-height: 1;
}}

.hero-stat-label {{
    font-size: 0.72rem;
    color: {text_muted} !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 3px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   KPI CARDS
═══════════════════════════════════════════════════════════════════════════ */
.kpi-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
    padding: 1.2rem 1.3rem;
    position: relative;
    overflow: hidden;
    box-shadow: {card_shadow};
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: default;
    height: 100%;
    min-height: 130px;
}}

.kpi-card:hover {{
    transform: translateY(-3px);
    box-shadow: {card_hover_shadow};
    border-color: {accent_border};
}}

.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}}

/* Colour accent variants */
.kpi-card.blue::before   {{ background: linear-gradient(90deg, #2563EB, #60A5FA); }}
.kpi-card.teal::before   {{ background: linear-gradient(90deg, #0D9488, #2DD4BF); }}
.kpi-card.amber::before  {{ background: linear-gradient(90deg, #D97706, #FCD34D); }}
.kpi-card.green::before  {{ background: linear-gradient(90deg, #059669, #34D399); }}
.kpi-card.violet::before {{ background: linear-gradient(90deg, #7C3AED, #A78BFA); }}
.kpi-card.rose::before   {{ background: linear-gradient(90deg, #E11D48, #FB7185); }}
.kpi-card.sky::before    {{ background: linear-gradient(90deg, #0284C7, #38BDF8); }}

.kpi-icon-box {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: {accent_light};
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    margin-bottom: 0.9rem;
    flex-shrink: 0;
}}

.kpi-card.blue   .kpi-icon-box {{ background: {accent_light}; }}
.kpi-card.teal   .kpi-icon-box {{ background: {teal_light}; }}
.kpi-card.amber  .kpi-icon-box {{ background: {warning_light}; }}
.kpi-card.green  .kpi-icon-box {{ background: {success_light}; }}
.kpi-card.violet .kpi-icon-box {{ background: rgba(124,58,237,0.10); }}
.kpi-card.rose   .kpi-icon-box {{ background: rgba(225,29,72,0.09); }}
.kpi-card.sky    .kpi-icon-box {{ background: rgba(2,132,199,0.09); }}

.kpi-label {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {kpi_label_color} !important;
    margin-bottom: 0.3rem;
}}

.kpi-value {{
    font-size: 1.55rem;
    font-weight: 800;
    color: {kpi_val_color} !important;
    line-height: 1.1;
    margin-bottom: 0.35rem;
    letter-spacing: -0.01em;
}}

.kpi-delta {{
    font-size: 0.74rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 3px;
}}

.kpi-delta.positive {{ color: #059669 !important; }}
.kpi-delta.negative {{ color: #DC2626 !important; }}
.kpi-delta.neutral  {{ color: {text_muted} !important; }}

/* ═══════════════════════════════════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════════════════════════════════ */
.section-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1.25rem;
    padding-bottom: 0.85rem;
    border-bottom: 2px solid {section_border};
}}

.section-icon {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: {section_icon_bg};
    border: 1px solid {accent_border};
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    flex-shrink: 0;
}}

.section-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {text_primary} !important;
    margin: 0;
    letter-spacing: -0.01em;
}}

.section-subtitle {{
    font-size: 0.78rem;
    color: {text_muted} !important;
    margin: 0;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INSIGHT CARDS
═══════════════════════════════════════════════════════════════════════════ */
.insight-card {{
    background: {insight_bg};
    border: 1px solid {insight_border};
    border-radius: 10px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.65rem;
    transition: border-color 0.2s ease, transform 0.15s ease;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}}

.insight-card:hover {{
    border-color: {accent};
    transform: translateX(3px);
}}

.insight-emoji {{ font-size: 1.3rem; flex-shrink: 0; margin-top: 1px; }}

.insight-text {{
    font-size: 0.87rem;
    color: {text_secondary} !important;
    line-height: 1.65;
    margin: 0;
}}

.insight-highlight {{
    color: {accent} !important;
    font-weight: 700;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   CHART CARD WRAPPER
═══════════════════════════════════════════════════════════════════════════ */
.chart-card {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
    padding: 1rem 1.2rem 0.8rem 1.2rem;
    box-shadow: {card_shadow};
    margin-bottom: 1rem;
    transition: box-shadow 0.2s ease;
}}

.chart-card:hover {{
    box-shadow: {card_hover_shadow};
}}

.chart-description {{
    font-size: 0.8rem;
    color: {text_muted} !important;
    padding: 0.5rem 0.75rem;
    margin-top: 0.5rem;
    background: {accent_light};
    border-radius: 6px;
    border-left: 3px solid {accent};
    line-height: 1.55;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {card_bg};
    border-radius: 10px;
    padding: 5px;
    border: 1px solid {card_border};
    box-shadow: {card_shadow};
    flex-wrap: wrap;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 0.81rem;
    font-weight: 500;
    color: {text_secondary};
    background: transparent;
    transition: all 0.18s ease;
    border: 1px solid transparent;
    white-space: nowrap;
}}

.stTabs [data-baseweb="tab"]:hover {{
    background: {accent_light};
    color: {accent} !important;
}}

.stTabs [aria-selected="true"] {{
    background: {tab_active_bg} !important;
    color: {tab_active_color} !important;
    font-weight: 600 !important;
    border: 1px solid {accent_border} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   EXPANDER
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    background: {expander_bg};
    border: 1px solid {card_border};
    border-radius: 10px;
    overflow: hidden;
}}

[data-testid="stExpander"] summary {{
    color: {text_primary} !important;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.75rem 1rem;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════════════════════════════════════ */
.stDownloadButton > button,
.stButton > button {{
    background: {accent} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.1rem !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.3) !important;
    letter-spacing: 0.01em;
}}

.stDownloadButton > button:hover,
.stButton > button:hover {{
    background: {accent_hover} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
}}

/* Reset button special style */
.reset-btn > button {{
    background: {card_bg} !important;
    color: {accent} !important;
    border: 1px solid {accent_border} !important;
    box-shadow: none !important;
}}

.reset-btn > button:hover {{
    background: {accent_light} !important;
    box-shadow: none !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SELECTBOX / MULTISELECT / SLIDER
═══════════════════════════════════════════════════════════════════════════ */
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    background: {input_bg} !important;
    border: 1px solid {input_border} !important;
    border-radius: 8px !important;
    color: {text_primary} !important;
    font-size: 0.85rem !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
}}

.stSelectbox > div > div:focus-within,
.stMultiSelect > div > div:focus-within {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px {accent_light} !important;
}}

/* Slider track */
[data-testid="stSlider"] > div > div > div {{
    background: {accent} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   METRIC (st.metric)
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {{
    background: {metric_bg};
    border: 1px solid {metric_border};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: {card_shadow};
}}

[data-testid="stMetric"] label {{
    color: {text_muted} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600 !important;
}}

[data-testid="stMetricValue"] {{
    color: {text_primary} !important;
    font-weight: 800 !important;
    font-size: 1.4rem !important;
}}

[data-testid="stMetricDelta"] {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   DATAFRAME / TABLE
═══════════════════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid {card_border};
    box-shadow: {card_shadow};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   INFO BOX
═══════════════════════════════════════════════════════════════════════════ */
.info-box {{
    background: {accent_light};
    border: 1px solid {accent_border};
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin: 0.6rem 0;
}}

.info-box p {{
    color: {text_secondary} !important;
    font-size: 0.85rem;
    margin: 0;
    line-height: 1.6;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR LOGO BLOCK
═══════════════════════════════════════════════════════════════════════════ */
.sidebar-logo {{
    background: {accent_light};
    border: 1px solid {accent_border};
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 1.25rem;
    text-align: center;
}}

.sidebar-logo-title {{
    font-size: 0.9rem;
    font-weight: 700;
    color: {text_primary} !important;
    margin: 4px 0 2px 0;
    line-height: 1.3;
}}

.sidebar-logo-sub {{
    font-size: 0.7rem;
    color: {text_muted} !important;
    margin: 0;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR FILTER LABEL
═══════════════════════════════════════════════════════════════════════════ */
.filter-header {{
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {accent} !important;
    margin: 1rem 0 0.35rem 0;
    display: flex;
    align-items: center;
    gap: 5px;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   RANK TABLE
═══════════════════════════════════════════════════════════════════════════ */
.rank-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
}}

.rank-table th {{
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: {text_muted} !important;
    padding: 0.45rem 0.7rem;
    border-bottom: 2px solid {divider};
    text-align: left;
    white-space: nowrap;
}}

.rank-table td {{
    color: {text_secondary} !important;
    padding: 0.5rem 0.7rem;
    border-bottom: 1px solid {divider};
    vertical-align: middle;
}}

.rank-table tr:last-child td {{ border-bottom: none; }}
.rank-table tr:nth-child(even) td {{ background: {table_stripe}; }}
.rank-table tr:hover td {{ background: {accent_light}; }}

.rank-number {{ font-weight: 800; color: {accent} !important; }}

/* ═══════════════════════════════════════════════════════════════════════════
   QUALITY BADGES
═══════════════════════════════════════════════════════════════════════════ */
.quality-badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 50px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}}

.quality-badge.excellent {{
    background: {quality_excellent_bg};
    color: {quality_excellent_color};
    border: 1px solid rgba(5,150,105,0.25);
}}

.quality-badge.good {{
    background: {quality_good_bg};
    color: {quality_good_color};
    border: 1px solid rgba(217,119,6,0.25);
}}

.quality-badge.poor {{
    background: {quality_poor_bg};
    color: {quality_poor_color};
    border: 1px solid rgba(220,38,38,0.25);
}}

/* ═══════════════════════════════════════════════════════════════════════════
   DIVIDER
═══════════════════════════════════════════════════════════════════════════ */
hr {{
    border: none;
    border-top: 1px solid {divider};
    margin: 1.4rem 0;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   FOOTER
═══════════════════════════════════════════════════════════════════════════ */
.footer-container {{
    text-align: center;
    padding: 1.5rem;
    margin-top: 2.5rem;
    border-top: 1px solid {divider};
}}

.footer-text {{
    font-size: 0.76rem;
    color: {footer_color} !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {scrollbar_track}; }}
::-webkit-scrollbar-thumb {{ background: {scrollbar_thumb}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {accent}; }}

/* ═══════════════════════════════════════════════════════════════════════════
   SPINNER
═══════════════════════════════════════════════════════════════════════════ */
.stSpinner > div {{ border-top-color: {accent} !important; }}

/* ═══════════════════════════════════════════════════════════════════════════
   HIDE DEFAULT STREAMLIT CHROME
═══════════════════════════════════════════════════════════════════════════ */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header {{ visibility: hidden; }}

/* ═══════════════════════════════════════════════════════════════════════════
   THEME TOGGLE BUTTON
═══════════════════════════════════════════════════════════════════════════ */
.theme-toggle-btn > button {{
    background: {card_bg} !important;
    color: {text_primary} !important;
    border: 1px solid {card_border} !important;
    border-radius: 8px !important;
    padding: 0.35rem 0.8rem !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    box-shadow: {card_shadow} !important;
    transition: all 0.18s ease !important;
}}

.theme-toggle-btn > button:hover {{
    border-color: {accent} !important;
    color: {accent} !important;
    background: {accent_light} !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* ═══════════════════════════════════════════════════════════════════════════
   STATS PILL (hero area)
═══════════════════════════════════════════════════════════════════════════ */
.stat-pill {{
    background: {card_bg};
    border: 1px solid {card_border};
    border-radius: 8px;
    padding: 0.5rem 1rem;
    display: inline-block;
    box-shadow: {card_shadow};
}}

/* ═══════════════════════════════════════════════════════════════════════════
   SUBHEADER OVERRIDES
═══════════════════════════════════════════════════════════════════════════ */
.stMarkdown h3,
.stMarkdown h2 {{
    color: {text_primary} !important;
    font-weight: 700 !important;
    margin-top: 0.5rem !important;
}}
</style>
"""


# Alias for backwards compatibility — app.py still calls MAIN_CSS
# We generate in light mode by default; the app will regenerate on toggle
MAIN_CSS = build_css(dark=False)
