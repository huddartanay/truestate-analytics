"""
Sharjah source-of-truth registry.

Every value on the Sharjah dashboard and every value inside the Sharjah PDF
report is defined here — nowhere else. Each item is stamped with its source
report, its period, its status (published / mathematically derived from a
published figure / estimated by the source), and its verbatim wording where
applicable.

Reports the values come from (and nothing else):

    SAVILLS_Q1_2026  Savills — Sharjah Residential Market in Minutes, Q1 2026
    MARKAZ_2024      Marmore/Markaz — UAE Real Estate Report, H1 2024 review + H2 2024 outlook
                     (Sharjah-specific items only, from p.22)
    MARKAZ_2024_25   Marmore/Markaz — UAE Real Estate Report, H2 2024 review + H1 2025 outlook
                     (Sharjah-specific items only, from p.24)

If a value is not explicitly present in one of these reports for Sharjah, it
is not in this file. Nothing here is derived from Dubai, Abu Dhabi, or a
UAE-wide aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE HANDLES
# ─────────────────────────────────────────────────────────────────────────────

SAVILLS_Q1_2026 = {
    "id": "savills_q1_2026",
    "publisher": "Savills",
    "title": "Sharjah Residential Market — Market in Minutes, Q1 2026",
    "period": "Q1 2026",
    "citation": "Savills, Sharjah Residential Market — Market in Minutes, Q1 2026.",
}

MARKAZ_2024 = {
    "id": "markaz_2024",
    "publisher": "Marmore / Markaz (Kuwait Financial Centre)",
    "title": "UAE Real Estate Report — H1 2024 Review and H2 2024 Outlook",
    "period": "H1 2024",
    "citation": "Marmore/Markaz, UAE Real Estate Report — H1 2024 Review and H2 2024 Outlook, p. 22.",
}

MARKAZ_2024_25 = {
    "id": "markaz_2024_25",
    "publisher": "Marmore / Markaz (Kuwait Financial Centre)",
    "title": "UAE Real Estate Report — H2 2024 Review and H1 2025 Outlook",
    "period": "H2 2024",
    "citation": "Marmore/Markaz, UAE Real Estate Report — H2 2024 Review and H1 2025 Outlook, p. 24.",
}

REPORTS = [SAVILLS_Q1_2026, MARKAZ_2024, MARKAZ_2024_25]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — KEY STATS (Savills Q1 2026, page 1)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_KEY_STATS = [
    {
        "label": "Total Transaction Value",
        "value": "AED 18.5B",
        "change": "+40.7% year-on-year",
        "period": "Q1 2026",
        "source": SAVILLS_Q1_2026,
        "icon": "💰",
        "color_class": "teal",
    },
    {
        "label": "Total Transactions",
        "value": "29,235",
        "change": "+18.9% year-on-year",
        "period": "Q1 2026",
        "source": SAVILLS_Q1_2026,
        "icon": "🔢",
        "color_class": "blue",
    },
    {
        "label": "Sales Transactions",
        "value": "9,978",
        "change": "+18.9% year-on-year",
        "period": "Q1 2026",
        "source": SAVILLS_Q1_2026,
        "icon": "🏷️",
        "color_class": "amber",
    },
    {
        "label": "Investing Nationalities",
        "value": "113",
        "change": "vs 97 in Q1 2025",
        "period": "Q1 2026",
        "source": SAVILLS_Q1_2026,
        "icon": "🌍",
        "color_class": "violet",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — MONTHLY DYNAMICS (Savills Q1 2026, page 2)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_MONTHLY_DYNAMICS = [
    {
        "month": "January 2026",
        "headline": "AED 9.3B in transactions. 10,333 deals.",
        "note": (
            "Record January activity. ACRES exhibition drove AED 5B in sales in 4 days."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "month": "February 2026",
        "headline": "Sustained activity across both residential and investment segments.",
        "note": "Escrow framework publicly launched.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "month": "March 2026",
        "headline": (
            "Regional tensions from 28 February introduced caution."
        ),
        "note": "Ramadan seasonality compounded the slowdown.",
        "source": SAVILLS_Q1_2026,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — TRANSACTION VALUE QUARTERLY (Savills Q1 2026, page 2)
# ─────────────────────────────────────────────────────────────────────────────
#
# The Savills report shows a quarterly bar chart covering 2024, 2025 and Q1
# 2026, with Q4 2025 explicitly marked "† estimated from official full-year
# figure (AED 65.6B)". Individual quarterly bar values are NOT numerically
# labelled in the source and are represented visually only. Rather than
# reverse-engineer them from pixels (prohibited by scope), only the values
# the report itself states in numbers are recorded here. Anything derived
# arithmetically from those explicit values is flagged `status = "derived"`.

SHARJAH_TRANSACTION_VALUE_POINTS = [
    {
        "period": "Q1 2025",
        "value_aed_billion": 18.5 / 1.407,   # derived from Savills Q1 2026 stated +40.7% YoY
        "status": "derived",
        "note": "Derived from Savills stated Q1 2026 value AED 18.5B and +40.7% YoY.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "Q1 2026",
        "value_aed_billion": 18.5,
        "status": "published",
        "note": "Savills Q1 2026 key stat.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "FY 2025",
        "value_aed_billion": 65.6,
        "status": "published",
        "note": "Savills chart note: Q4 2025 estimated from official full-year figure (AED 65.6B).",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "April 2026",
        "value_aed_billion": 3.5,
        "status": "published (post-Q1 indicator)",
        "note": "Savills page 1: post-Q1 April 2026 total, released after Q1 close.",
        "source": SAVILLS_Q1_2026,
    },
]

SHARJAH_TRANSACTION_VALUE_CHART_NOTE = (
    "The Savills report shows a quarterly bar chart across 2024, 2025 and Q1 2026, "
    "with Q4 2025 marked as an estimate derived from the official full-year figure "
    "(AED 65.6B). Only values the report explicitly states in numbers are tabulated "
    "here — individual mid-quarter bars are shown visually in the source and are "
    "not reproduced numerically."
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — TRANSACTION VOLUME QUARTERLY (Savills Q1 2026, page 2)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_TRANSACTION_VOLUME_POINTS = [
    {
        "period": "Q1 2025",
        "transactions": round(29235 / 1.189),   # derived from Savills Q1 2026 stated +18.9% YoY
        "status": "derived",
        "note": "Derived from Savills stated Q1 2026 volume 29,235 and +18.9% YoY.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "Q1 2026",
        "transactions": 29235,
        "status": "published",
        "note": "Savills Q1 2026 key stat.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "January 2026",
        "transactions": 10333,
        "status": "published",
        "note": "Savills monthly dynamics — record January activity.",
        "source": SAVILLS_Q1_2026,
    },
    {
        "period": "April 2026",
        "transactions": 15669,
        "status": "published (post-Q1 indicator)",
        "note": "Savills page 1: post-Q1 April 2026 total, released after Q1 close.",
        "source": SAVILLS_Q1_2026,
    },
]

SHARJAH_TRANSACTION_VOLUME_CHART_NOTE = (
    "The Savills report shows a quarterly transaction-count bar chart across 2024, "
    "2025 and Q1 2026, with quarters estimated from official H1, 9M and FY "
    "cumulative releases marked with †. Only values the report explicitly states "
    "in numbers are tabulated here."
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — INVESTMENT BY NATIONALITY (Savills Q1 2026, page 3)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_INVESTOR_NATIONALITY = [
    {"label": "UAE Nationals",   "value_aed_billion": 9.0, "source": SAVILLS_Q1_2026},
    {"label": "International",   "value_aed_billion": 5.3, "source": SAVILLS_Q1_2026},
    {"label": "Arab Nationals",  "value_aed_billion": 3.4, "source": SAVILLS_Q1_2026},
    {"label": "GCC Nationals",   "value_aed_billion": 0.8, "source": SAVILLS_Q1_2026},
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — SALES BY PROPERTY TYPE (Savills Q1 2026, page 3)
# ─────────────────────────────────────────────────────────────────────────────
#
# STRICT: the source displays these three categories only, and the percentages
# do NOT sum to 100%. They are NOT normalised here and no "Other" is invented.

SHARJAH_PROPERTY_TYPE_SHARE = [
    {"label": "Residential",   "share_pct": 78.0, "source": SAVILLS_Q1_2026},
    {"label": "Commercial",    "share_pct":  6.4, "source": SAVILLS_Q1_2026},
    {"label": "Agricultural",  "share_pct":  3.2, "source": SAVILLS_Q1_2026},
]

SHARJAH_PROPERTY_TYPE_NOTE = (
    "Shown here in the same categories and precision as the Savills report. "
    "The source percentages do not sum to 100% and are NOT normalised."
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — TOP PERFORMING AREAS BY TRADING VALUE (Savills Q1 2026, page 3)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_TOP_AREAS = [
    {"rank": 1, "area": "Muwaileh Commercial", "value_aed_million": 1700, "source": SAVILLS_Q1_2026,
     "note": "Q1 aggregate. Savills notes the January figure for Muwaileh Commercial was AED 1.1B."},
    {"rank": 2, "area": "Al Belaida",          "value_aed_million": 1100, "source": SAVILLS_Q1_2026},
    {"rank": 3, "area": "Al Khan",             "value_aed_million":  718, "source": SAVILLS_Q1_2026},
    {"rank": 4, "area": "Hamriyah West",       "value_aed_million":  715, "source": SAVILLS_Q1_2026},
    {"rank": 5, "area": "Rawdat Al Sidr",      "value_aed_million":  568, "source": SAVILLS_Q1_2026},
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — NOTABLE TRANSACTIONS (Savills Q1 2026, page 4)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_NOTABLE_TRANSACTIONS = [
    {"area": "Al Khan",     "type": "Built-in land", "transaction_type": "Sale",     "value_aed_million":  90, "source": SAVILLS_Q1_2026},
    {"area": "Al Tay West", "type": "Vacant land",   "transaction_type": "Mortgage", "value_aed_million": 240, "source": SAVILLS_Q1_2026},
    {"area": "Al Majaz 1",  "type": "Land",          "transaction_type": "Mortgage", "value_aed_million": 153, "source": SAVILLS_Q1_2026},
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — NEW PROJECT REGISTRATIONS (Savills Q1 2026, page 4)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_NEW_PROJECTS = [
    {"metric": "New projects registered",         "value": 7,   "unit": "projects", "period": "Q1 2026",             "source": SAVILLS_Q1_2026},
    {"metric": "New freehold-eligible projects",  "value": 3,   "unit": "projects", "period": "Q1 2026",             "source": SAVILLS_Q1_2026},
    {"metric": "Total freehold projects",         "value": 47,  "unit": "projects", "period": "Cumulative since 2022", "source": SAVILLS_Q1_2026},
    {"metric": "ACRES 2026 sales",                "value": 5,   "unit": "AED billion (in 4 days)", "period": "January 2026", "source": SAVILLS_Q1_2026},
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — REGULATORY LANDSCAPE
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_REGULATORY = [
    {
        "title": "Escrow Regulation — Executive Council Resolution No. 37 of 2024",
        "period": "Formally launched at ACRES, January 2026",
        "summary": (
            "Mandatory escrow accounts for off-plan residential development in Sharjah, "
            "requiring all buyer payments to be held in bank-managed escrow accounts, "
            "with funds released progressively against verified construction milestones."
        ),
        "impact": (
            "Addresses a structural confidence gap in the off-plan segment, particularly "
            "for more cautious international buyers attracted by Sharjah's relative pricing. "
            "Savills notes it materially alters the risk profile of off-plan investment "
            "in the emirate."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "title": "Freehold Ownership Reforms — Resolution No. 30 of 2022",
        "period": "In effect; expanding through Q1 2026",
        "summary": (
            "Freehold ownership reforms that continue to broaden Sharjah's active buyer "
            "base. Q1 2026 added 3 new freehold-eligible projects; 47 freehold projects "
            "have been approved cumulatively since 2022."
        ),
        "impact": (
            "Savills identifies the freehold framework as a driver of Sharjah's "
            "progressive internationalisation — 113 nationalities were active in Q1 2026 "
            "against 97 in Q1 2025."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "title": "Sharjah Law No. (5) of 2024 on Property Leasing in the Emirate",
        "period": "H2 2024",
        "summary": (
            "Issued by Dr. Sheikh Sultan bin Muhammad Al Qasimi, Supreme Council Member "
            "and Ruler of Sharjah. Applies to properties leased for residential, "
            "commercial, industrial and professional purposes. Landlords are prohibited "
            "from raising rents for three years unless all parties agree; if an increase "
            "is agreed within that period it cannot be raised again for a further two "
            "years. Landlords must certify lease contracts or renewals within 15 days of "
            "drafting; where no certified lease exists, either party may file a claim "
            "with the Rental Disputes Centre."
        ),
        "impact": (
            "Residential tenants in Sharjah now enjoy a three-year protection from "
            "eviction; businesses receive a five-year safeguard. Markaz records the law "
            "as intended to provide stability and predictability for tenants in the "
            "Sharjah property market."
        ),
        "source": MARKAZ_2024_25,
    },
    {
        "title": "SRERD × UAE Pass — Digital deeds integration",
        "period": "14 April 2024",
        "summary": (
            "The Real Estate Registration Department in Sharjah (SRERD) announced the "
            "provision of ownership and usufruct deeds of various types via the UAE "
            "Digital Identity (UAE Pass) digital wallet, becoming the first government "
            "department in the emirate to provide this service."
        ),
        "impact": (
            "SRERD customers can download ownership deeds, joint ownership deeds, "
            "usufruct deeds and joint usufruct deeds through the digital ID smart "
            "application on mobile phones, in line with the UAE government's digital "
            "transformation vision."
        ),
        "source": MARKAZ_2024,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 11 — INFRASTRUCTURE (Savills Q1 2026, page 4)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_INFRASTRUCTURE = [
    {
        "title": "Etihad Rail Phase 1",
        "expected": "Passenger services anticipated in 2026",
        "detail": (
            "Stations serving Sharjah city and Al Dhaid. Savills notes the potential to "
            "meaningfully alter residential demand patterns along the corridor by "
            "improving connectivity to Dubai and Abu Dhabi. Locations in proximity to "
            "confirmed station sites are already attracting elevated interest."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "title": "Sharjah International Airport — Expansion",
        "expected": "Planned expansion to 25 million passengers annually by 2027",
        "detail": (
            "Savills describes the expansion as a further source of medium-term demand "
            "support, reinforcing the emirate's position as a self-sufficient urban "
            "centre rather than a peripheral extension of the wider conurbation."
        ),
        "source": SAVILLS_Q1_2026,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 — NEAR-TERM CONDITIONS (Savills Q1 2026, page 5)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_NEAR_TERM = [
    (
        "January's exceptional performance was driven in part by structural factors "
        "specific to the ACRES exhibition period — reduced registration fees and the "
        "concentration of Q4 2025 project launches registering at the event — which "
        "are unlikely to recur at the same scale in subsequent months. The underlying "
        "quarterly run rate is therefore somewhat softer than the opening month implies."
    ),
    (
        "April 2026 recorded AED 3.5 billion across 15,669 transactions — a level "
        "materially below the Q1 monthly average but consistent with a market that has "
        "moderated rather than retrenched. Savills labels this a post-Q1 early indicator."
    ),
    (
        "March moderation reflects the early impact of regional geopolitical uncertainty "
        "that emerged from late February. The secondary market was most acutely "
        "affected, while the primary off-plan market held up comparatively well, "
        "sustained by pipeline registrations with a degree of timing lag."
    ),
    (
        "The persistence of that uncertainty represents the principal near-term risk, "
        "with the potential to weigh on international buyer activity, developer launch "
        "programmes and, over a longer horizon, pricing in more sentiment-sensitive "
        "segments."
    ),
]

SHARJAH_APRIL_POST_Q1 = {
    "period": "April 2026 — post-Q1 early indicator",
    "value": "AED 3.5B across 15,669 transactions",
    "note": (
        "Reported by Savills subsequent to the close of Q1 2026. Must NOT be included in "
        "any Q1 2026 total. Sales across Sharjah City were led once again by Muwaileh "
        "Commercial, with Tilal and Rodhat Al Sidr also registering meaningful activity."
    ),
    "source": SAVILLS_Q1_2026,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 13 — UNDERLYING MARKET FUNDAMENTALS (Savills Q1 2026, page 5)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_FUNDAMENTALS = [
    (
        "The market's character as a predominantly end-user driven, affordability-led "
        "environment provides a degree of inherent stability. End-user demand tends to "
        "be more durable through periods of external uncertainty."
    ),
    (
        "Sharjah's pricing position relative to Dubai continues to work in its favour. "
        "As Dubai's residential market has appreciated materially over recent years, "
        "the cost differential has widened, and Sharjah has become an increasingly "
        "considered destination for buyers seeking quality residential product at "
        "accessible price points."
    ),
    (
        "The active buyer base has grown consistently year on year and speaks to "
        "deepening international awareness of the market's merits."
    ),
    (
        "The supply pipeline is anchored by a series of well-regarded masterplan "
        "developments — Masaar, Al Mamsha, Sustainable City and the broader Tilal "
        "corridor — which have demonstrated sustained demand across multiple launch "
        "cycles."
    ),
    (
        "Rental yields, described by Savills as among the most competitive in the UAE, "
        "provide an additional pillar of support for the investment case, independent "
        "of short-term sentiment."
    ),
]

SHARJAH_MASTERPLANS = [
    {"name": "Masaar",           "source": SAVILLS_Q1_2026},
    {"name": "Al Mamsha",        "source": SAVILLS_Q1_2026},
    {"name": "Sustainable City", "source": SAVILLS_Q1_2026},
    {"name": "Tilal corridor",   "source": SAVILLS_Q1_2026},
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 14 — OUTLOOK / FORWARD SIGNALS (Savills Q1 2026, page 5)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_FORWARD_SIGNALS = [
    {
        "number": 1,
        "text": (
            "Q2 transaction volumes are expected to reflect the March moderation. "
            "Resolution of regional uncertainty and the post-Ramadan seasonal recovery "
            "will be key indicators to monitor in the coming months."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "number": 2,
        "text": (
            "The mandatory escrow framework and continued freehold expansion are "
            "structural positives for the off-plan segment over the medium term, subject "
            "to the broader external environment remaining supportive."
        ),
        "source": SAVILLS_Q1_2026,
    },
    {
        "number": 3,
        "text": (
            "Etihad Rail Phase 1 connectivity, if delivered on the anticipated timeline, "
            "has the potential to reprice residential locations along the corridor. "
            "Supply delivery from major masterplan communities will be a key variable "
            "for the market through 2026 and 2027."
        ),
        "source": SAVILLS_Q1_2026,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 15 — MARKET OVERVIEW NARRATIVE (Savills Q1 2026, page 1)
# ─────────────────────────────────────────────────────────────────────────────

SHARJAH_OVERVIEW_NARRATIVE = (
    "Sharjah's residential market recorded a strong first quarter in 2026, with total "
    "real estate trading value rising 40.7% year-on-year to AED 18.5 billion across "
    "29,235 transactions. Activity was heavily concentrated in January and February, "
    "which performed in line with the strongest months of 2025. March, however, "
    "reflected a more cautious environment following the escalation of regional "
    "geopolitical tensions from late February, compounded by the seasonal effects of "
    "Ramadan and the Eid al-Fitr holiday. Whilst the quarterly aggregate is robust, "
    "the monthly trajectory provides the more relevant indication of near-term market "
    "conditions."
)

SHARJAH_OVERVIEW_SUBTITLE = "Residential market intelligence, Q1 2026"


# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY (used by the Sources page and the PDF methodology section)
# ─────────────────────────────────────────────────────────────────────────────

def all_sources() -> list[dict]:
    """Return the three reports this dashboard is built from."""
    return list(REPORTS)


def source_index() -> list[dict]:
    """
    Flat list of (section, source citation) so the PDF methodology page and the
    dashboard Sources expander can enumerate provenance without any hard-coding.
    """
    return [
        ("Key stats",                     SAVILLS_Q1_2026["citation"]),
        ("Monthly dynamics",              SAVILLS_Q1_2026["citation"]),
        ("Transaction value",             SAVILLS_Q1_2026["citation"]),
        ("Transaction volume",            SAVILLS_Q1_2026["citation"]),
        ("Investment by nationality",     SAVILLS_Q1_2026["citation"]),
        ("Sales by property type",        SAVILLS_Q1_2026["citation"]),
        ("Top performing areas",          SAVILLS_Q1_2026["citation"]),
        ("Notable transactions",          SAVILLS_Q1_2026["citation"]),
        ("New project registrations",     SAVILLS_Q1_2026["citation"]),
        ("Regulatory — Escrow 37/2024",   SAVILLS_Q1_2026["citation"]),
        ("Regulatory — Freehold 30/2022", SAVILLS_Q1_2026["citation"]),
        ("Regulatory — Leasing Law 5/2024", MARKAZ_2024_25["citation"]),
        ("Regulatory — SRERD × UAE Pass", MARKAZ_2024["citation"]),
        ("Infrastructure",                SAVILLS_Q1_2026["citation"]),
        ("Near-term conditions",          SAVILLS_Q1_2026["citation"]),
        ("Underlying fundamentals",       SAVILLS_Q1_2026["citation"]),
        ("Outlook / Forward signals",     SAVILLS_Q1_2026["citation"]),
    ]
