"""Bounded Stage 16 contracts; Stage 13/14 retain factual authority."""
from typing import Literal
from decimal import Decimal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from intelligence.query.models import Evidence

SYSTEM_PROMPT_VERSION=ANSWER_ENGINE_VERSION=RETRIEVAL_VERSION='stage16-v1'
MAX_FACTS=6
MAX_SUMMARY_FACTS=10
MAX_CONTEXT_BYTES=18000
Provenance=Literal['SYSTEM_CALCULATED','SOURCE_REPORTED']
Nature=Literal['OBSERVED','SOURCE_REPORTED_FORECAST']

class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)

class DashboardFact(Model):
    """Trusted backend adapter input, never a free-form user fact declaration."""
    identity:str=Field(min_length=1,max_length=100)
    location:str=Field(min_length=1,max_length=160)
    metric:str=Field(min_length=1,max_length=100)
    value:str=Field(min_length=1,max_length=100)
    unit:str=Field(min_length=1,max_length=50)
    period:str=Field(min_length=1,max_length=60)
    provenance:Provenance
    nature:Nature
    source:str=Field(min_length=1,max_length=160)
    reference:str=Field(min_length=1,max_length=300)
    rank:int|None=Field(default=None,ge=1,strict=True)
    group_id:str|None=Field(default=None,max_length=100)
    basis:str|None=Field(default=None,max_length=40)

    @model_validator(mode='after')
    def coherent(self):
        if not Decimal(self.value).is_finite():raise ValueError('Finite exact value required')
        if self.nature=='SOURCE_REPORTED_FORECAST' and self.provenance!='SOURCE_REPORTED':raise ValueError('Forecast is source-reported')
        if self.rank is not None and (not self.group_id or self.provenance!='SYSTEM_CALCULATED'):raise ValueError('Ranking requires calculated group')
        return self

class Fact(Model):
    evidence_id:str=Field(pattern=r'^E(?:[1-9]|10)$')
    identity:str
    origin:Literal['INTELLIGENCE','DASHBOARD','CURRENT_RSS']
    kind:str
    location:str
    metric:str|None=None
    value:str|None=None
    unit:str|None=None
    currency:str|None=None
    property_type:str|None=None
    statistic:str|None=None
    period:str|None=None
    basis:str|None=None
    provenance:Provenance
    nature:Nature
    rank:int|None=None
    position:int|None=None
    group_id:str|None=None
    title:str|None=None
    source:str
    published_at:str|None=None
    excerpt:str|None=Field(default=None,max_length=600)
    reference:str|None=None
    lineage:tuple[Evidence,...]=()

class Package(Model):
    status:Literal['ANSWER','PARTIAL_DATA','NO_DATA','OUT_OF_SCOPE','AMBIGUOUS','UNSUPPORTED','NOT_COMPARABLE']
    question:str=Field(max_length=1000)
    mode:Literal['HELP','DASHBOARD']
    intent:str
    action:str|None
    scope:str
    facts:tuple[Fact,...]=Field(default=(),max_length=MAX_SUMMARY_FACTS)
    missing:tuple[str,...]=()
    source_disagreement:bool=False
    truncated:bool=False
    retrieval_version:str=RETRIEVAL_VERSION

    @model_validator(mode='after')
    def mode_limit(self):
        if self.mode=='HELP' and len(self.facts)>MAX_FACTS:raise ValueError('HELP_EVIDENCE_LIMIT')
        return self

class Claim(Model):
    evidence_id:str=Field(pattern=r'^E(?:[1-9]|10)$')
    value:str|None
    unit:str|None
    location:str
    period:str|None
    provenance:Provenance
    nature:Nature
    rank:int|None=Field(ge=1,strict=True)
    text:str|None=Field(max_length=500)

class Generated(Model):
    status:Literal['ANSWER','PARTIAL_DATA']
    claims:list[Claim]=Field(min_length=1,max_length=MAX_FACTS)

class SummaryClaim(Claim):
    # Short schema keys keep ten fully checked facts within the unchanged
    # provider output cap. Internal field names/validation remain identical.
    model_config=ConfigDict(extra='forbid',frozen=True,populate_by_name=True)
    evidence_id:str=Field(alias='id',pattern=r'^E(?:[1-9]|10)$')
    value:str|None=Field(alias='v')
    unit:str|None=Field(alias='u')
    location:str=Field(alias='l')
    period:str|None=Field(alias='p')
    provenance:Provenance=Field(alias='pr')
    nature:Nature=Field(alias='n')
    rank:int|None=Field(alias='r',ge=1,strict=True)
    text:str|None=Field(alias='t',max_length=500)

class RichGenerated(Generated):
    claims:list[SummaryClaim]=Field(min_length=1,max_length=MAX_SUMMARY_FACTS)

class RenderedClaim(Model):
    evidence_id:str
    text:str
    provenance:Provenance
    nature:Nature
    source:str

class Audit(Model):
    request_id:str
    intent:str
    action:str|None
    model:str
    evidence_count:int
    evidence_ids:tuple[str,...]
    status:str
    attempts:int
    retry_count:int
    latency_ms:float
    retrieval_ms:float
    validation:Literal['PASS','FAIL','NOT_RUN']
    error_code:str|None=None
    retry_after_seconds:float|None=None
    prompt_version:str=SYSTEM_PROMPT_VERSION
    answer_engine_version:str=ANSWER_ENGINE_VERSION
    retrieval_version:str=RETRIEVAL_VERSION

class Answer(Model):
    status:str
    answer:str
    claims:tuple[RenderedClaim,...]=()
    evidence:tuple[Fact,...]=()
    audit:Audit
