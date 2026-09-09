"""Versioned bounded lexicon. No geography, company identities or source scores.

Phrases are high precision only in article focus; body-only acceptance also
requires category diversity and density. Weak terms never suffice alone.
Arabic coverage is deliberately finite, without translation or stemming.
"""

PHRASES = {
    "market": (
        "real estate", "property market", "housing market", "property prices",
        "home prices", "house prices", "property values", "realty market",
        "residential property", "commercial property", "industrial property",
        "retail property", "hotel property", "سوق العقارات", "اسعار العقارات",
        "اسعار المنازل", "السوق العقاري", "العقارات السكنية",
    ),
    "sales": (
        "property sales", "home sales", "house sales", "villa sales", "apartment sales",
        "apartment transactions", "property transactions", "real estate transactions",
        "land sales", "مبيعات العقارات", "المعاملات العقارية", "مبيعات الشقق",
    ),
    "rental": (
        "rental market", "rental prices", "property rents", "apartment rents",
        "housing rents", "office leasing", "warehouse leasing", "warehouse lease",
        "apartment leasing", "tenancy agreements", "rent increases", "rents rise",
        "rents fall", "ارتفاع الايجارات", "اسعار الايجارات", "ايجار الشقق",
        "عقود الايجار", "ايجارات العقارات",
    ),
    "development": (
        "off plan", "property launch", "residential project",
        "residential development", "property development", "housing development",
        "real estate development", "master development", "master community",
        "master communities", "land development", "hotel development",
        "مشروع سكني",
        "مجمع سكني", "تطوير عقاري", "التطوير العقاري", "علي الخارطة", "على الخارطة",
    ),
    "supply": (
        "housing supply", "residential supply", "new homes", "unit handover",
        "unit handovers", "property completion", "housing inventory", "housing shortage",
        "تسليم الوحدات", "وحدات سكنية", "المعروض السكني",
    ),
    "mortgage": (
        "mortgage", "mortgages", "home loan", "home loans", "housing finance",
        "الرهن العقاري", "التمويل العقاري", "قروض الاسكان",
    ),
    "investment": (
        "rental yield", "rental yields", "property investment", "real estate investment",
        "reit", "reits", "property investor", "property investors",
        "الاستثمار العقاري", "العائد الايجاري",
    ),
    "regulation": (
        "property regulation", "real estate law", "rent regulation", "tenancy regulation",
        "property registration", "land registration", "tenancy law", "rent control",
        "تسجيل العقارات", "تسجيل الاراضي", "قانون الايجارات", "تنظيم الايجارات",
    ),
}

WEAK = ("property", "properties", "housing", "rent", "rents", "rental", "lease",
        "leasing", "villa", "villas", "apartment", "apartments", "townhouse",
        "warehouse", "office", "land", "construction", "developer", "development",
        "عقار", "عقارات", "العقارات", "سكن", "الاسكان", "اراضي", "ايجار")

# Remove non-property uses before scanning positives. Record the safeguard.
COLLISIONS = {
    "non_property": ("intellectual property", "object property", "software property",
                     "material property", "material properties", "physical properties",
                     "chemical properties", "property of an object", "الملكية الفكرية"),
}
# Entire sentence is incidental to the economic/property focus of an article.
INCIDENTAL = {
    "company_background": ("portfolio includes", "interests include", "interests in",
                           "diversified company", "diversified group", "businesses include",
                           "operations span", "including real estate", "such as real estate"),
    "shelter_context": ("humanitarian", "refugee", "refugees", "emergency shelter",
                        "employee accommodation", "temporary shelters", "نازحين", "لاجئين"),
    "agriculture_environment": ("agricultural land", "farmland", "land conservation",
                                "wildlife habitat", "military territory", "اراضي زراعية"),
}

BACKGROUND = {
    "generic_economy": ("gdp", "inflation", "federal reserve", "central bank", "interest rates",
                        "oil prices", "stocks", "stock market", "bonds", "currencies", "currency",
                        "employment", "tourism", "trade", "earnings", "corporate financing"),
    "infrastructure": ("road", "roads", "bridge", "airport", "metro", "port",
                       "pipeline", "oil facility", "utility", "infrastructure"),
}

# Same-clause proximity: physical property type + market/development action.
PROPERTY_TYPES = ("villa", "villas", "apartment", "apartments", "townhouse", "townhouses",
                  "warehouse", "warehouses", "residential units", "commercial units", "housing")
PROPERTY_ACTIONS = ("sales", "transactions", "prices", "rents", "leasing", "launch",
                    "launches", "construction", "build", "builds", "development", "supply")
