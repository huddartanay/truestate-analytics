"""
RAK source-of-truth registry.

Every value on the RAK dashboard and every value inside the RAK PDF report is
defined here — nowhere else. Every item carries the source report and period
it came from. Nothing is inferred from Dubai, Sharjah or any other emirate.

Reports the values come from (and nothing else):

    RAK_ANNUAL_2025    Real Estate Report on Lands and Properties Sector
                       Transactions 2024–2025  (r4.pdf)
    RAK_ANNUAL_2021    Real Estate Report on Lands and Properties Sector
                       Transactions 2020–2021  (r2.pdf)
    RAK_MONTHLY_JAN26  Real Estate Trading Report — January 2025–2026  (r1.pdf)

All three are published by the RAK Statistics Office / Lands and Properties
Sector.
"""

from __future__ import annotations


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE HANDLES
# ─────────────────────────────────────────────────────────────────────────────

RAK_ANNUAL_2025 = {
    "id": "rak_annual_2025",
    "publisher": "RAK Statistics Office — Lands & Properties Sector",
    "title": "Real Estate Report on Lands and Properties Sector Transactions 2024–2025",
    "period": "2024–2025",
    "citation": "RAK Statistics Office, Real Estate Report on Lands and Properties Sector Transactions 2024–2025.",
}

RAK_ANNUAL_2021 = {
    "id": "rak_annual_2021",
    "publisher": "RAK Statistics Office — Lands & Properties Sector",
    "title": "Real Estate Report on Lands and Properties Sector Transactions 2020–2021",
    "period": "2020–2021",
    "citation": "RAK Statistics Office, Real Estate Report on Lands and Properties Sector Transactions 2020–2021.",
}

RAK_MONTHLY_JAN26 = {
    "id": "rak_monthly_jan26",
    "publisher": "RAK Statistics Office — Lands & Properties Sector",
    "title": "Real Estate Trading Report — January 2025–2026",
    "period": "January 2026",
    "citation": "RAK Statistics Office, Real Estate Trading Report — January 2025–2026.",
}

REPORTS = [RAK_ANNUAL_2025, RAK_ANNUAL_2021, RAK_MONTHLY_JAN26]


# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW NARRATIVE (RAK Annual 2025, page 1)
# ─────────────────────────────────────────────────────────────────────────────

RAK_OVERVIEW_NARRATIVE = (
    "Real Estate Transactions of the Lands and Properties Sectors exceeded AED 18 billion "
    "in 2025. Based on the Annual Report issued by the Lands and Properties Sector, a "
    "large number of various Real Estate Transactions were recorded, such as Sales and "
    "Mortgages of plots, Documentation and Waivers. This included 2,964 sales with a "
    "value exceeding AED 3 billion, 1,480 Mortgages with total value of their contracts "
    "exceeding AED 12 billion, and 825 Waiver transactions with the total value of their "
    "market contracts exceeding AED 2 billion."
)

RAK_OVERVIEW_SUBTITLE = "Ras Al Khaimah real estate market intelligence, 2024–2025"


# ─────────────────────────────────────────────────────────────────────────────
# KEY STATS (RAK Annual 2025)
# ─────────────────────────────────────────────────────────────────────────────

RAK_KEY_STATS = [
    {"label": "Total Transaction Value",  "value": "AED 18.80B", "change": "+25% vs 2024",
     "period": "2025", "icon": "💰", "color_class": "teal",  "source": RAK_ANNUAL_2025},
    {"label": "Total Transactions",       "value": "5,269",     "change": "+4% vs 2024",
     "period": "2025", "icon": "🔢", "color_class": "blue",  "source": RAK_ANNUAL_2025},
    {"label": "Real Estate Sales",        "value": "2,964",     "change": "AED 3.19B · -1% count / -50% value",
     "period": "2025", "icon": "🏷️", "color_class": "amber", "source": RAK_ANNUAL_2025},
    {"label": "Total Investors",          "value": "3,469",     "change": "vs 3,363 in 2024",
     "period": "2025", "icon": "🌍", "color_class": "violet", "source": RAK_ANNUAL_2025},
]


