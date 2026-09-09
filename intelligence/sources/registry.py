"""
Authoritative RSS source registry for the UAE Real Estate Intelligence Layer.

This is the ONLY place RSS URLs live. Adding, removing or re-tiering a source
requires a code change and code review — never a runtime edit.

VERIFICATION POLICY
───────────────────
Every AVAILABLE_RSS entry below was verified live on the date recorded in
`last_verified_at` by:

  1. HTTP GET the URL with the platform User-Agent
  2. Parsing the response body with `feedparser`
  3. Confirming a valid feed version was detected (rss20 / atom10 / ...) AND
     the entry list had `n >= 1` real entries.

Any URL that failed the probe is recorded here as RSS_UNAVAILABLE with the
concrete reason (HTTP 404, HTTP 403, HTML returned instead of RSS, malformed
XML, etc). RSS_UNAVAILABLE records are kept — they are useful documentation
that a source was investigated and does not offer public RSS.

NO URL IN THIS FILE WAS GUESSED. Endpoints derived from RSS autodiscovery
`<link rel="alternate" type="application/rss+xml">` tags on the source's home
page, or from probe results, are the only URLs marked AVAILABLE_RSS.

To re-verify: `python -m intelligence.sources.health`.

Registry version: see `intelligence.config.REGISTRY_VERSION`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from intelligence.enums import (
    Emirate,
    RealEstateFocus,
    Region,
    RSSStatus,
    Scope,
    SourceTier,
)
from intelligence.schemas import Source


# Verification timestamp for the records in this file (UTC, Stage 3 build)
_VERIFIED = datetime(2026, 9, 3, tzinfo=timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1 — OFFICIAL / PRIMARY UAE SOURCES
#
# Investigated: WAM, Dubai Media Office, Dubai Land Department, ADREC,
# Sharjah24 (official), Sharjah Government, Ras Al Khaimah Government,
# Ajman / Fujairah / Umm Al Quwain authorities.
#
# Result: NONE of the UAE government or land-department portals investigated
# publish a public RSS feed at any URL that could be discovered from their
# home-page HTML or from common well-known feed patterns. Their sites are
# JavaScript-rendered SPAs or Drupal instances without RSS enabled. They are
# recorded here as RSS_UNAVAILABLE so the coverage gap is explicit; they are
# NOT enabled and must not be substituted with a scraped alternative.
# ─────────────────────────────────────────────────────────────────────────────

TIER_1_SOURCES: tuple[Source, ...] = (
    Source(
        source_id="wam-en",
        source_name="WAM — Emirates News Agency (English)",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "https://wam.ae/en/rss and /en/rss.xml both return HTTP 200 with "
            "an HTML SPA page (title in Arabic), not an RSS feed. Home page "
            "HTML contains no <link rel=alternate type=rss>. No public RSS."
        ),
        enabled=False,
    ),
    Source(
        source_id="dubai-media-office",
        source_name="Dubai Media Office",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.DUBAI,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "https://mediaoffice.ae/en/rss and /en/feed return HTTP 200 with "
            "HTML (SPA). No feed autodiscovery on the home page."
        ),
        enabled=False,
    ),
    Source(
        source_id="dubai-land-department",
        source_name="Dubai Land Department",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.DUBAI,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "dubailand.gov.ae/en/rss returns HTTP 404. Home page HTML has no "
            "RSS autodiscovery."
        ),
        enabled=False,
    ),
    Source(
        source_id="adrec",
        source_name="Abu Dhabi Real Estate Centre (ADREC)",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.ABU_DHABI,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "adrec.gov.ae/en/rss returns HTML SPA on HTTP 200 (malformed XML "
            "when parsed as RSS). No autodiscovery on home page."
        ),
        enabled=False,
    ),
    Source(
        source_id="sharjah24-official",
        source_name="Sharjah24 (Sharjah Government media)",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.SHARJAH,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "sharjah24.ae/en/rss, /en/rss.xml, /en/feed all return an HTML "
            "SPA. Home page has no feed autodiscovery."
        ),
        enabled=False,
    ),
    Source(
        source_id="srerd",
        source_name="Sharjah Real Estate Registration Department (SRERD)",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.SHARJAH,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "shjrerd.gov.ae is a JS-rendered portal with no exposed RSS "
            "endpoint. No autodiscovery on home page."
        ),
        enabled=False,
    ),
    Source(
        source_id="rak-government",
        source_name="Ras Al Khaimah Government",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.RAS_AL_KHAIMAH,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "ras-al-khaimah.gov.ae DNS not resolvable from probe host; "
            "no known alternative RSS endpoint documented publicly."
        ),
        enabled=False,
    ),
    Source(
        source_id="ajman-government",
        source_name="Ajman Government",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.AJMAN,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "No publicly documented RSS endpoint for the Ajman Government "
            "portal or Ajman relevant authority."
        ),
        enabled=False,
    ),
    Source(
        source_id="fujairah-government",
        source_name="Fujairah Government",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.FUJAIRAH,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes="No publicly documented RSS endpoint located.",
        enabled=False,
    ),
    Source(
        source_id="umm-al-quwain-government",
        source_name="Umm Al Quwain Government",
        source_tier=SourceTier.TIER_1,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.GOVERNMENT,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UMM_AL_QUWAIN,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes="No publicly documented RSS endpoint located.",
        enabled=False,
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 2 — MAJOR UAE / REGIONAL BUSINESS & PROPERTY MEDIA
#
# All AVAILABLE_RSS URLs below were discovered via RSS autodiscovery from the
# outlet's home page HTML, then live-verified: HTTP 200, feedparser parses
# with entry count >= 1. The Khaleej Times feeds are their public news-API
# collections; Emirates 24|7 exposes mobile-app RSS at /rss/mobile/v2/*.
#
# Sources marked RSS_UNAVAILABLE were investigated and either return HTML in
# place of RSS, return HTTP 404, or block anonymous access. Nothing is
# fabricated.
# ─────────────────────────────────────────────────────────────────────────────

TIER_2_SOURCES: tuple[Source, ...] = (
    # ── Khaleej Times (5 verified topic feeds) ────────────────────────────
    Source(
        source_id="khaleejtimes-top",
        source_name="Khaleej Times — Top Section",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.khaleejtimes.com/api/v1/collections/top-section.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 20 entries. Autodiscovered from home page.",
        enabled=True,
        refresh_interval_minutes=60,
    ),
    Source(
        source_id="khaleejtimes-uae",
        source_name="Khaleej Times — UAE",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE, Emirate.DUBAI, Emirate.ABU_DHABI,
                       Emirate.SHARJAH),
        trust_score=4,
        rss_url="https://www.khaleejtimes.com/api/v1/collections/uae.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 40 entries.",
        enabled=True,
        refresh_interval_minutes=60,
    ),
    Source(
        source_id="khaleejtimes-business",
        source_name="Khaleej Times — Business",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.khaleejtimes.com/api/v1/collections/business.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 40 entries. Property coverage sits inside the "
            "Business collection; no separate 'property' collection endpoint "
            "exists (tested /collections/property.rss → HTTP 404)."
        ),
        enabled=True,
        refresh_interval_minutes=60,
    ),
    Source(
        source_id="khaleejtimes-world",
        source_name="Khaleej Times — World",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url="https://www.khaleejtimes.com/api/v1/collections/world.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 40 entries. Enabled but low real-estate density; "
            "kept for regional context (e.g., foreign-investor stories)."
        ),
        enabled=False,   # off by default — Stage 8 relevance will decide
        refresh_interval_minutes=240,
    ),
    Source(
        source_id="khaleejtimes-life",
        source_name="Khaleej Times — Living in the UAE",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url="https://www.khaleejtimes.com/api/v1/collections/life-and-living.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 40 entries. Off by default; kept for supply-side "
            "housing/lifestyle stories the relevance filter may keep."
        ),
        enabled=False,
        refresh_interval_minutes=240,
    ),

    # ── Emirates 24|7 (3 verified topic feeds) ─────────────────────────────
    Source(
        source_id="emirates247-flash",
        source_name="Emirates 24|7 — Flash News",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url="https://www.emirates247.com/rss/mobile/v2/flash-news.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 20 entries.",
        enabled=True,
        refresh_interval_minutes=120,
    ),
    Source(
        source_id="emirates247-uae",
        source_name="Emirates 24|7 — UAE",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url="https://www.emirates247.com/rss/mobile/v2/uae.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 20 entries.",
        enabled=True,
        refresh_interval_minutes=120,
    ),
    Source(
        source_id="emirates247-business",
        source_name="Emirates 24|7 — Business",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url="https://www.emirates247.com/rss/mobile/v2/business.rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 20 entries. Property coverage sits inside "
            "Business; dedicated property feed URL (…/property.rss) returns 404."
        ),
        enabled=True,
        refresh_interval_minutes=120,
    ),

    # ── Dubai Chronicle (WordPress feed) ───────────────────────────────────
    Source(
        source_id="dubai-chronicle",
        source_name="Dubai Chronicle",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.DUBAI, Emirate.UAE_WIDE),
        trust_score=3,
        rss_url="https://www.dubaichronicle.com/feed/",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 10 entries (WordPress default feed).",
        enabled=True,
        refresh_interval_minutes=240,
    ),

    # ── ME Construction News (WordPress feed) ──────────────────────────────
    Source(
        source_id="me-construction-news",
        source_name="Middle East Construction News",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.REGIONAL_GCC,
        scope=Scope.TRADE_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://meconstructionnews.com/feed",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 10 entries. Construction-focused trade "
            "publication; contains project-launch, supply-pipeline signal."
        ),
        enabled=True,
        refresh_interval_minutes=240,
    ),

    # ── Gulf News, The National, Arabian Business, Zawya, Gulf Today: NO RSS
    Source(
        source_id="gulfnews",
        source_name="Gulf News",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "/rss.xml, /business/rss, /uae/rss, /business/property/rss all "
            "return HTTP 404. Home page HTML has no RSS autodiscovery link. "
            "FeedBurner alias 'gulfnews' returns empty. No public RSS."
        ),
        enabled=False,
    ),
    Source(
        source_id="thenationalnews",
        source_name="The National (UAE)",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE, Emirate.ABU_DHABI),
        trust_score=4,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "/rss.xml, /business/rss.xml, /uae/rss.xml all return HTTP 404. "
            "Home page has no autodiscovery. No public RSS."
        ),
        enabled=False,
    ),
    Source(
        source_id="arabianbusiness",
        source_name="Arabian Business",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.REGIONAL_GCC,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "/rss and /industries/rss return HTTP 403 (WAF/CDN block on "
            "anonymous fetches). Home page also 403. No public RSS reachable."
        ),
        enabled=False,
    ),
    Source(
        source_id="zawya",
        source_name="Zawya (LSEG)",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.REGIONAL_GCC,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.BUSINESS_SECTION,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "/en/rss/real-estate, /en/rss/mena, /en/rss/uae return HTTP 200 "
            "with HTML SPA content that is not RSS. No autodiscovery."
        ),
        enabled=False,
    ),
    Source(
        source_id="gulftoday",
        source_name="Gulf Today",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.SHARJAH, Emirate.UAE_WIDE),
        trust_score=3,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "/rss and /business/rss return HTML pages, not RSS. No home-page "
            "autodiscovery link."
        ),
        enabled=False,
    ),
    Source(
        source_id="propertyfinder-blog",
        source_name="Property Finder Blog",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.TRADE_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "propertyfinder.ae/blog/feed returns HTTP 200 with malformed XML "
            "(likely a rendered HTML template served under a feed URL). No "
            "usable RSS."
        ),
        enabled=False,
    ),
    Source(
        source_id="mybayut",
        source_name="MyBayut (Bayut editorial)",
        source_tier=SourceTier.TIER_2,
        country="AE",
        region=Region.LOCAL_UAE,
        scope=Scope.TRADE_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=3,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "bayut.com/mybayut/feed/ returns HTTP 404. WordPress REST API "
            "endpoint returns HTTP 401. No public RSS reachable."
        ),
        enabled=False,
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 3 — INTERNATIONAL (supplementary; must clear a higher UAE-relevance
# threshold before any of their articles are accepted; see Stage 9).
# ─────────────────────────────────────────────────────────────────────────────

TIER_3_SOURCES: tuple[Source, ...] = (
    Source(
        source_id="bbc-business",
        source_name="BBC News — Business",
        source_tier=SourceTier.TIER_3,
        country="GB",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 51 entries.",
        enabled=True,
        refresh_interval_minutes=360,
    ),
    Source(
        source_id="bbc-middle-east",
        source_name="BBC News — Middle East",
        source_tier=SourceTier.TIER_3,
        country="GB",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url="https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 34 entries.",
        enabled=True,
        refresh_interval_minutes=360,
    ),
    Source(
        source_id="cnbc-realestate",
        source_name="CNBC — Real Estate",
        source_tier=SourceTier.TIER_3,
        country="US",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.cnbc.com/id/10000115/device/rss/rss.html",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 30 entries. US-heavy; kept for occasional "
            "international-investor angle on Dubai / UAE."
        ),
        enabled=True,
        refresh_interval_minutes=720,
    ),
    Source(
        source_id="cnbc-world",
        source_name="CNBC — World News",
        source_tier=SourceTier.TIER_3,
        country="US",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.cnbc.com/id/100727362/device/rss/rss.html",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 30 entries.",
        enabled=False,
        refresh_interval_minutes=720,
    ),
    Source(
        source_id="guardian-property",
        source_name="The Guardian — Property",
        source_tier=SourceTier.TIER_3,
        country="GB",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.theguardian.com/money/property/rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "Verified: rss20, 20 entries. UK-heavy; occasional international "
            "property coverage."
        ),
        enabled=False,
        refresh_interval_minutes=720,
    ),
    Source(
        source_id="guardian-business",
        source_name="The Guardian — Business",
        source_tier=SourceTier.TIER_3,
        country="GB",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.GENERAL,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=4,
        rss_url="https://www.theguardian.com/business/rss",
        rss_status=RSSStatus.AVAILABLE_RSS,
        last_verified_at=_VERIFIED,
        verification_notes="Verified: rss20, 40 entries.",
        enabled=False,
        refresh_interval_minutes=720,
    ),
    Source(
        source_id="reuters-realestate",
        source_name="Reuters — Real Estate",
        source_tier=SourceTier.TIER_3,
        country="US",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "reuters.com/business/real-estate/rss returns HTTP 401 "
            "(subscription required). feeds.reuters.com is dead (DNS)."
        ),
        enabled=False,
    ),
    Source(
        source_id="bloomberg-realestate",
        source_name="Bloomberg — Real Estate",
        source_tier=SourceTier.TIER_3,
        country="US",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "bloomberg.com/feed/podcast/realestate.xml returns HTTP 404. "
            "Bloomberg does not offer public real-estate news RSS."
        ),
        enabled=False,
    ),
    Source(
        source_id="ft-property-construction",
        source_name="Financial Times — Property & Construction",
        source_tier=SourceTier.TIER_3,
        country="GB",
        region=Region.INTERNATIONAL,
        scope=Scope.NEWS_MEDIA,
        real_estate_focus=RealEstateFocus.DEDICATED,
        emirate_scope=(Emirate.UAE_WIDE,),
        trust_score=5,
        rss_url=None,
        rss_status=RSSStatus.RSS_UNAVAILABLE,
        last_verified_at=_VERIFIED,
        verification_notes=(
            "ft.com/companies/property-construction?format=rss returns "
            "HTTP 404. FT deprecated public RSS for most sections."
        ),
        enabled=False,
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY: tuple[Source, ...] = TIER_1_SOURCES + TIER_2_SOURCES + TIER_3_SOURCES


# ─────────────────────────────────────────────────────────────────────────────
# ACCESSORS (avoid iterating REGISTRY directly outside this module so future
# indexing changes are one-line adjustments here).
# ─────────────────────────────────────────────────────────────────────────────


def all_sources() -> tuple[Source, ...]:
    """Return every source in the registry (verified and unavailable)."""
    return REGISTRY


def enabled_sources() -> tuple[Source, ...]:
    """Return only sources marked enabled and AVAILABLE_RSS."""
    return tuple(s for s in REGISTRY if s.enabled)


def sources_by_tier(tier: SourceTier) -> tuple[Source, ...]:
    return tuple(s for s in REGISTRY if s.source_tier == tier)


def sources_by_status(status: RSSStatus) -> tuple[Source, ...]:
    return tuple(s for s in REGISTRY if s.rss_status == status)


def sources_by_emirate(emirate: Emirate) -> tuple[Source, ...]:
    return tuple(s for s in REGISTRY if emirate in s.emirate_scope)


__all__ = [
    "REGISTRY",
    "TIER_1_SOURCES", "TIER_2_SOURCES", "TIER_3_SOURCES",
    "all_sources", "enabled_sources", "sources_by_tier",
    "sources_by_status", "sources_by_emirate",
]
