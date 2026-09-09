"""
Controlled vocabularies for the intelligence layer.

Every enum defined here is a hard boundary. LLM outputs that fall outside
these values are rejected at the Pydantic layer, never silently coerced.

Stage 3 uses only the subset needed by the source registry. The remaining
enums (EventType, MetricKind, Intent, ActionName, etc.) are added by
subsequent stages so this file stays a single source of truth.
"""

from __future__ import annotations

from enum import Enum


class Emirate(str, Enum):
    """The seven UAE emirates plus non-emirate scopes."""

    DUBAI = "DUBAI"
    ABU_DHABI = "ABU_DHABI"
    SHARJAH = "SHARJAH"
    AJMAN = "AJMAN"
    RAS_AL_KHAIMAH = "RAS_AL_KHAIMAH"
    FUJAIRAH = "FUJAIRAH"
    UMM_AL_QUWAIN = "UMM_AL_QUWAIN"
    # Non-emirate scopes
    UAE_WIDE = "UAE_WIDE"
    MULTI_EMIRATE = "MULTI_EMIRATE"
    UNKNOWN = "UNKNOWN"


class SourceTier(str, Enum):
    """Editorial priority of a source."""

    TIER_1 = "TIER_1"   # Official / primary (WAM, government, land departments)
    TIER_2 = "TIER_2"   # Major UAE / regional business & property media
    TIER_3 = "TIER_3"   # International, supplementary


class Region(str, Enum):
    """Geographic origin of the source, used for policy (relevance thresholds)."""

    LOCAL_UAE = "LOCAL_UAE"
    REGIONAL_GCC = "REGIONAL_GCC"
    INTERNATIONAL = "INTERNATIONAL"


class Scope(str, Enum):
    """Nature of the publisher."""

    GOVERNMENT = "GOVERNMENT"
    NEWS_MEDIA = "NEWS_MEDIA"
    TRADE_MEDIA = "TRADE_MEDIA"
    RESEARCH_HOUSE = "RESEARCH_HOUSE"


class RealEstateFocus(str, Enum):
    """How central real estate is to the source's coverage."""

    DEDICATED = "DEDICATED"          # Real-estate publication
    BUSINESS_SECTION = "BUSINESS_SECTION"  # General media with a business/property section
    GENERAL = "GENERAL"              # General media, occasional property coverage


class RSSStatus(str, Enum):
    """
    Verification state of the RSS feed.

    AVAILABLE_RSS
        The URL was probed, returned a valid RSS/Atom feed, and at least one
        entry was parsed successfully. Only feeds in this state may be
        `enabled = True` in the registry.

    RSS_UNAVAILABLE
        The URL was probed and definitively does not serve RSS: HTTP 404, HTTP
        403, HTTP 401, a well-formed HTML page returned in place of a feed, or
        a feed that parsed with zero entries. This is a *definite negative* —
        it does not mean the source has no RSS anywhere, only that the URL
        recorded in the registry does not.

    RSS_UNVERIFIED
        The URL could not be probed reliably: network timeout, DNS failure, or
        an environment issue on the probe host (e.g., SSL trust store). This
        is *not* a negative verdict — it is an "unknown" that should be
        re-probed from a different network before the source is enabled.
    """

    AVAILABLE_RSS = "AVAILABLE_RSS"
    RSS_UNAVAILABLE = "RSS_UNAVAILABLE"
    RSS_UNVERIFIED = "RSS_UNVERIFIED"


class EntityType(str, Enum):
    """Stage 10 entity types; separate from article-level Emirate scope."""
    COUNTRY = "COUNTRY"
    EMIRATE = "EMIRATE"
    CITY = "CITY"
    AREA = "AREA"
    COMMUNITY = "COMMUNITY"
    PROJECT = "PROJECT"
    BUILDING = "BUILDING"
    DEVELOPER = "DEVELOPER"