# ─────────────────────────────────────────────────────────────────────────────
# ANNUAL TRANSACTIONS BREAKDOWN — Value & Count (RAK Annual 2025 Table 1)
# ─────────────────────────────────────────────────────────────────────────────

RAK_ANNUAL_2024_2025_VALUE = [
    # (category, 2024 AED, 2025 AED, share 2024 %, share 2025 %, %change)
    {"category": "Real Estate Sales Volume",     "y2024_aed": 6_438_983_837,  "y2025_aed": 3_192_316_419,
     "share_2024": 43, "share_2025": 17, "change_pct": -50, "source": RAK_ANNUAL_2025},
    {"category": "Real Estate Mortgages Volume", "y2024_aed": 4_889_069_491,  "y2025_aed": 12_682_671_958,
     "share_2024": 32, "share_2025": 67, "change_pct": 159, "source": RAK_ANNUAL_2025},
    {"category": "Waiver Market Value",          "y2024_aed": 3_757_413_142,  "y2025_aed": 2_928_225_958,
     "share_2024": 25, "share_2025": 16, "change_pct": -22, "source": RAK_ANNUAL_2025},
    {"category": "Total Transactions",           "y2024_aed": 15_085_466_470, "y2025_aed": 18_803_214_335,
     "share_2024": 100, "share_2025": 100, "change_pct": 25, "source": RAK_ANNUAL_2025},
]

RAK_ANNUAL_2024_2025_COUNT = [
    {"category": "Real Estate Sales Number",     "y2024": 2985, "y2025": 2964,
     "share_2024": 59, "share_2025": 56, "change_pct": -1, "source": RAK_ANNUAL_2025},
    {"category": "Real Estate Mortgages Number", "y2024": 1224, "y2025": 1480,
     "share_2024": 24, "share_2025": 28, "change_pct": 21, "source": RAK_ANNUAL_2025},
    {"category": "Waivers Number",               "y2024": 845,  "y2025": 825,
     "share_2024": 17, "share_2025": 16, "change_pct": -2, "source": RAK_ANNUAL_2025},
    {"category": "Total Number of Transactions", "y2024": 5054, "y2025": 5269,
     "share_2024": 100, "share_2025": 100, "change_pct": 4, "source": RAK_ANNUAL_2025},
]

RAK_TOP_REGION_BY_YEAR = [
    {"year": 2024, "region": "Jazeerat AL Marjan", "source": RAK_ANNUAL_2025},
    {"year": 2025, "region": "Jazeerat AL Marjan", "source": RAK_ANNUAL_2025},
]


# ─────────────────────────────────────────────────────────────────────────────
# HISTORICAL CONTEXT — 2020 vs 2021 (RAK Annual 2021 Table 1)
# ─────────────────────────────────────────────────────────────────────────────

RAK_ANNUAL_2020_2021_VALUE = [
    {"category": "Real Estate Sales Volume",     "y2020_aed": 1_001_412_200, "y2021_aed": 1_738_994_965,
     "share_2020": 26, "share_2021": 27, "change_pct": 74,  "source": RAK_ANNUAL_2021},
    {"category": "Real Estate Mortgages Volume", "y2020_aed": 2_463_386_166, "y2021_aed": 4_152_346_223,
     "share_2020": 64, "share_2021": 63, "change_pct": 69,  "source": RAK_ANNUAL_2021},
    {"category": "Waiver Market Value",          "y2020_aed":   382_099_485, "y2021_aed":   667_421_666,
     "share_2020": 10, "share_2021": 10, "change_pct": 75,  "source": RAK_ANNUAL_2021},
    {"category": "Total Transactions",           "y2020_aed": 3_846_897_851, "y2021_aed": 6_558_762_854,
     "share_2020": 100, "share_2021": 100, "change_pct": 70, "source": RAK_ANNUAL_2021},
]

