"""
Global platform configuration.

Single source of truth for:
  - the global st.set_page_config()
  - platform branding
  - the navigation model (routes, regions, Dubai sections, experiments)

The three experiences are deliberately kept apart:

    🇦🇪 Abu Dhabi            the existing, approved dashboard
    🇦🇪 Dubai                the new regional dashboard (regions/dubai_market)
    🧪 Experimental Analysis  the existing version-based work (regions/dubai)
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
REGIONS_DIR = ROOT_DIR / "regions"
DATA_DIR = ROOT_DIR / "data"

ABU_DHABI_DIR = REGIONS_DIR / "abu_dhabi"
ABU_DHABI_ENTRY = ABU_DHABI_DIR / "app.py"

# The existing Dubai experimental application.
EXPERIMENTAL_DIR = REGIONS_DIR / "dubai"
EXPERIMENTAL_ENTRY = EXPERIMENTAL_DIR / "trial.py"

# The new Dubai regional dashboard (a package, not a script).
DUBAI_MARKET_DIR = REGIONS_DIR / "dubai_market"


# ─────────────────────────────────────────────────────────────────────────────
# BRANDING
# ─────────────────────────────────────────────────────────────────────────────

PLATFORM_NAME = "TruEstates"
PLATFORM_NAME_2 = "Analytics"
PLATFORM_TAGLINE = "Regional Property Intelligence"
PLATFORM_VERSION = "1.1.0"
PLATFORM_ICON = "🏙️"

PAGE_CONFIG = dict(
    page_title="TruEstates Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

ROUTE_OVERVIEW = "overview"
ROUTE_ABU_DHABI = "abu_dhabi"
ROUTE_DUBAI = "dubai"
ROUTE_AREA = "area"
ROUTE_EXPERIMENTAL = "experimental"
ROUTE_REPORT = "report"
# Its own destination in the rail, directly under Download Detailed Report.
ROUTE_FORECAST = "forecast"
ROUTE_EXPLORE = "explore"
ROUTE_ABOUT = "about"

DEFAULT_ROUTE = ROUTE_OVERVIEW

# Platform state is namespaced `uae.` so it can never collide with keys used
# inside any of the three environments.
SS_ROUTE = "uae.route"
SS_EXPERIMENT = "uae.experiment"

# The GLOBAL Dubai area. One value, set once in the Area section, read by every
# Dubai analysis. It is namespaced `uae.` like the rest of the platform state so
# it can never collide with a widget key inside a region — in particular it is
# NOT the Dubai sidebar's own `dxb_areas` multiselect, which is a separate,
# pre-existing control and is left alone.
SS_AREA = "uae.area"
ALL_AREAS = "All Areas"
SS_THEME_DARK = "dark_mode"  # shared with the Abu Dhabi dashboard on purpose


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT METADATA
# ─────────────────────────────────────────────────────────────────────────────

REGIONS = {
    ROUTE_ABU_DHABI: {
        "id": ROUTE_ABU_DHABI,
        "name": "Abu Dhabi",
        "flag": "🇦🇪",
        "kicker": "Real Estate Analytics",
        "subtitle": "Transaction intelligence for the Abu Dhabi property market",
        "accent": "#2563EB",
        "accent_soft": "rgba(37, 99, 235, 0.10)",
        "description": (
            "Interactive market dashboard built on official Abu Dhabi transaction records. "
            "Executive KPIs, smart business insights, market snapshot, then trend, geographic, "
            "price, distribution, correlation and data-quality analysis — all filterable live."
        ),
        "highlights": [
            "12 analytical tabs",
            "Live sidebar filtering",
            "Light & dark themes",
            "CSV / Excel export",
        ],
    },
    ROUTE_DUBAI: {
        "id": ROUTE_DUBAI,
        "name": "Dubai",
        "flag": "🇦🇪",
        "kicker": "Real Estate Analytics",
        "subtitle": "Residential transaction intelligence for the Dubai property market",
        "accent": "#0D9488",
        "accent_soft": "rgba(13, 148, 136, 0.10)",
        "description": (
            "The Dubai regional dashboard, structured exactly like Abu Dhabi: Executive KPIs, "
            "Smart Business Insights and Market Snapshot, followed by six analytical sections "
            "covering insights, trends, geography, property, price and distribution."
        ),
        "highlights": [
            "818K+ transactions",
            "69 areas · 2010–2026",
            "Amenity price analysis",
            "Published forecasts",
        ],
    },
    ROUTE_EXPERIMENTAL: {
        "id": ROUTE_EXPERIMENTAL,
        "name": "Experimental Analysis",
        "flag": "🧪",
        "kicker": "Research Environment",
        "subtitle": "Version-based analytical experiments, preserved as originally built",
        "accent": "#7C3AED",
        "accent_soft": "rgba(124, 58, 237, 0.10)",
        "description": (
            "A separate research environment holding the Dubai analytical experiments — six "
            "generations of exploratory work, feature studies, per-area models, forecasting "
            "and area-proxy mapping. Kept intact and apart from the regional dashboards."
        ),
        "highlights": [
            "6 experiment generations",
            "20 area-level ML models",
            "SARIMA & LOWESS forecasts",
            "Original logic preserved",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DUBAI REGIONAL DASHBOARD — section model
# ─────────────────────────────────────────────────────────────────────────────
# These six sections belong exclusively to 🇦🇪 Dubai. They do not appear under
# Experimental Analysis and they are not global.

DUBAI_SUMMARY_BLOCKS = [
    ("📊", "Executive KPIs", "Twelve headline indicators for the current selection"),
    ("💡", "Smart Business Insights", "Automatically derived executive observations"),
    ("📋", "Market Snapshot", "Quick-reference summary statistics"),
]

DUBAI_SECTIONS = [
    ("💡", "Insights", "Market concentration, the biggest developments, quality tiers and yield"),
    ("📈", "Trends", "Monthly, annual, quarterly and seasonal market movement"),
    ("🗺️", "Geography", "Busiest and most expensive areas, value map, zones and metro"),
    ("🏠", "Property", "Layout mix, unit sizes, off-plan vs existing, size against price"),
    ("💵", "Price", "Price movement, amenities vs price, price bands and published forecasts"),
    ("📊", "Distribution", "How price, rate and size are spread, and how that has changed"),
]


# ─────────────────────────────────────────────────────────────────────────────
# EXPERIMENTAL ANALYSIS — experiment model
# ─────────────────────────────────────────────────────────────────────────────
# `legacy` MUST match the branch strings inside regions/dubai/trial.py exactly —
# it is the value handed back to that untouched branching logic.
#
# Labels and descriptions are presentation only and were written from the code.
# No project history is invented.

EXPERIMENTS = [
    {
        "id": "v1",
        "legacy": "V1",
        "label": "V1 · Market Data Explorer",
        "short": "V1",
        "icon": "📊",
        "blurb": "First-generation exploration of the full transaction base.",
        "detail": (
            "The original exploratory pass over the Dubai registry: Pareto (ABC) concentration "
            "analysis, univariate and bivariate distribution studies, a geographical view and "
            "the first price-prediction model results."
        ),
        "views": ["Pareto Analysis", "Univariate Analysis", "Bivariate Analysis",
                  "Geo Graphical Analysis", "Price Prediction Model"],
    },
    {
        "id": "v2",
        "legacy": "V2",
        "label": "V2 · Refined Market Analysis",
        "short": "V2",
        "icon": "🔎",
        "blurb": "Second generation on the combined micro dataset.",
        "detail": (
            "Repeats the exploratory programme on the cleaned / combined micro dataset and "
            "adds a correlation and feature-dropping study, plus the refined price-prediction "
            "model performance."
        ),
        "views": ["Univariate Analysis", "Bivariate Analysis", "Correlation",
                  "Price Prediction Model"],
    },
    {
        "id": "v21",
        "legacy": "V2.1",
        "label": "V2.1 · Modelling & Prediction Lab",
        "short": "V2.1",
        "icon": "🤖",
        "blurb": "The full modelling pipeline, end to end.",
        "detail": (
            "Data understanding, EDA and feature engineering, then per-area model results "
            "driven by 20 saved decision-tree models — metrics, feature importance, "
            "actual-vs-predicted and area comparison — followed by a validation view."
        ),
        "views": ["📂 Data Understanding", "📊 EDA & Feature Engineering", "📈 Model Results",
                  "validation", "🤖 Model Input / Prediction"],
    },
    {
        "id": "fc",
        "legacy": "FC",
        "label": "FC · Forecasting",
        "short": "FC",
        "icon": "📈",
        "blurb": "Auto-ARIMA / SARIMA forecasting with LOWESS smoothing.",
        "detail": (
            "Area-level rate forecasts. Compares the LOWESS-smoothed actual series with the "
            "model's fitted and forward path, alongside accuracy metrics and the full SARIMA "
            "model summary. A second tab keeps the earlier forecasting models."
        ),
        "views": ["Auto Arima with Lowess", "Previous models"],
    },
    {
        "id": "area_combination",
        "legacy": "area_combination",
        "label": "Area Combination",
        "short": "Areas",
        "icon": "📍",
        "blurb": "How individual areas were grouped into modelling proxies.",
        "detail": (
            "A bubble map showing the area groupings used by the models, across eight proxy "
            "definitions (original, revised, 2021 and modified variants). This is the "
            "geographic reasoning behind the per-area models."
        ),
        "views": ["8 proxy datasets"],
    },
    {
        "id": "v22",
        "legacy": "V_2.2",
        "label": "V2.2 · Price Predictor",
        "short": "V2.2",
        "icon": "🔮",
        "blurb": "Link to the separately deployed price-prediction application.",
        "detail": (
            "This generation is a pointer to the standalone FlipOse price-prediction app "
            "rather than an embedded model."
        ),
        "views": ["External application"],
    },
]

# The Trend Smoothing comparison was removed from the rail by request. The
# six original generations are untouched; `metrics.smoothing_experiment()`
# and its chart remain in the codebase but are no longer reachable from the
# interface.
EXPERIMENT_BY_ID = {e["id"]: e for e in EXPERIMENTS}
DEFAULT_EXPERIMENT = EXPERIMENTS[0]["id"]

# Removed from the Experimental Analysis user interface by request.
# The underlying code in regions/dubai/trial.py is left in place and is simply
# no longer reachable from the UI — see docs/INTEGRATION_CHANGES.md (DXB-5).
EXPERIMENT_HIDDEN_VIEWS = ("Data Summary",)


# ─────────────────────────────────────────────────────────────────────────────
# ABU DHABI — descriptive only (the region owns its own tabs)
# ─────────────────────────────────────────────────────────────────────────────

ABU_DHABI_TABS = [
    ("💡", "Insights", "Auto-generated business insights from the filtered data"),
    ("📈", "Trends", "Monthly, annual and quarterly transaction dynamics"),
    ("🗺️", "Geographic", "District treemap, community rankings, volume vs price"),
    ("🏠", "Property", "Type mix, layouts, off-plan vs ready, primary vs secondary"),
    ("💵", "Price", "Price and rate/SQM trends, distributions and area-price scatter"),
    ("📊", "Distribution", "Violin, density and statistical distribution profiling"),
    ("🕐", "Time Series", "Seasonality and year-over-year growth"),
    ("🔗", "Correlations", "Correlation matrix with plain-English interpretation"),
    ("⚠️", "Outliers", "Extreme-value detection and top outlier transactions"),
    ("🔍", "Data Quality", "Completeness, dtypes and per-column quality grading"),
    ("⬇️", "Download", "Export the filtered dataset as CSV or Excel"),
    ("ℹ️", "About", "Dataset provenance, column definitions and disclaimers"),
]