class EventType(str, Enum):
    """Stage 11 event taxonomy; numeric observations remain a later contract."""
    PRICE_CHANGE = "PRICE_CHANGE"
    RENT_CHANGE = "RENT_CHANGE"
    TRANSACTION_VALUE = "TRANSACTION_VALUE"
    TRANSACTION_VOLUME = "TRANSACTION_VOLUME"
    SALES_ACTIVITY = "SALES_ACTIVITY"
    MORTGAGE_ACTIVITY = "MORTGAGE_ACTIVITY"
    OFF_PLAN_ACTIVITY = "OFF_PLAN_ACTIVITY"
    READY_PROPERTY_ACTIVITY = "READY_PROPERTY_ACTIVITY"
    NEW_PROJECT = "NEW_PROJECT"
    PROJECT_LAUNCH = "PROJECT_LAUNCH"
    PROJECT_COMPLETION = "PROJECT_COMPLETION"
    NEW_SUPPLY = "NEW_SUPPLY"
    SUPPLY_PIPELINE = "SUPPLY_PIPELINE"
    DEVELOPER_ACTIVITY = "DEVELOPER_ACTIVITY"
    INVESTOR_ACTIVITY = "INVESTOR_ACTIVITY"
    FOREIGN_INVESTMENT = "FOREIGN_INVESTMENT"
    REGULATION = "REGULATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DEMAND_CHANGE = "DEMAND_CHANGE"
    MARKET_SENTIMENT = "MARKET_SENTIMENT"
    MARKET_OUTLOOK = "MARKET_OUTLOOK"
    RENTAL_ACTIVITY = "RENTAL_ACTIVITY"


class EventDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


__all__ = [
    "EventType", "EventDirection",
    "EntityType",
    "Emirate",
    "SourceTier",
    "Region",
    "Scope",
    "RealEstateFocus",
    "RSSStatus",
]


class MetricType(str, Enum):
    SALE_PRICE = 'SALE_PRICE'
    AVERAGE_SALE_PRICE = 'AVERAGE_SALE_PRICE'
    MEDIAN_SALE_PRICE = 'MEDIAN_SALE_PRICE'
    SALE_PRICE_PER_SQFT = 'SALE_PRICE_PER_SQFT'
    SALE_PRICE_PER_SQM = 'SALE_PRICE_PER_SQM'
    RENTAL_PRICE = 'RENTAL_PRICE'
    ANNUAL_RENT = 'ANNUAL_RENT'
    MONTHLY_RENT = 'MONTHLY_RENT'
    RENTAL_YIELD = 'RENTAL_YIELD'
    PRICE_CHANGE_PCT = 'PRICE_CHANGE_PCT'
    RENT_CHANGE_PCT = 'RENT_CHANGE_PCT'
    TRANSACTION_VALUE = 'TRANSACTION_VALUE'
    TRANSACTION_VOLUME = 'TRANSACTION_VOLUME'


class MetricUnit(str, Enum):
    CURRENCY_AMOUNT = 'CURRENCY_AMOUNT'
    CURRENCY_PER_SQFT = 'CURRENCY_PER_SQFT'
    CURRENCY_PER_SQM = 'CURRENCY_PER_SQM'
    PERCENT = 'PERCENT'
    TRANSACTIONS = 'TRANSACTIONS'


class Currency(str, Enum):
    AED = 'AED'
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'


class NumberScale(str, Enum):
    ONE = 'ONE'
    THOUSAND = 'THOUSAND'
    MILLION = 'MILLION'
    BILLION = 'BILLION'


class PeriodBasis(str, Enum):
    MOM = 'MOM'
    QOQ = 'QOQ'
    YOY = 'YOY'
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    ANNUAL = 'ANNUAL'
    CURRENT = 'CURRENT'
    UNKNOWN = 'UNKNOWN'


class PropertyType(str, Enum):
    APARTMENT = 'APARTMENT'
    VILLA = 'VILLA'
    TOWNHOUSE = 'TOWNHOUSE'
    LAND = 'LAND'
    COMMERCIAL = 'COMMERCIAL'
    OFFICE = 'OFFICE'
    RETAIL = 'RETAIL'
    WAREHOUSE = 'WAREHOUSE'
    RESIDENTIAL = 'RESIDENTIAL'
    COMMERCIAL_PROPERTY = 'COMMERCIAL_PROPERTY'
    UNKNOWN = 'UNKNOWN'


class ObservationNature(str, Enum):
    OBSERVED = 'OBSERVED'
    SOURCE_REPORTED_FORECAST = 'SOURCE_REPORTED_FORECAST'


class ValueQualifier(str, Enum):
    EXACT = 'EXACT'
    APPROXIMATE = 'APPROXIMATE'
    GREATER_THAN = 'GREATER_THAN'
    LESS_THAN = 'LESS_THAN'


__all__ += ['MetricType','MetricUnit','Currency','NumberScale','PeriodBasis','PropertyType',
            'ObservationNature','ValueQualifier']