RAK_ANNUAL_2020_2021_COUNT = [
    {"category": "Real Estate Sales Number",     "y2020": 1777, "y2021": 2406,
     "share_2020": 64, "share_2021": 59, "change_pct": 35, "source": RAK_ANNUAL_2021},
    {"category": "Real Estate Mortgages Number", "y2020": 544,  "y2021": 1147,
     "share_2020": 19, "share_2021": 28, "change_pct": 111, "source": RAK_ANNUAL_2021},
    {"category": "Waivers Number",               "y2020": 471,  "y2021": 529,
     "share_2020": 17, "share_2021": 13, "change_pct": 12, "source": RAK_ANNUAL_2021},
    {"category": "Total Number of Transactions", "y2020": 2792, "y2021": 4082,
     "share_2020": 100, "share_2021": 100, "change_pct": 46, "source": RAK_ANNUAL_2021},
]


# ─────────────────────────────────────────────────────────────────────────────
# POPULAR AREAS (RAK Annual 2025 Table 2 + RAK Annual 2021 Table 2)
# ─────────────────────────────────────────────────────────────────────────────

RAK_POPULAR_AREAS_2025 = [
    {"rank": 1, "region": "Jazeerat AL Marjan",
     "sales_value_2025_aed":   940_279_261, "sales_number_2025": 250,
     "sales_value_2024_aed": 4_044_092_592, "sales_number_2024": 378,
     "change_pct": -77, "source": RAK_ANNUAL_2025},
    {"rank": 2, "region": "AL Riffa",
     "sales_value_2025_aed":   605_902_422, "sales_number_2025": 412,
     "sales_value_2024_aed":   522_255_919, "sales_number_2024": 370,
     "change_pct": 16, "source": RAK_ANNUAL_2025},
    {"rank": 3, "region": "AL Jazeera AL Hamra (Qaryat AL Hamra)",
     "sales_value_2025_aed":   385_111_220, "sales_number_2025": 335,
     "sales_value_2024_aed":   431_826_921, "sales_number_2024": 504,
     "change_pct": -11, "source": RAK_ANNUAL_2025},
]

RAK_POPULAR_AREAS_2021 = [
    {"rank": 1, "region": "Al Jazirah Al Hamra",
     "sales_value_2021_aed": 782_505_476, "sales_number_2021": 762,
     "sales_value_2020_aed": 339_715_466, "sales_number_2020": 423,
     "change_pct": 130, "source": RAK_ANNUAL_2021},
    {"rank": 2, "region": "Saih Al Bir",
     "sales_value_2021_aed":  93_917_500, "sales_number_2021":  98,
     "sales_value_2020_aed":            0, "sales_number_2020":   0,
     "change_pct": None, "source": RAK_ANNUAL_2021,
     "note": "Not in the 2020 top three; comparison not reported."},
    {"rank": 3, "region": "Al Hudaiba",
     "sales_value_2021_aed":  61_342_200, "sales_number_2021":  78,
     "sales_value_2020_aed":            0, "sales_number_2020":   0,
     "change_pct": None, "source": RAK_ANNUAL_2021,
     "note": "Not in the 2020 top three; comparison not reported."},
]


# ─────────────────────────────────────────────────────────────────────────────
# PROPERTY USE — 2024 vs 2025 (RAK Annual 2025 Table 3)
# Rows exactly as the source lists them, with source-stated shares and % change.
# ─────────────────────────────────────────────────────────────────────────────

