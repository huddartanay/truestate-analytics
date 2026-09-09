"""Source-specific series. No imputation, unit conversion or source averaging."""
from dataclasses import dataclass, asdict
from decimal import Decimal
from intelligence.entities.registry import REGISTRY
from intelligence.serving.policy import identity
from intelligence.serving.periods import Period


@dataclass(frozen=True)
class Series:
    entity_id: str
    entity_type: str
    scope: str
    source_id: str
    metric: str
    property_type: str
    statistic: str
    currency: str
    unit: str
    nature: str
    frequency: str

    @property
    def series_id(self): return identity(asdict(self))


@dataclass(frozen=True)
class Point:
    observation_id: str
    series: Series
    period: Period
    value: Decimal

    def __post_init__(self):
        if not isinstance(self.value,Decimal) or not self.value.is_finite() or self.value < 0:
            raise ValueError('Finite nonnegative Decimal level required')
        if self.period.frequency != self.series.frequency or self.series.nature != 'OBSERVED':
            raise ValueError('Point must be an observed level with matching frequency')


def geography(links):
    """Choose the one most specific explicitly linked geographic entity.

    Multiple branches fail closed. An article's MULTI_EMIRATE scope is never
    assigned to a clause observation. Ancestors are registry metadata only.
    """
    found = {link.entity_id for link in links if REGISTRY.entities[link.entity_id].entity_type != 'DEVELOPER'}
    leaves = set(found)
    for entity_id in found:
        parent = REGISTRY.entities[entity_id].parent_entity_id
        while parent:
            leaves.discard(parent)
            parent = REGISTRY.entities[parent].parent_entity_id
    if len(leaves) != 1: return ('UNKNOWN','UNKNOWN','UNKNOWN')
    entity = REGISTRY.entities[leaves.pop()]
    return entity.entity_id,entity.entity_type.value,entity.emirate.value if entity.emirate else 'UAE_WIDE'


def family(metric):
    if metric.startswith('TRANSACTION_'): return 'TRANSACTION'
    if metric.startswith('RENT') or metric in ('ANNUAL_RENT','MONTHLY_RENT'): return 'RENT'
    return 'PRICE'


def exclusion(observation,period,geo):
    if observation.nature != 'OBSERVED': return 'FORECAST'
    if observation.metric in ('PRICE_CHANGE_PCT','RENT_CHANGE_PCT'): return 'SOURCE_REPORTED_CHANGE'
    if observation.qualifier != 'EXACT': return 'NON_EXACT'
    if period is None: return 'UNRESOLVED_PERIOD'
    if geo[0] == 'UNKNOWN': return 'UNKNOWN_GEOGRAPHY'
    return None
