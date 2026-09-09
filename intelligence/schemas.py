"""
Pydantic v2 schemas for the intelligence layer.

Stage 3 defines only the schemas needed by the source registry:

    Source            — one entry in the registry
    ProbeResult       — output of the RSS health probe

Later stages add: RelevanceOutput, LocationOutput, EntitiesOutput,
EventOutput, MarketObservationOutput, IntentOutput, EvidencePackage,
AnswerOutput — all in this same file so schemas are one source of truth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from intelligence.enums import (
    Emirate,
    RealEstateFocus,
    Region,
    RSSStatus,
    Scope,
    SourceTier,
)


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE — the atomic entry in the RSS source registry
# ─────────────────────────────────────────────────────────────────────────────


class Source(BaseModel):
    """
    One RSS source. Every field is required unless documented otherwise.

    A record is only allowed to have `enabled = True` when
    `rss_status = AVAILABLE_RSS`. This is enforced by the model validator
    below, not by the caller — so a stale enable flag cannot slip through.

    `rss_url` is optional: some Tier-1 official sources are known but do not
    publish RSS. Those records exist so the coverage report is complete; they
    are stored with `rss_url = None` and `rss_status = RSS_UNAVAILABLE`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    source_id: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$",
        description="Slug-form unique id, e.g., 'khaleejtimes-business'",
    )
    source_name: str = Field(min_length=2, max_length=128)

    # Editorial metadata
    source_tier: SourceTier
    country: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="ISO 3166-1 alpha-2, uppercase",
    )
    region: Region
    scope: Scope
    real_estate_focus: RealEstateFocus
    emirate_scope: tuple[Emirate, ...] = Field(
        default_factory=tuple,
        description="Emirates the source *typically* covers. A hint only; "
                    "final classification is made from article content in "
                    "later stages.",
    )
    trust_score: int = Field(ge=1, le=5)

    # RSS
    rss_url: Optional[HttpUrl] = None
    rss_status: RSSStatus
    last_verified_at: Optional[datetime] = None
    verification_notes: str = ""

    # Runtime
    enabled: bool = False
    refresh_interval_minutes: int = Field(ge=15, le=1440, default=240)

    # ── Validators ──────────────────────────────────────────────────────────
    @field_validator("emirate_scope")
    @classmethod
    def _no_duplicate_emirates(cls, v: tuple[Emirate, ...]) -> tuple[Emirate, ...]:
        if len(v) != len(set(v)):
            raise ValueError("emirate_scope contains duplicates")
        return v

    @field_validator("verification_notes")
    @classmethod
    def _notes_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("verification_notes must be <= 500 chars")
        return v

    @model_validator(mode="after")
    def _enabled_only_if_available(self) -> "Source":
        if self.enabled and self.rss_status != RSSStatus.AVAILABLE_RSS:
            raise ValueError(
                f"source_id={self.source_id!r}: enabled=True requires "
                f"rss_status=AVAILABLE_RSS (got {self.rss_status.value})"
            )
        if self.enabled and self.rss_url is None:
            raise ValueError(
                f"source_id={self.source_id!r}: enabled=True requires rss_url"
            )
        return self

    @model_validator(mode="after")
    def _available_requires_url(self) -> "Source":
        if self.rss_status == RSSStatus.AVAILABLE_RSS and self.rss_url is None:
            raise ValueError(
                f"source_id={self.source_id!r}: rss_status=AVAILABLE_RSS "
                f"requires rss_url"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# PROBE RESULT — output of the RSS health probe
# ─────────────────────────────────────────────────────────────────────────────


class ProbeResult(BaseModel):
    """The verified outcome of live-fetching a candidate RSS URL."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    url: Optional[HttpUrl]
    status: RSSStatus
    http_code: Optional[int] = None
    n_entries: int = 0
    feed_version: str = ""       # e.g., "rss20", "atom10"
    feed_title: str = ""
    note: str = ""
    probed_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# RAW ARTICLE RECORD — the raw JSONL contract (Stage 5)
# ─────────────────────────────────────────────────────────────────────────────


class RawArticleRecord(BaseModel):
    """
    One JSONL line in ``data/intelligence/raw_articles/*.jsonl``.

    This model MUST match exactly what Stage 4's ``build_raw_article`` emits.
    Fields that Stage 4 does not populate today but that later stages may add
    (``clean_title``, ``clean_body``, and canonical ``title``/``body``/``url``/
    ``published_at`` synonyms) are declared optional so the same schema
    validates historical files after later stages start writing enriched
    records — without ever re-requiring a field that Stage 4 omits.

    Raw content is stored verbatim. The distinction between ``raw_*`` and
    ``clean_*`` is architecturally preserved: raw fields are never edited by
    cleaning, and clean fields never overwrite the raw record.
    """

    model_config = ConfigDict(extra="forbid")

    # ── Identity (deterministic in Stage 4) ─────────────────────────────
    article_id: str = Field(
        pattern=r"^[0-9a-f]{40}$",
        description="sha1(source_id::guid_or_fallback), 40 hex chars",
    )
    raw_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="sha256(title|link|published|body), 64 hex chars",
    )

    # ── Source (from the authoritative registry) ────────────────────────
    source_id: str = Field(
        min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$",
    )
    source_name: str = Field(min_length=1, max_length=128)
    rss_url: HttpUrl

    # ── Raw content (verbatim from feedparser; may be empty strings) ────
    raw_title: str
    raw_body: str
    raw_url: str
    raw_published_at: str

    # ── Transport ───────────────────────────────────────────────────────
    retrieved_at: datetime
    content_type: str

    # ── Full feedparser entry for future re-processing ──────────────────
    raw_payload: dict

    # ── Optional stage-later fields (never required in Stage 4/5) ───────
    clean_title: Optional[str] = None
    clean_body: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None

    @field_validator("content_type")
    @classmethod
    def _content_type_must_be_rss(cls, v: str) -> str:
        if v != "rss":
            raise ValueError(f"content_type must be 'rss' (got {v!r})")
        return v

    @field_validator("raw_payload")
    @classmethod
    def _payload_is_object(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("raw_payload must be a JSON object")
        return v


class CleanArticle(BaseModel):
    """Stage 6 text only; raw provenance is copied, never rewritten.

    A null publication time with date_parse_error=False means the calendar
    date parsed but its timezone was not established. True means missing,
    malformed or incomplete input. Neither case substitutes retrieval time.
    word_count counts body tokens containing a Unicode letter or number.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    article_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_id: str = Field(
        min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$",
    )
    source_name: str = Field(min_length=1, max_length=128)
    rss_url: HttpUrl
    retrieved_at: datetime
    content_type: Literal["rss"]
    clean_title: str
    clean_body: str
    normalized_published_at: Optional[datetime]
    detected_language: Literal["en", "ar", "mixed", "unknown"]
    word_count: int = Field(ge=0)
    date_parse_error: bool
    cleaning_version: str = Field(min_length=1, max_length=64)

    @field_validator("normalized_published_at")
    @classmethod
    def _publication_is_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None:
            if value.utcoffset() != timedelta(0):
                raise ValueError("normalized_published_at must be timezone-aware UTC")
            return value.astimezone(timezone.utc)
        return value

    @model_validator(mode="after")
    def _failed_date_is_null(self) -> "CleanArticle":
        if self.date_parse_error and self.normalized_published_at is not None:
            raise ValueError("date_parse_error requires a null publication time")
        return self


class RealEstateRelevanceResult(BaseModel):
    """Immutable Stage 8 decision for a versioned canonical membership context.

    Evidence contains rule identifiers/lexicon phrases, never article excerpts.
    evaluated_at is operational metadata supplied by the caller, not a feature.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    article_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cleaning_version: str = Field(min_length=1, max_length=64)
    dedup_version: str = Field(min_length=1, max_length=64)
    relevance_version: str = Field(min_length=1, max_length=64)
    context_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    relevance_score: int = Field(strict=True, ge=0, le=5)
    is_real_estate_relevant: bool = Field(strict=True)
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    matched_positive_signals: tuple[str, ...] = Field(max_length=24)
    matched_negative_signals: tuple[str, ...] = Field(max_length=24)
    decision_reason: str = Field(min_length=1, max_length=240)
    evaluated_at: datetime

    @field_validator("matched_positive_signals", "matched_negative_signals")
    @classmethod
    def _bounded_signals(cls, value):
        if any(not s or len(s) > 120 for s in value) or len(set(value)) != len(value):
            raise ValueError("Evidence must contain unique bounded rule signals")
        return value

    @model_validator(mode="after")
    def _consistent_decision(self):
        if self.is_real_estate_relevant != (self.relevance_score >= 3):
            raise ValueError("Stage 8 acceptance requires score >= 3")
        if self.evaluated_at.utcoffset() is None:
            raise ValueError("Evaluation timestamp must be timezone-aware")
        expected = "HIGH" if self.relevance_score in (0, 4, 5) else "MEDIUM" if self.relevance_score == 3 else "LOW"
        if self.confidence != expected:
            raise ValueError("Confidence must match the deterministic score mapping")
        return self


class UAERealEstateRelevanceResult(BaseModel):
    """Stage 9 evidence only, referencing the complete immutable Stage 8 key."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    article_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cleaning_version: str = Field(min_length=1, max_length=64)
    dedup_version: str = Field(min_length=1, max_length=64)
    relevance_version: str = Field(min_length=1, max_length=64)
    context_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    uae_relevance_version: str = Field(min_length=1, max_length=64)
    registry_version: str = Field(min_length=1, max_length=64)
    uae_relevance_score: int = Field(strict=True, ge=0, le=5)
    is_uae_real_estate_relevant: bool = Field(strict=True)
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    source_context: Literal["LOCAL_UAE", "INTERNATIONAL"]
    acceptance_threshold: int = Field(strict=True, ge=3, le=4)
    matched_uae_signals: tuple[str, ...] = Field(max_length=24)
    matched_exclusion_signals: tuple[str, ...] = Field(max_length=24)
    decision_reason: str = Field(min_length=1, max_length=240)
    evaluated_at: datetime

    @field_validator("matched_uae_signals", "matched_exclusion_signals")
    @classmethod
    def _bounded_uae_signals(cls, value):
        if any(not s or len(s) > 120 for s in value) or len(set(value)) != len(value):
            raise ValueError("Evidence must contain unique bounded rule signals")
        return value

    @model_validator(mode="after")
    def _consistent_uae_decision(self):
        threshold = 3 if self.source_context == "LOCAL_UAE" else 4
        if self.acceptance_threshold != threshold or self.is_uae_real_estate_relevant != (self.uae_relevance_score >= threshold):
            raise ValueError("UAE acceptance must match source policy and score")
        if self.evaluated_at.utcoffset() is None:
            raise ValueError("Evaluation timestamp must be timezone-aware")
        expected = "HIGH" if self.uae_relevance_score in (0,4,5) else "MEDIUM" if self.uae_relevance_score == 3 else "LOW"
        if self.confidence != expected:
            raise ValueError("Confidence must match deterministic score mapping")
        return self


# Stage 10 reuses the established Emirate enum for location_scope only.
from intelligence.enums import EntityType


class EntityAlias(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1, max_length=160)
    language: Literal["en", "ar", "und"] = "en"
    abbreviation: bool = False


class EntityDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-z][a-z0-9:_-]+$")
    canonical_name: str = Field(min_length=1, max_length=160)
    entity_type: EntityType
    aliases: tuple[EntityAlias, ...] = Field(min_length=1, max_length=32)
    parent_entity_id: str | None = None
    emirate: Emirate | None = None
    active: bool = True
    provenance: tuple[str, ...] = Field(min_length=1, max_length=8)


class EntityMention(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_id: str = Field(min_length=3, max_length=120)
    canonical_name: str = Field(min_length=1, max_length=160)
    entity_type: EntityType
    parent_entity_id: str | None = None
    matched_text: str = Field(min_length=1, max_length=160)
    normalized_alias: str = Field(min_length=1, max_length=160)
    source_field: Literal["TITLE", "BODY"]
    start_offset: int = Field(strict=True, ge=0)
    end_offset: int = Field(strict=True, gt=0)
    confidence: Literal["HIGH", "MEDIUM"]
    extraction_method: Literal["EXACT_ALIAS", "CONTEXT_ABBREVIATION"]

    @model_validator(mode="after")
    def _valid_span(self):
        if self.end_offset-self.start_offset != len(self.matched_text):
            raise ValueError("Mention offsets must describe the exact matched text")
        expected = "MEDIUM" if self.extraction_method == "CONTEXT_ABBREVIATION" else "HIGH"
        if self.confidence != expected:
            raise ValueError("Mention confidence must match extraction method")
        return self


class EntityExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    extraction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    article_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cleaning_version: str = Field(min_length=1, max_length=64)
    dedup_version: str = Field(min_length=1, max_length=64)
    relevance_version: str = Field(min_length=1, max_length=64)
    context_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    uae_relevance_version: str = Field(min_length=1, max_length=64)
    registry_version: str = Field(min_length=1, max_length=64)
    entity_extraction_version: str = Field(min_length=1, max_length=64)
    entity_registry_version: str = Field(min_length=1, max_length=64)
    location_scope: Emirate
    mentions: tuple[EntityMention, ...] = Field(max_length=256)
    entity_ids: tuple[str, ...] = Field(max_length=256)
    evaluated_at: datetime

    @model_validator(mode="after")
    def _consistent_entities(self):
        import hashlib
        import json
        key = [getattr(self,k) for k in ("article_id","raw_hash","cleaning_version","dedup_version",
               "relevance_version","context_id","uae_relevance_version","registry_version",
               "entity_extraction_version","entity_registry_version")]
        if self.extraction_id != hashlib.sha256(json.dumps(key,separators=(",", ":")).encode()).hexdigest():
            raise ValueError("Extraction identity must bind the complete versioned upstream key")
        if self.entity_ids != tuple(sorted({m.entity_id for m in self.mentions})):
            raise ValueError("Entity IDs must equal the unique sorted mentioned identities")
        ends = {}
        order = [(m.source_field != "TITLE",m.start_offset,m.end_offset,m.entity_id) for m in self.mentions]
        if order != sorted(order):
            raise ValueError("Mentions must be in deterministic field/span order")
        for m in self.mentions:
            if m.start_offset < ends.get(m.source_field,0):
                raise ValueError("Resolved mention spans cannot overlap")
            ends[m.source_field] = m.end_offset
        if self.evaluated_at.utcoffset() is None:
            raise ValueError("Evaluation time must be timezone-aware")
        return self


# Stage 11 instances reference their extraction result; lineage lives once there.
from intelligence.enums import EventType, EventDirection
from intelligence.events.identity import UPSTREAM_KEY, digest as event_digest, result_id as event_result_id, event_id as make_event_id


class EventEntityLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_id: str = Field(min_length=3, max_length=120)
    mention_index: int = Field(strict=True, ge=0, le=255)
    relationship: Literal["CLAUSE_CONTEXT"] = "CLAUSE_CONTEXT"


class RealEstateEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_result_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_type: EventType
    rule_id: str = Field(min_length=1, max_length=64)
    source_field: Literal["TITLE", "BODY"]
    matched_text: str = Field(min_length=1, max_length=640)
    start_offset: int = Field(strict=True, ge=0)
    end_offset: int = Field(strict=True, gt=0)
    confidence: Literal["HIGH", "MEDIUM"]
    direction: EventDirection = EventDirection.UNKNOWN
    entity_links: tuple[EventEntityLink, ...] = Field(max_length=32)

    @property
    def associated_entity_ids(self):
        return tuple(link.entity_id for link in self.entity_links)

    @model_validator(mode="after")
    def _event_contract(self):
        if self.end_offset-self.start_offset != len(self.matched_text):
            raise ValueError("Event span must describe exact evidence")
        if self.confidence != ("HIGH" if self.source_field == "TITLE" else "MEDIUM"):
            raise ValueError("Confidence must match field policy")
        if self.associated_entity_ids != tuple(sorted(set(self.associated_entity_ids))):
            raise ValueError("Entity links must be unique and sorted")
        expected = make_event_id(self.event_result_id,self.event_type.value,self.source_field,self.start_offset,
                                self.end_offset,self.rule_id,self.direction.value,self.matched_text,self.entity_links)
        if expected != self.event_id:
            raise ValueError("Event ID must bind versioned result and evidence")
        return self


class EventExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_result_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    extraction_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    article_id: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cleaning_version: str = Field(min_length=1, max_length=64)
    dedup_version: str = Field(min_length=1, max_length=64)
    relevance_version: str = Field(min_length=1, max_length=64)
    context_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    uae_relevance_version: str = Field(min_length=1, max_length=64)
    registry_version: str = Field(min_length=1, max_length=64)
    entity_extraction_version: str = Field(min_length=1, max_length=64)
    entity_registry_version: str = Field(min_length=1, max_length=64)
    event_extraction_version: str = Field(min_length=1, max_length=64)
    location_scope: Emirate
    events: tuple[RealEstateEvent, ...] = Field(max_length=128)
    evaluated_at: datetime

    @model_validator(mode="after")
    def _event_result_contract(self):
        if self.extraction_id != event_digest([getattr(self,k) for k in UPSTREAM_KEY]):
            raise ValueError("Stage 10 identity must preserve complete upstream key")
        if self.event_result_id != event_result_id(self.extraction_id,self.event_extraction_version):
            raise ValueError("Result ID must bind Stage 10 and event version")
        order = [(e.source_field != "TITLE",e.start_offset,e.end_offset,e.event_type.value,e.event_id) for e in self.events]
        if order != sorted(order) or len({e.event_id for e in self.events}) != len(self.events):
            raise ValueError("Events must be unique and deterministically ordered")
        if any(e.event_result_id != self.event_result_id for e in self.events):
            raise ValueError("Event belongs to a different extraction")
        if self.evaluated_at.utcoffset() is None:
            raise ValueError("Evaluation time must be timezone aware")
        return self


__all__ = ["EventEntityLink", "RealEstateEvent", "EventExtractionResult", "Source", "ProbeResult", "RawArticleRecord", "CleanArticle", "RealEstateRelevanceResult", "UAERealEstateRelevanceResult", "EntityAlias", "EntityDefinition", "EntityMention", "EntityExtractionResult"]


from decimal import Decimal
import re
from pydantic import field_validator, field_serializer
from intelligence.enums import (MetricType, MetricUnit, Currency, NumberScale, PeriodBasis,
                                PropertyType, ObservationNature, ValueQualifier)
from intelligence.metrics.identity import decimal_text, observation_id, result_id as metric_result_id


class MarketObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    observation_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    metric_result_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    metric: MetricType
    value: Decimal
    reported_value: Decimal
    reported_value_text: str = Field(min_length=1, max_length=80)
    scale: NumberScale
    currency: Currency | None
    unit: MetricUnit
    period_basis: PeriodBasis = PeriodBasis.UNKNOWN
    reported_period_text: str | None = Field(default=None, max_length=80)
    property_type: PropertyType = PropertyType.UNKNOWN
    nature: ObservationNature = ObservationNature.OBSERVED
    qualifier: ValueQualifier = ValueQualifier.EXACT
    statistic: Literal['UNSPECIFIED','AVERAGE','MEDIAN'] = 'UNSPECIFIED'
    direction: EventDirection = EventDirection.UNKNOWN
    rule_id: str = Field(min_length=1, max_length=64)
    source_field: Literal['TITLE','BODY']
    start_offset: int = Field(strict=True, ge=0)
    end_offset: int = Field(strict=True, gt=0)
    numeric_start: int = Field(strict=True, ge=0)
    numeric_end: int = Field(strict=True, gt=0)
    matched_text: str = Field(min_length=1, max_length=640)
    confidence: Literal['HIGH','MEDIUM']
    entity_links: tuple[EventEntityLink, ...] = Field(max_length=32)
    associated_event_ids: tuple[str, ...] = Field(max_length=128)

    @property
    def associated_entity_ids(self):
        return tuple(link.entity_id for link in self.entity_links)

    @field_validator('value','reported_value',mode='before')
    @classmethod
    def _decimal_only(cls,value):
        if not isinstance(value,(Decimal,str)):
            raise ValueError('Decimal or exact decimal text required; floats forbidden')
        return value

    @field_serializer('value','reported_value')
    def _decimal_text(self,value):
        return decimal_text(value)

    @model_validator(mode='after')
    def _contract(self):
        if not self.value.is_finite() or not self.reported_value.is_finite():
            raise ValueError('Finite values required')
        if not (self.start_offset <= self.numeric_start < self.numeric_end <= self.end_offset):
            raise ValueError('Numeric evidence must be inside clause evidence')
        if self.end_offset-self.start_offset != len(self.matched_text):
            raise ValueError('Invalid evidence span')
        if self.matched_text[self.numeric_start-self.start_offset:self.numeric_end-self.start_offset] != self.reported_value_text:
            raise ValueError('Numeric evidence mismatch')
        if self.confidence != ('HIGH' if self.source_field=='TITLE' else 'MEDIUM'):
            raise ValueError('Invalid confidence')
        if self.associated_entity_ids != tuple(sorted(set(self.associated_entity_ids))):
            raise ValueError('Entity links must be unique and ordered')
        if self.associated_event_ids != tuple(sorted(set(self.associated_event_ids))) or any(not re.fullmatch('[0-9a-f]{64}',v) for v in self.associated_event_ids):
            raise ValueError('Invalid event links')
        units = {'SALE_PRICE_PER_SQFT':'CURRENCY_PER_SQFT','SALE_PRICE_PER_SQM':'CURRENCY_PER_SQM',
                 'RENTAL_YIELD':'PERCENT','PRICE_CHANGE_PCT':'PERCENT','RENT_CHANGE_PCT':'PERCENT','TRANSACTION_VOLUME':'TRANSACTIONS'}
        if self.unit.value != units.get(self.metric.value,'CURRENCY_AMOUNT'):
            raise ValueError('Metric and unit disagree')
        if (self.currency is not None) != self.unit.value.startswith('CURRENCY'):
            raise ValueError('Currency required only for money')
        change = self.metric in (MetricType.PRICE_CHANGE_PCT,MetricType.RENT_CHANGE_PCT)
        if not change and (self.value < 0 or self.direction != EventDirection.UNKNOWN):
            raise ValueError('Invalid unsigned level or count')
        if change and self.direction.value != ('INCREASE' if self.value>0 else 'DECREASE' if self.value<0 else 'STABLE'):
            raise ValueError('Change sign disagrees with direction')
        if self.metric==MetricType.TRANSACTION_VOLUME and self.value!=self.value.to_integral_value():
            raise ValueError('Transaction count must be integral')
        from intelligence.metrics.numbers import NUMBER, number_at
        match = NUMBER.match(self.reported_value_text)
        if match is None:
            raise ValueError('Invalid reported numeric text')
        reported, scaled, scale, end = number_at(self.reported_value_text, match)
        if end != len(self.reported_value_text) or reported != self.reported_value or scale != self.scale.value:
            raise ValueError('Reported numeric value or scale mismatch')
        expected = scaled.copy_negate() if self.direction == EventDirection.DECREASE and scaled >= 0 else scaled
        if expected != self.value:
            raise ValueError('Value must equal exact reported scale and direction')
        if self.reported_period_text and self.reported_period_text not in self.matched_text:
            raise ValueError('Reported period must preserve evidence text')
        if self.metric == MetricType.ANNUAL_RENT and self.period_basis != PeriodBasis.ANNUAL:
            raise ValueError('Annual rent requires annual period')
        if self.metric == MetricType.MONTHLY_RENT and self.period_basis != PeriodBasis.MONTHLY:
            raise ValueError('Monthly rent requires monthly period')
        if self.metric == MetricType.AVERAGE_SALE_PRICE and self.statistic != 'AVERAGE':
            raise ValueError('Average metric requires average statistic')
        if self.metric == MetricType.MEDIAN_SALE_PRICE and self.statistic != 'MEDIAN':
            raise ValueError('Median metric requires median statistic')
        if observation_id(self.model_dump(mode='json')) != self.observation_id:
            raise ValueError('Observation identity mismatch')
        return self


class MetricExtractionResult(EventExtractionResult):
    """Complete upstream lineage; inherited event tuple must be empty (stored upstream)."""
    metric_result_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    metric_extraction_version: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=120)
    observations: tuple[MarketObservation, ...] = Field(max_length=256)

    @model_validator(mode='after')
    def _metric_contract(self):
        if self.events:
            raise ValueError('Events remain exclusively in Stage 11 storage')
        if self.metric_result_id != metric_result_id(self.event_result_id,self.metric_extraction_version):
            raise ValueError('Metric result identity mismatch')
        order = [(o.source_field!='TITLE',o.start_offset,o.numeric_start,o.metric.value,o.observation_id) for o in self.observations]
        if order!=sorted(order) or len({o.observation_id for o in self.observations})!=len(order):
            raise ValueError('Observations must be unique and ordered')
        if any(o.metric_result_id!=self.metric_result_id for o in self.observations):
            raise ValueError('Observation belongs to another result')
        return self


__all__ += ['MarketObservation','MetricExtractionResult']