RAK_PROPERTY_USE_2024_2025 = [
    {"use": "Commercial",             "y2024_aed":    23_272_333, "y2024_n":  24, "y2024_share": 0.8,
                                       "y2025_aed":    10_720_000, "y2025_n":  21, "y2025_share": 0.7, "change_pct": -54},
    {"use": "Agricultural",           "y2024_aed":    96_681_770, "y2024_n":  66, "y2024_share": 2.2,
                                       "y2025_aed":   103_579_565, "y2025_n":  82, "y2025_share": 2.8, "change_pct":   7},
    {"use": "Popular Houses",         "y2024_aed":    14_588_750, "y2024_n":  31, "y2024_share": 1.0,
                                       "y2025_aed":    22_542_500, "y2025_n":  46, "y2025_share": 1.6, "change_pct":  55},
    {"use": "Free Residential",       "y2024_aed":   326_037_918, "y2024_n": 762, "y2024_share": 25.5,
                                       "y2025_aed":   274_361_810, "y2025_n": 798, "y2025_share": 26.9, "change_pct": -16},
    {"use": "Built Residential",      "y2024_aed":   294_514_656, "y2024_n": 428, "y2024_share": 14.3,
                                       "y2025_aed":   357_593_123, "y2025_n": 516, "y2025_share": 17.4, "change_pct":  21},
    {"use": "Apartments (Investment)", "y2024_aed":  668_061_598, "y2024_n": 969, "y2024_share": 32.5,
                                       "y2025_aed":   585_089_172, "y2025_n": 759, "y2025_share": 25.6, "change_pct": -12},
    {"use": "Villas (Investment)",    "y2024_aed":   503_418_932, "y2024_n": 248, "y2024_share": 8.3,
                                       "y2025_aed":   543_287_047, "y2025_n": 221, "y2025_share": 7.5, "change_pct":   8},
    {"use": "Commercial Residential", "y2024_aed": 1_201_006_402, "y2024_n": 212, "y2024_share": 7.1,
                                       "y2025_aed":   603_003_371, "y2025_n": 194, "y2025_share": 6.5, "change_pct": -50},
    {"use": "Investment Residential", "y2024_aed":   595_133_808, "y2024_n": 188, "y2024_share": 6.3,
                                       "y2025_aed":   312_487_668, "y2025_n": 280, "y2025_share": 9.4, "change_pct": -47},
    {"use": "Touristic",              "y2024_aed": 2_649_984_906, "y2024_n":  10, "y2024_share": 0.3,
                                       "y2025_aed":   341_504_312, "y2025_n":   2, "y2025_share": 0.1, "change_pct": -87},
    {"use": "Industrial",             "y2024_aed":     8_882_857, "y2024_n":   9, "y2024_share": 0.3,
                                       "y2025_aed":     6_360_000, "y2025_n":   4, "y2025_share": 0.1, "change_pct": -28},
    {"use": "Commercial Unit",        "y2024_aed":    22_190_885, "y2024_n":  37, "y2024_share": 1.2,
                                       "y2025_aed":    31_787_851, "y2025_n":  41, "y2025_share": 1.4, "change_pct":  43},
    {"use": "Infrastructure",         "y2024_aed":    35_209_022, "y2024_n":   1, "y2024_share": 0.03,
                                       "y2025_aed":              0, "y2025_n":   0, "y2025_share": 0.0, "change_pct": None,
     "note": "Source reports a dash (no data) for Infrastructure in 2025."},
]

RAK_PROPERTY_USE_NOTE = (
    "Values, counts and shares are reproduced from RAK Annual 2025 Table 3 exactly as "
    "reported. The source lists these categories with a dash where no value is recorded; "
    "those are shown as dashes here rather than replaced with a zero."
)


# ─────────────────────────────────────────────────────────────────────────────
# INVESTORS — Top 10 by Transaction Value (RAK Annual 2025 Tables 4 & 5)
# ─────────────────────────────────────────────────────────────────────────────

