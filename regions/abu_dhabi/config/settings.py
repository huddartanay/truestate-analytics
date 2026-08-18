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
