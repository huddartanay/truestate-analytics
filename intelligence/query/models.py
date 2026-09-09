"""Validated Stage 14 boundary contracts. No conversational answer field."""
from intelligence import config as cfg
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from intelligence.enums import Emirate, MetricType, PropertyType, EventType

class Model(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')

class Intent(str,Enum):
    CURRENT_NEWS='CURRENT_NEWS'
    MARKET_STATUS='MARKET_STATUS'
    PRICE_MOVEMENT='PRICE_MOVEMENT'
    RENTAL_MOVEMENT='RENTAL_MOVEMENT'
    TRANSACTION_TREND='TRANSACTION_TREND'
    TOP_INCREASE='TOP_INCREASE'
    TOP_DECREASE='TOP_DECREASE'
    EMIRATE_ANALYSIS='EMIRATE_ANALYSIS'
    AREA_ANALYSIS='AREA_ANALYSIS'
    PROJECT_NEWS='PROJECT_NEWS'
    REGULATION='REGULATION'
    INVESTOR_ACTIVITY='INVESTOR_ACTIVITY'
    SUPPLY='SUPPLY'
    DEMAND='DEMAND'
    OFF_PLAN='OFF_PLAN'
    MARKET_OUTLOOK='MARKET_OUTLOOK'
    INFRASTRUCTURE='INFRASTRUCTURE'
    LATEST_EVENTS='LATEST_EVENTS'
    PROPERTY_PRICE='PROPERTY_PRICE'
    RENTAL_PRICE='RENTAL_PRICE'
    TRANSACTION_VALUE='TRANSACTION_VALUE'
    TRANSACTION_VOLUME='TRANSACTION_VOLUME'
    COMPARE_EMIRATES='COMPARE_EMIRATES'
    COMPARE_AREAS='COMPARE_AREAS'
    SOURCE_DETAILS='SOURCE_DETAILS'
    OUT_OF_SCOPE='OUT_OF_SCOPE'
    AMBIGUOUS='AMBIGUOUS'
    UNSUPPORTED='UNSUPPORTED'

class Status(str,Enum):
    AVAILABLE='AVAILABLE'
    PARTIAL='PARTIAL'
    NO_DATA='NO_DATA'
    OUT_OF_SCOPE='OUT_OF_SCOPE'
    AMBIGUOUS='AMBIGUOUS'
    UNSUPPORTED='UNSUPPORTED'
    NOT_COMPARABLE='NOT_COMPARABLE'

class PageContext(Model):
    page_id: str=Field(default='GLOBAL',min_length=1,max_length=80)
    page_type: Literal['GLOBAL','EMIRATE','AREA','PROJECT','DEVELOPER','OUTLOOK','DASHBOARD']='GLOBAL'
    emirate: Emirate | None=None
    city: str | None=Field(default=None,max_length=160)
    area: str | None=Field(default=None,max_length=160)
    community: str | None=Field(default=None,max_length=160)
    project: str | None=Field(default=None,max_length=160)
    building: str | None=Field(default=None,max_length=160)
    developer: str | None=Field(default=None,max_length=160)
    property_type: PropertyType | None=None
    active_filters: dict[str,str | tuple[str,...]]=Field(default_factory=dict,max_length=12)
    dashboard_section: str | None=Field(default=None,max_length=100)

    @field_validator('active_filters')
    @classmethod
    def bounded_filters(cls,value):
        if any(len(k)>80 or len(str(v))>500 for k,v in value.items()): raise ValueError('Bounded filters required')
        return value

class QueryRequest(Model):
    question: str=Field(min_length=1,max_length=1000)
    selected_question_id: str | None=Field(default=None,max_length=80)
    page_context: PageContext | None=None
    emirate: Emirate | None=None
    city: str | None=Field(default=None,max_length=160)
    area: str | None=Field(default=None,max_length=160)
    community: str | None=Field(default=None,max_length=160)
    project: str | None=Field(default=None,max_length=160)
    building: str | None=Field(default=None,max_length=160)
    developer: str | None=Field(default=None,max_length=160)
    property_type: PropertyType | None=None
    metric: MetricType | None=None
    time_expression: str | None=Field(default=None,max_length=80)
    comparison_targets: tuple[str,...]=Field(default=(),max_length=2)
    source_id: str | None=Field(default=None,pattern=r'^[a-z0-9][a-z0-9-]{1,63}$')
    limit: int=Field(default=10,ge=1,le=50,strict=True)
    as_of: datetime | None=None

    @field_validator('question')
    @classmethod
    def not_empty(cls,value):
        if not value.strip(): raise ValueError('Question cannot be blank')
        return value

    @field_validator('comparison_targets')
    @classmethod
    def bounded_targets(cls,value):
        if any(not v.strip() or len(v)>160 for v in value): raise ValueError('Bounded comparison targets required')
        return value

    @field_validator('as_of')
    @classmethod
    def aware(cls,value):
        if value is not None and value.utcoffset() is None: raise ValueError('as_of must be timezone aware')
        return value

class TimeFilter(Model):
    expression: str='LATEST'
    start: datetime | None=None
    end: datetime | None=None
    period: str | None=None
    @model_validator(mode='after')
    def valid_window(self):
        if bool(self.start)!=bool(self.end): raise ValueError('Complete time window required')
        if self.start and (self.start.utcoffset() is None or self.end.utcoffset() is None or self.start>=self.end): raise ValueError('Ordered aware time window required')
        return self

    # News/events filter publication time; observations/rankings use explicit
    # observation periods. Missing publication dates never gain invented dates.

class Filters(Model):
    emirate: Emirate=Emirate.UAE_WIDE
    entity_ids: tuple[str,...]=Field(default=(),max_length=4)
    property_type: PropertyType | None=None
    metric: MetricType | None=None
    source_id: str | None=Field(default=None,pattern=r'^[a-z0-9][a-z0-9-]{1,63}$')
    time: TimeFilter=Field(default_factory=TimeFilter)
    movement_basis: Literal['MOM','QOQ','YOY'] | None=None
    family: Literal['PRICE','RENT','TRANSACTION'] | None=None
    hierarchy: Literal['EMIRATE','AREA','COMMUNITY'] | None=None
    event_types: tuple[EventType,...]=Field(default=(),max_length=22)
    limit: int=Field(default=10,ge=1,le=50,strict=True)

    @field_validator('entity_ids')
    @classmethod
    def known_entities(cls,value):
        from intelligence.entities.registry import REGISTRY
        if any(e not in REGISTRY.entities for e in value): raise ValueError('Unknown entity identity')
        return value

class RouteDecision(Model):
    router_version: str=cfg.QUERY_ROUTER_VERSION
    scope: Literal['TRUESTATE_UAE_REAL_ESTATE_ONLY']='TRUESTATE_UAE_REAL_ESTATE_ONLY'
    scope_status: Literal['IN_SCOPE','OUT_OF_SCOPE','AMBIGUOUS','UNSUPPORTED']
    intent: Intent
    action_id: str | None=None
    filters: Filters=Field(default_factory=Filters)
    resolved_entities: tuple[str,...]=()
    comparison_targets: tuple[str,...]=Field(default=(),max_length=2)
    page_context_used: bool=False
    explicit_context_used: bool=False
    confidence: Literal['HIGH','MEDIUM','LOW']='HIGH'
    reason_code: str=Field(max_length=100)
    expected_output_type: str | None=None

    @model_validator(mode='after')
    def safe_route(self):
        if self.scope_status!='IN_SCOPE' and self.intent.value!=self.scope_status: raise ValueError('Stopped route intent must match status')
        if self.scope_status!='IN_SCOPE' and (self.action_id or self.expected_output_type): raise ValueError('Stopped routes cannot execute actions')
        if self.scope_status=='IN_SCOPE' and (not self.action_id or not self.expected_output_type): raise ValueError('Executable route requires action/output')
        return self

class Evidence(Model):
    reference_id: str=Field(min_length=1,max_length=100)
    build_id: str=Field(pattern=r'^[0-9a-f]{64}$')
    metric_result_id: str=Field(pattern=r'^[0-9a-f]{64}$')
    article_id: str=Field(pattern=r'^[0-9a-f]{40}$')
    raw_hash: str=Field(pattern=r'^[0-9a-f]{64}$')
    source_id: str
    source_name: str
    article_url: str | None=None
    rss_url: str
    published_at: datetime | None=None
    retrieved_at: datetime
    entity_ids: tuple[str,...]=()
    event_id: str | None=None
    observation_id: str | None=None
    movement_id: str | None=None
    ranking_id: str | None=None

class Record(Model):
    kind: Literal['NEWS','EVENT','OBSERVATION','MOVEMENT','RANKING','SOURCE']
    identity: str
    evidence_ids: tuple[str,...]=Field(min_length=1,max_length=2)
    title: str | None=None
    event_type: str | None=None
    metric: MetricType | None=None
    value: str | None=None
    unit: str | None=None
    currency: str | None=None
    property_type: PropertyType | None=None
    statistic: str | None=None
    nature: Literal['OBSERVED','SOURCE_REPORTED_FORECAST'] | None=None
    provenance: Literal['SOURCE_REPORTED','SYSTEM_CALCULATED'] | None=None
    period: str | None=None
    frequency: str | None=None
    movement_basis: str | None=None
    classification: str | None=None
    rank_number: int | None=Field(default=None,ge=1)
    position: int | None=Field(default=None,ge=1)
    group_id: str | None=None
    source_tier: str | None=None
    trust_metadata: tuple[str,...]=()
    exclusion_reason: str | None=None

    @model_validator(mode='after')
    def factual_contract(self):
        from decimal import Decimal, InvalidOperation
        if self.value is not None:
            try: finite=Decimal(self.value).is_finite()
            except InvalidOperation: raise ValueError('Exact decimal text required') from None
            if not finite: raise ValueError('Finite decimal required')
        if self.kind in ('OBSERVATION','MOVEMENT','RANKING'):
            if self.value is None or not Decimal(self.value).is_finite() or self.metric is None or self.provenance is None: raise ValueError('Numeric facts require metric, exact value and provenance')
        if self.kind in ('MOVEMENT','RANKING') and (self.provenance!='SYSTEM_CALCULATED' or len(self.evidence_ids)!=2): raise ValueError('Movement requires both observations')
        if self.kind=='RANKING' and (self.rank_number is None or self.position is None or not self.group_id): raise ValueError('Ranking requires original rank/group')
        return self

class Section(Model):
    name: str
    status: Status
    records: tuple[Record,...]=Field(default=(),max_length=100)

class ActionResult(Model):
    action_version: str=cfg.INTELLIGENCE_ACTION_VERSION
    action_id: str | None
    intent: Intent
    status: Status
    reason_code: str='STAGE13_EVIDENCE'
    output_type: str='ActionResult'
    filters_applied: Filters
    build_id: str | None=None
    as_of: datetime | None=None
    latest_available_at: datetime | None=None
    data_scope: Literal['TRUESTATE_UAE_REAL_ESTATE_ONLY']='TRUESTATE_UAE_REAL_ESTATE_ONLY'
    records: tuple[Record,...]=Field(default=(),max_length=100)
    sections: tuple[Section,...]=Field(default=(),max_length=8)
    evidence: tuple[Evidence,...]=Field(default=(),max_length=1600)
    result_count: int=Field(ge=0)
    evidence_count: int=Field(ge=0)
    source_disagreement: bool=False
    truncated: bool=False
    answer_policy: Literal['EVIDENCE_ONLY','NO_DATA','CLARIFY','REFUSE_SCOPE','UNSUPPORTED']='EVIDENCE_ONLY'

    @model_validator(mode='after')
    def complete_evidence(self):
        records=self.records+tuple(r for s in self.sections for r in s.records)
        ids={e.reference_id for e in self.evidence}
        if self.result_count!=len(records) or self.evidence_count!=len(self.evidence) or len(ids)!=len(self.evidence): raise ValueError('Invalid result/evidence count')
        if any(not set(r.evidence_ids)<=ids for r in records): raise ValueError('Naked fact')
        if any(e.build_id!=self.build_id for e in self.evidence): raise ValueError('Mixed serving builds')
        policy={Status.OUT_OF_SCOPE:'REFUSE_SCOPE',Status.AMBIGUOUS:'CLARIFY',Status.UNSUPPORTED:'UNSUPPORTED',Status.NO_DATA:'NO_DATA'}.get(self.status,'EVIDENCE_ONLY')
        if self.answer_policy!=policy: raise ValueError('Status and answer policy must agree')
        if self.status in (Status.AVAILABLE,Status.PARTIAL) and not records: raise ValueError('Available evidence requires records')
        if self.status in (Status.OUT_OF_SCOPE,Status.AMBIGUOUS,Status.UNSUPPORTED,Status.NO_DATA) and records: raise ValueError('Stopped/empty result cannot contain facts')
        return self

class NewsResult(ActionResult): output_type: Literal['NewsResult']='NewsResult'
class PriceHistoryResult(ActionResult): output_type: Literal['PriceHistoryResult']='PriceHistoryResult'
class RentalHistoryResult(ActionResult): output_type: Literal['RentalHistoryResult']='RentalHistoryResult'
class TransactionHistoryResult(ActionResult): output_type: Literal['TransactionHistoryResult']='TransactionHistoryResult'
class RankingResult(ActionResult): output_type: Literal['RankingResult']='RankingResult'
class MarketSnapshotResult(ActionResult): output_type: Literal['MarketSnapshotResult']='MarketSnapshotResult'
class ProjectResult(ActionResult): output_type: Literal['ProjectResult']='ProjectResult'
class RegulationResult(ActionResult): output_type: Literal['RegulationResult']='RegulationResult'
class OutlookResult(ActionResult): output_type: Literal['OutlookResult']='OutlookResult'
class EventActivityResult(ActionResult): output_type: Literal['EventActivityResult']='EventActivityResult'
class ComparisonResult(ActionResult): output_type: Literal['ComparisonResult']='ComparisonResult'
class SourceDetailsResult(ActionResult): output_type: Literal['SourceDetailsResult']='SourceDetailsResult'

OUTPUTS={c.__name__:c for c in (NewsResult,PriceHistoryResult,RentalHistoryResult,TransactionHistoryResult,RankingResult,MarketSnapshotResult,ProjectResult,RegulationResult,OutlookResult,EventActivityResult,ComparisonResult,SourceDetailsResult)}