RAK_INVESTORS_BY_VALUE_2025 = [
    {"rank":  1, "nationality": "UAE",                "value_aed": 1_369_351_039, "source": RAK_ANNUAL_2025},
    {"rank":  2, "nationality": "UK",                 "value_aed":   172_332_131, "source": RAK_ANNUAL_2025},
    {"rank":  3, "nationality": "India",              "value_aed":   164_594_106, "source": RAK_ANNUAL_2025},
    {"rank":  4, "nationality": "The Russian Union",  "value_aed":    91_598_097, "source": RAK_ANNUAL_2025},
    {"rank":  5, "nationality": "Canada",             "value_aed":    86_540_576, "source": RAK_ANNUAL_2025},
    {"rank":  6, "nationality": "South Africa",       "value_aed":    58_838_418, "source": RAK_ANNUAL_2025},
    {"rank":  7, "nationality": "Sultanate of Oman",  "value_aed":    52_930_276, "source": RAK_ANNUAL_2025},
    {"rank":  8, "nationality": "Kuwait",             "value_aed":    52_927_345, "source": RAK_ANNUAL_2025},
    {"rank":  9, "nationality": "Egypt",              "value_aed":    50_618_200, "source": RAK_ANNUAL_2025},
    {"rank": 10, "nationality": "KSA",                "value_aed":    41_489_759, "source": RAK_ANNUAL_2025},
]

RAK_INVESTORS_BY_VALUE_2024 = [
    {"rank":  1, "nationality": "UAE",                "value_aed": 1_310_229_960, "source": RAK_ANNUAL_2025},
    {"rank":  2, "nationality": "India",              "value_aed":   261_822_351, "source": RAK_ANNUAL_2025},
    {"rank":  3, "nationality": "UK",                 "value_aed":   209_020_044, "source": RAK_ANNUAL_2025},
    {"rank":  4, "nationality": "The Russian Union",  "value_aed":    66_796_421, "source": RAK_ANNUAL_2025},
    {"rank":  5, "nationality": "Egypt",              "value_aed":    66_522_400, "source": RAK_ANNUAL_2025},
    {"rank":  6, "nationality": "USA",                "value_aed":    63_217_394, "source": RAK_ANNUAL_2025},
    {"rank":  7, "nationality": "Kuwait",             "value_aed":    54_252_118, "source": RAK_ANNUAL_2025},
    {"rank":  8, "nationality": "Pakistan",           "value_aed":    46_639_590, "source": RAK_ANNUAL_2025},
    {"rank":  9, "nationality": "Jordan",             "value_aed":    43_096_046, "source": RAK_ANNUAL_2025},
    {"rank": 10, "nationality": "Lebanon",            "value_aed":    43_030_201, "source": RAK_ANNUAL_2025},
]

RAK_INVESTORS_BY_NUMBER_2025 = [
    {"rank":  1, "nationality": "UAE",                "count": 2079, "source": RAK_ANNUAL_2025},
    {"rank":  2, "nationality": "India",              "count":  163, "source": RAK_ANNUAL_2025},
    {"rank":  3, "nationality": "UK",                 "count":  143, "source": RAK_ANNUAL_2025},
    {"rank":  4, "nationality": "Kuwait",             "count":   88, "source": RAK_ANNUAL_2025},
    {"rank":  5, "nationality": "The Russian Union",  "count":   70, "source": RAK_ANNUAL_2025},
    {"rank":  6, "nationality": "Canada",             "count":   42, "source": RAK_ANNUAL_2025},
    {"rank":  7, "nationality": "Pakistan",           "count":   42, "source": RAK_ANNUAL_2025},
    {"rank":  8, "nationality": "Egypt",              "count":   41, "source": RAK_ANNUAL_2025},
    {"rank":  9, "nationality": "Sultanate of Oman",  "count":   36, "source": RAK_ANNUAL_2025},
    {"rank": 10, "nationality": "KSA",                "count":   34, "source": RAK_ANNUAL_2025},
]

RAK_INVESTORS_TOTALS = {
    "y2024": 3363,
    "y2025": 3469,
    "source": RAK_ANNUAL_2025,
}


# ─────────────────────────────────────────────────────────────────────────────
# LATEST MONTHLY — January 2026 (RAK Monthly Jan 2026, r1.pdf)
# ─────────────────────────────────────────────────────────────────────────────

RAK_JAN_2026 = {
    "period": "January 2026",
    "sales_value_aed":   249_794_299,  "sales_count":  302,
    "mortgages_aed":     136_953_350,  "mortgages_count": 104,
    "waivers_aed":        36_171_892,  "waivers_count":  39,
    "source": RAK_MONTHLY_JAN26,
}

