"""Comparable peer rankings; competition rank and deterministic tie positions."""
from collections import defaultdict
from dataclasses import asdict
from intelligence.serving.policy import identity


def rank(movements,version='stage13-v1'):
    groups=defaultdict(list)
    for movement in movements:
        series=movement.current.series
        if series.entity_type in ('UNKNOWN','COUNTRY','DEVELOPER') or series.scope in ('UNKNOWN','MULTI_EMIRATE') or movement.change_pct==0:
            continue
        direction='INCREASE' if movement.change_pct>0 else 'DECREASE'
        dimensions=asdict(series);dimensions.pop('entity_id')
        if series.entity_type=='EMIRATE': dimensions['scope']='UAE_WIDE'
        dimensions.update(basis=movement.basis,period=movement.current.period.label,direction=direction,
                          ranking_version=version,movement_version=movement.version,policy_id=movement.policy_id)
        key=identity(dimensions)
        groups[key].append((dimensions,movement))
    result=[]
    for key,group in sorted(groups.items()):
        dimensions=group[0][0];reverse=dimensions['direction']=='INCREASE'
        ordered=sorted((m for _,m in group),key=lambda m:((m.change_pct.copy_negate() if reverse else m.change_pct),m.current.series.entity_id,m.movement_id))
        entries=[];last=None;rank_number=0
        for position,movement in enumerate(ordered,1):
            if last is None or movement.change_pct!=last: rank_number=position
            last=movement.change_pct
            entries.append(dict(position=position,rank_number=rank_number,movement_id=movement.movement_id,entity_id=movement.current.series.entity_id))
        result.append(dict(ranking_id=key,dimensions=dimensions,entries=entries))
    return tuple(result)
