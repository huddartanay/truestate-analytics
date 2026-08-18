"""
Shared chart theme for platform-authored charts.

The Abu Dhabi dashboard already defines a Plotly layout and palette in
`regions/abu_dhabi/styles/theme.py`. That file is protected and is NOT imported
from here (its package names — `config`, `styles`, `utils` — are generic enough
to shadow other modules when placed on `sys.path`).

Instead the same values are restated here so anything the platform draws — the
Dubai regional dashboard in particular — is visually identical to Abu Dhabi.
If the Abu Dhabi palette ever changes, mirror the change here.
"""

from __future__ import annotations

# Identical to regions/abu_dhabi/styles/theme.py :: CHART_COLORS
CHART_COLORS = [
    "#2563EB",  # Blue-600 (primary)
    "#0D9488",  # Teal-600 (secondary)
    "#D97706",  # Amber-600
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

PRIMARY = CHART_COLORS[0]
SECONDARY = CHART_COLORS[1]
AMBER = CHART_COLORS[2]
VIOLET = CHART_COLORS[3]
RED = CHART_COLORS[4]
GREEN = CHART_COLORS[5]

SEQUENTIAL = ["#EFF6FF", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6", "#2563EB", "#1D4ED8", "#1E3A8A"]

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "dubai_real_estate_chart",
        "height": 600,
        "width": 1200,
        "scale": 2,
    },
}


def layout(title: str = "", height: int = 420, show_legend: bool = True,
           dark: bool = False, hovermode: str = "x unified") -> dict:
    """Standard Plotly layout — mirrors the Abu Dhabi helper."""
    if dark:
        font_color = "#CBD5E1"
        grid_color = "rgba(255,255,255,0.06)"
        zero_color = "rgba(255,255,255,0.12)"
        legend_bg = "rgba(30,41,59,0.8)"
        legend_border = "rgba(255,255,255,0.08)"
        hover_bg = "rgba(15,23,42,0.96)"
        hover_border = "rgba(37,99,235,0.7)"
        title_color = "#F1F5F9"
    else:
        font_color = "#374151"
        grid_color = "rgba(0,0,0,0.06)"
        zero_color = "rgba(0,0,0,0.15)"
        legend_bg = "rgba(255,255,255,0.95)"
        legend_border = "rgba(0,0,0,0.08)"
        hover_bg = "rgba(255,255,255,0.98)"
        hover_border = "rgba(37,99,235,0.5)"
        title_color = "#111827"

    return {
        "height": height,
        "title": {
            "text": title,
            "font": {"size": 15, "color": title_color, "family": "Inter, sans-serif"},
            "x": 0.01, "xanchor": "left", "pad": {"t": 4, "b": 8},
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": font_color, "family": "Inter, sans-serif", "size": 12},
        "legend": (
            {"bgcolor": legend_bg, "bordercolor": legend_border, "borderwidth": 1,
             "font": {"size": 11, "color": font_color}, "orientation": "v"}
            if show_legend else {"visible": False}
        ),
        "xaxis": {
            "gridcolor": grid_color, "zerolinecolor": zero_color,
            "tickfont": {"size": 11, "color": font_color},
            "title_font": {"size": 12, "color": font_color},
            "showline": True, "linecolor": grid_color, "linewidth": 1,
        },
        "yaxis": {
            "gridcolor": grid_color, "zerolinecolor": zero_color,
            "tickfont": {"size": 11, "color": font_color},
            "title_font": {"size": 12, "color": font_color},
            "showline": False,
        },
        "margin": {"l": 55, "r": 25, "t": 55, "b": 45},
        "hovermode": hovermode,
        "hoverlabel": {
            "bgcolor": hover_bg, "bordercolor": hover_border,
            "font": {"size": 12, "color": title_color, "family": "Inter, sans-serif"},
            "namelength": -1,
        },
        "separators": ".,",
    }
