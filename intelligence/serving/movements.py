"""Linear indexed period comparisons; exact inputs and 50-digit Decimal division."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from intelligence.serving.policy import POLICY, identity, ComponentError
from intelligence.serving.series import Point


@dataclass(frozen=True)
class Movement:
    movement_id: str
    current: Point
    previous: Point
    basis: str
    change_pct: Decimal
    classification: str
    version: str
    policy_id: str


def calculate(points,version='stage13-v1',policy=POLICY):
    indexed=defaultdict(lambda:defaultdict(list))
    counts=Counter(); unavailable=[]; movements=[]
    for point in points:
        indexed[point.series.series_id][point.period.ordinal].append(point)
        counts['indexed_points']+=1
    for series_id,periods in sorted(indexed.items()):
        for ordinal,current_group in sorted(periods.items()):
            # Distinct accepted publications at the same source/period are
            # ambiguous even when values agree; retain all, compare none.
            if len(current_group)!=1:
                counts['conflicting_observations']+=len(current_group)
                counts['SOURCE_CONFLICT']+=len(current_group)
                for point in current_group:
                    unavailable.append((point.observation_id,'ALL','SOURCE_CONFLICT'))
                continue
            current=current_group[0]
            comparisons={'MONTHLY':(('MOM',1),('YOY',12)),
                         'QUARTERLY':(('QOQ',1),('YOY',4)), 'ANNUAL':(('YOY',1),)}[current.period.frequency]
            for basis,offset in comparisons:
                counts['period_lookups']+=1
                previous_group=periods.get(ordinal-offset,())
                reason = ('MISSING_COMPARISON_PERIOD' if not previous_group else
                          'SOURCE_CONFLICT' if len(previous_group)!=1 else
                          'ZERO_DENOMINATOR' if previous_group[0].value==0 else None)
                if reason:
                    counts[reason]+=1
                    unavailable.append((current.observation_id,basis,reason));continue
                previous=previous_group[0]
                # Subtraction/multiplication use enough precision for all input
                # digits. Only division rounds to the documented policy precision.
                with localcontext() as ctx:
                    ctx.prec=max(policy.precision,max(current.value.adjusted(),previous.value.adjusted())-min(current.value.as_tuple().exponent,previous.value.as_tuple().exponent)+4)
                    numerator=(current.value-previous.value)*Decimal(100)
                    ctx.prec=policy.precision;ctx.rounding=ROUND_HALF_EVEN
                    change=numerator/previous.value
                key=identity((series_id,current.observation_id,previous.observation_id,basis,version,policy.policy_id))
                try:
                    classification=policy.classify(change)
                except Exception as exc:
                    raise ComponentError('CLASSIFICATION') from exc
                movements.append(Movement(key,current,previous,basis,change,classification,version,policy.policy_id))
                counts[basis]+=1
    return tuple(movements),dict(counts),tuple(unavailable)