RAK_JAN_2025 = {
    "period": "January 2025",
    "sales_value_aed":   549_433_417,  "sales_count":  234,
    "mortgages_aed":   1_116_512_387,  "mortgages_count": 111,
    "waivers_aed":        66_495_851,  "waivers_count":  54,
    "source": RAK_MONTHLY_JAN26,
}

RAK_JAN_HIGHEST_SALES = [
    {"period": "January 2026", "region": "AL NAKHEEL",
     "type": "Commercial Residential Land — Built (Transfer)",
     "value_aed": 7_000_000, "source": RAK_MONTHLY_JAN26},
    {"period": "January 2025", "region": "Jazeerat Al Marjan",
     "type": "Tourist Land — Free (Freehold — Transfer)",
     "value_aed": 160_000_000, "source": RAK_MONTHLY_JAN26},
]

RAK_JAN_TOP_REGION_2026 = {
    "region": "AL RIFFA", "sales_value_aed": 70_715_594, "sales_count": 53,
    "source": RAK_MONTHLY_JAN26,
}

RAK_JAN_TOP_REGION_2025 = {
    "region": "Al Jazeera Al Hamra (Qaryat Al Hamra)",
    "sales_value_aed": 30_129_689, "sales_count": 35,
    "source": RAK_MONTHLY_JAN26,
}

RAK_JAN_FREEHOLD_MARKET = [
    {"land_use": "Apartment (Investment)", "value_aed": 72_958_128, "count": 77, "share_pct": 81,
     "source": RAK_MONTHLY_JAN26},
    {"land_use": "Villa (Investment)",     "value_aed": 42_752_879, "count": 18, "share_pct": 19,
     "source": RAK_MONTHLY_JAN26},
    {"land_use": "Total",                  "value_aed": 115_711_007, "count": 95, "share_pct": 100,
     "source": RAK_MONTHLY_JAN26},
]

RAK_JAN_FREEHOLD_AREAS_TOTAL = {
    "sales_count": 407, "sales_value_aed": 762_041_962,
    "source": RAK_MONTHLY_JAN26,
}


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY TIME SERIES — every monthly RAK Statistics Office report we could read.
# Each data point comes verbatim from one of the 26 monthly PDFs the user
# provided. Reports whose values could not be extracted (image-based text that
# neither pypdf, pdfplumber, nor OCR could parse into a clean 6-row table) are
# listed in RAK_MONTHLY_UNREADABLE below and are NOT invented.
# ─────────────────────────────────────────────────────────────────────────────

