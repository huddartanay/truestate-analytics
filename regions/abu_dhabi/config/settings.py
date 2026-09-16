"""
Abu Dhabi Real Estate Market Dashboard
Configuration file
"""

# App Configuration
APP_TITLE = "Abu Dhabi Real Estate Market Intelligence"
APP_SUBTITLE = "Enterprise Analytics Dashboard"
APP_ICON = "🏙️"
APP_VERSION = "1.0.0"

# Data Configuration
DATA_FILE = "Abu_Dhabi_Sales_Cleaned (1).csv"
PARQUET_FILE = "Abu_Dhabi_Sales_Optimized.parquet"

# Column Mappings
COLS = {
    "date": "Sale Application Date",
    "price": "Property Sale Price (AED)",
    "area_sqm": "Property Sold Area (SQM)",
    "rate": "Rate (AED per SQM)",
    "property_type": "Property Type",
    "asset_class": "Asset Class",
    "layout": "Property Layout",
    "district": "District",
    "community": "Community",
    "project": "Project Name",
    "sale_type": "Sale Application Type",
    "sale_sequence": "Sale Sequence",
    "year": "Year",
    "month": "Month",
    "quarter": "Quarter",
    "land_area": "Land Plot Ground Area (SQM)",
    "sold_share": "Property Sold Share",
}

# The prepared Parquet keeps the same raw/export columns and the same derived
# feature columns produced by the original loader.  Keeping this contract
# explicit lets the runtime loader fail safely if an incomplete artifact is
# ever deployed.
RAW_COLUMNS = (
    "Asset Class", "Property Type", "Sale Application Date",
    "Property Sold Area (SQM)", "Land Plot Ground Area (SQM)",
    "Property Layout", "District", "Community", "Project Name",
    "Property Sale Price (AED)", "Property Sold Share", "Rate (AED per SQM)",
    "Sale Application Type", "Sale Sequence", "Year", "Month", "Quarter",
)
PREPARED_COLUMNS = RAW_COLUMNS + ("Month_Num", "YearMonth", "YearQuarter")

# Premium Color Palette
COLORS = {
    "primary": "#6C63FF",
    "secondary": "#00D4AA",
    "accent": "#FF6B6B",
    "gold": "#FFD700",
    "dark_bg": "#0A0E1A",
    "card_bg": "rgba(255,255,255,0.05)",
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0AEC0",
    "gradient_start": "#6C63FF",
    "gradient_end": "#00D4AA",
}

# Chart Configuration
CHART_HEIGHT = 450
MAP_HEIGHT = 550
PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "abu_dhabi_real_estate_chart",
        "height": 600,
        "width": 1200,
        "scale": 2,
    },
}