RAK_MONTHLY_TIMESERIES = [
    # ── 2019 (from the 2019-2020 monthly reports — prev-year column) ──
    {"year": 2019, "month": "January",  "sales_v": 105_635_787, "sales_n": 207,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "February", "sales_v": 130_463_474, "sales_n": 220,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "March",    "sales_v":  97_273_555, "sales_n": 191,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "April",    "sales_v":  80_679_853, "sales_n": 163,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "May",      "sales_v":  85_250_926, "sales_n": 155,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "June",     "sales_v":  67_420_139, "sales_n": 139,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "July",     "sales_v":  69_092_022, "sales_n": 144,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2019, "month": "August",   "sales_v":  64_987_180, "sales_n": 130,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    # ── 2020 (current-year column from the 2019-2020 monthlies, plus Dec 2020 from the Dec 2020/2021 report) ──
    {"year": 2020, "month": "January",  "sales_v":  61_912_710, "sales_n": 125,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "February", "sales_v":  88_045_257, "sales_n": 177,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "March",    "sales_v":  57_613_160, "sales_n": 134,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "April",    "sales_v":  34_005_382, "sales_n":  98,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "May",      "sales_v":  34_416_591, "sales_n":  65,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "June",     "sales_v":  87_966_918, "sales_n": 147,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "July",     "sales_v": 108_808_877, "sales_n": 184,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "August",   "sales_v": 104_484_715, "sales_n": 190,
     "mort_v": None, "mort_n": None, "waiv_v": None, "waiv_n": None,
     "source_note": "Sales-only (2019-2020 monthly report format)"},
    {"year": 2020, "month": "December", "sales_v": 112_858_726, "sales_n": 186,
     "mort_v":     65_120_201, "mort_n":  59, "waiv_v":  38_682_278, "waiv_n":  38,
     "source_note": "December 2020/2021 monthly report (prev-year column)"},
    # ── 2021 ──
    {"year": 2021, "month": "December", "sales_v": 129_885_930, "sales_n": 198,
     "mort_v":    514_753_763, "mort_n":  86, "waiv_v":  27_694_107, "waiv_n":  38,
     "source_note": "December 2020/2021 monthly report"},
    # ── 2022 ──
    {"year": 2022, "month": "October",  "sales_v": 119_869_006, "sales_n": 177,
     "mort_v":    674_360_576, "mort_n":  33, "waiv_v":  28_036_886, "waiv_n":  39,
     "source_note": "October 2022/2023 monthly report (prev-year column, OCR)"},
    {"year": 2022, "month": "November", "sales_v": 156_320_288, "sales_n": 225,
     "mort_v":    115_748_388, "mort_n":  64, "waiv_v":  24_943_056, "waiv_n":  31,
     "source_note": "November 2022/2023 monthly report (prev-year column)"},
    # ── 2023 ──
    {"year": 2023, "month": "January",  "sales_v": 328_256_070, "sales_n":  53,
     "mort_v":     69_241_851, "mort_n":  43, "waiv_v": None,        "waiv_n":  25,
     "source_note": "January 2023/2024 monthly report (prev-year column, OCR)"},
    {"year": 2023, "month": "June",     "sales_v": 297_575_951, "sales_n": 175,
     "mort_v":    161_788_789, "mort_n": 106, "waiv_v":  77_593_294, "waiv_n":  89,
     "source_note": "June 2023/2024 monthly report (prev-year column, OCR)"},
    {"year": 2023, "month": "October",  "sales_v": 304_910_035, "sales_n": 246,
     "mort_v":    886_167_023, "mort_n": 158, "waiv_v":  92_409_621, "waiv_n":  52,
     "source_note": "October 2022/2023 monthly report (OCR)"},
    {"year": 2023, "month": "November", "sales_v": 582_281_834, "sales_n": 329,
     "mort_v":    156_883_251, "mort_n": 146, "waiv_v": 111_396_720, "waiv_n": 102,
     "source_note": "November 2022/2023 monthly report"},
    # ── 2024 ──
    {"year": 2024, "month": "January",  "sales_v": 173_517_441, "sales_n": 109,
     "mort_v":  1_488_560_324, "mort_n":  83, "waiv_v": None,        "waiv_n":  48,
     "source_note": "January 2023/2024 monthly report (OCR)"},
    {"year": 2024, "month": "June",     "sales_v": 2_935_067_291, "sales_n":  95,
     "mort_v":    110_476_796, "mort_n":  89, "waiv_v":  78_815_423, "waiv_n": None,
     "source_note": "June 2023/2024 monthly report (OCR)"},
    {"year": 2024, "month": "August",   "sales_v": 197_985_289, "sales_n": 245,
     "mort_v":    102_445_860, "mort_n": 105, "waiv_v":  59_894_347, "waiv_n": None,
     "source_note": "August 2024/2025 monthly report (prev-year column, OCR)"},
    {"year": 2024, "month": "November", "sales_v": 751_753_825, "sales_n": 257,
     "mort_v":    148_310_038, "mort_n": 127, "waiv_v":  46_882_337, "waiv_n":  55,
     "source_note": "November 2024/2025 monthly report (prev-year column)"},
    {"year": 2024, "month": "December", "sales_v": 168_295_839, "sales_n": 245,
     "mort_v":    123_946_085, "mort_n":  92, "waiv_v": 1_436_821_780, "waiv_n": 89,
     "source_note": "December 2024/2025 monthly report (prev-year column)"},
    # ── 2025 ──
    {"year": 2025, "month": "January",  "sales_v": 549_433_417, "sales_n": 234,
     "mort_v":  1_116_512_387, "mort_n": 111, "waiv_v":  66_495_851, "waiv_n":  54,
     "source_note": "January 2025/2026 monthly report (prev-year column)"},
    {"year": 2025, "month": "June",     "sales_v": 216_527_787, "sales_n": 255,
     "mort_v":    146_506_905, "mort_n": 143, "waiv_v": 163_041_129, "waiv_n": None,
     "source_note": "June 2024/2025 monthly report (OCR)"},
    {"year": 2025, "month": "August",   "sales_v": 174_068_834, "sales_n": 201,
     "mort_v":    125_707_386, "mort_n": 147, "waiv_v": 232_334_273, "waiv_n": None,
     "source_note": "August 2024/2025 monthly report (OCR)"},
    {"year": 2025, "month": "November", "sales_v": 166_581_440, "sales_n": 220,
     "mort_v":    100_690_201, "mort_n": 102, "waiv_v": 333_744_328, "waiv_n":  71,
     "source_note": "November 2024/2025 monthly report"},
    {"year": 2025, "month": "December", "sales_v": 233_008_207, "sales_n": 231,
     "mort_v":    119_958_120, "mort_n":  85, "waiv_v":  43_280_655, "waiv_n":  35,
     "source_note": "December 2024/2025 monthly report"},
    # ── 2026 ──
    {"year": 2026, "month": "January",  "sales_v": 249_794_299, "sales_n": 302,
     "mort_v":    136_953_350, "mort_n": 104, "waiv_v":  36_171_892, "waiv_n":  39,
     "source_note": "January 2025/2026 monthly report (r1.pdf)"},
]

# Reports the user provided whose data could NOT be extracted from the PDF —
# image-based rendering where neither text extraction nor OCR produced a
# reliable 6-row transactions table. Per the strict rule, values are NOT
# invented for these; they are surfaced on the dashboard so nothing is hidden.
RAK_MONTHLY_UNREADABLE = [
    {"period": "February 2023 / 2024",  "reason": "PDF text rendered as vector; OCR produced no reliable table."},
    {"period": "March 2023 / 2024",     "reason": "PDF text rendered as vector; OCR produced no reliable table."},
    {"period": "April 2023 / 2024",     "reason": "OCR values failed sanity checks."},
    {"period": "May 2023 / 2024",       "reason": "OCR values failed sanity checks."},
    {"period": "February 2024 / 2025",  "reason": "PDF text rendered as vector; OCR produced no reliable table."},
    {"period": "March 2024 / 2025",     "reason": "OCR values failed sanity checks."},
    {"period": "April 2024 / 2025",     "reason": "OCR values failed sanity checks."},
    {"period": "May 2024 / 2025",       "reason": "PDF text rendered as vector; OCR produced no reliable table."},
]


# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY (used by the Sources section and the PDF methodology)
# ─────────────────────────────────────────────────────────────────────────────

def all_sources() -> list[dict]:
    return list(REPORTS)


def source_index() -> list[tuple[str, str]]:
    return [
        ("Overview / Key stats",         RAK_ANNUAL_2025["citation"]),
        ("2024–2025 transactions",       RAK_ANNUAL_2025["citation"]),
        ("2020–2021 transactions",       RAK_ANNUAL_2021["citation"]),
        ("Popular areas 2025",           RAK_ANNUAL_2025["citation"]),
        ("Popular areas 2021",           RAK_ANNUAL_2021["citation"]),
        ("Property use 2024–2025",       RAK_ANNUAL_2025["citation"]),
        ("Investors 2024 & 2025",        RAK_ANNUAL_2025["citation"]),
        ("Latest monthly (January 2026)", RAK_MONTHLY_JAN26["citation"]),
        ("Monthly time series 2019–2026", "RAK Statistics Office monthly reports (26 PDFs; 35 data points extracted)."),
    ]
