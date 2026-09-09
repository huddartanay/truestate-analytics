"""Exact registry aliases and explicit reference-time calendar resolution."""
import re
from datetime import datetime,timedelta,timezone
from intelligence.entities.registry import REGISTRY
from intelligence.entities.normalize import normalize
from intelligence.query.models import PageContext,TimeFilter
from intelligence.enums import Emirate

GEO_FIELDS=('city','area','community','project','building','developer')

def entities(text):
    value=normalize(text);hits=[]
    for alias,entity,policy,regex in REGISTRY.matchers:
        for match in regex.finditer(value): hits.append((match.start(),match.end(),entity.entity_id))
    occupied=set();found=[]
    for start,end,entity in sorted(hits,key=lambda x:(-(x[1]-x[0]),x[0],x[2])):
        if any(i in occupied for i in range(start,end)): continue
        occupied.update(range(start,end));found.append((start,entity))
    ids=tuple(dict.fromkeys(e for _,e in sorted(found)))
    # Ancestor mentions specify context, not extra comparison targets.
    ancestors=set()
    for entity in ids:
        parent=REGISTRY.entities[entity].parent_entity_id
        while parent:
            ancestors.add(parent);parent=REGISTRY.entities[parent].parent_entity_id
    return tuple(e for e in ids if e not in ancestors)

def resolve_one(value,kind=None):
    if value in REGISTRY.entities: ids=(value,)
    else: ids=entities(value.replace('_',' '))
    if len(ids)!=1: raise ValueError('UNRESOLVED_ENTITY')
    if kind and REGISTRY.entities[ids[0]].entity_type.value!=kind: raise ValueError('ENTITY_TYPE_MISMATCH')
    return ids[0]

def context_ids(context):
    if context is None: return ()
    if context.emirate in (Emirate.UNKNOWN,Emirate.MULTI_EMIRATE): raise ValueError('EXPLICIT_EMIRATE_REQUIRED')
    result=tuple(resolve_one(getattr(context,k),k.upper()) for k in GEO_FIELDS if getattr(context,k,None))
    if result:
        scopes={REGISTRY.entities[e].emirate for e in result if REGISTRY.entities[e].emirate}
        if len(scopes)>1 or (context.emirate and context.emirate!=Emirate.UAE_WIDE and scopes and context.emirate not in scopes): raise ValueError('CONFLICTING_CONTEXT')
    elif context.emirate and context.emirate not in (Emirate.UNKNOWN,Emirate.MULTI_EMIRATE):
        result=('country:uae',) if context.emirate==Emirate.UAE_WIDE else ('emirate:'+context.emirate.value.lower(),)
    return result

def page(value):
    """Backend adapter names only; no Streamlit import or state access."""
    key=value.upper().replace(' ','_')
    if key in ('GLOBAL','OVERVIEW','EXPLORE','ABOUT','HELP'): return PageContext(page_id=key)
    if key=='BUSINESS_BAY': return PageContext(page_id='AREA_ANALYSIS',page_type='AREA',emirate='DUBAI',area='area:dubai:business_bay')
    if key in ('FORECAST','MARKET_OUTLOOK'): return PageContext(page_id=key,page_type='OUTLOOK')
    if key=='RAK':key='RAS_AL_KHAIMAH'
    if key=='UAQ':key='UMM_AL_QUWAIN'
    return PageContext(page_id=key+'_OVERVIEW',page_type='EMIRATE',emirate=Emirate(key))

def time_filter(text,as_of):
    value=text.lower().replace('_',' ');basis=None
    for label,pattern in [('MOM',r'\b(?:mom|month.over.month)\b'),('QOQ',r'\b(?:qoq|quarter.over.quarter)\b'),('YOY',r'\b(?:yoy|year.over.year)\b')]:
        if re.search(pattern,value):
            if basis: raise ValueError('CONFLICTING_TIME_BASIS')
            basis=label
    relative=[label for label,pattern in [('TODAY',r'\btoday\b'),('THIS_WEEK',r'\bthis week\b'),('THIS_MONTH',r'\bthis month\b'),('LAST_MONTH',r'\blast month\b')] if re.search(pattern,value)]
    quarters=re.findall(r'\bq([1-4])(?:\s+(20\d{2}))?\b',value)
    explicit=re.search(r'\b(20\d{2})-(0[1-9]|1[0-2])\b',value)
    if len(relative)+len(quarters)+bool(explicit)>1: raise ValueError('CONFLICTING_TIME_FILTER')
    if (relative or (quarters and not quarters[0][1])) and as_of is None: raise ValueError('REFERENCE_TIME_REQUIRED')
    now=as_of.astimezone(timezone.utc) if as_of else None
    def month(year,number):return datetime(year,number,1,tzinfo=timezone.utc)
    def next_month(date):return month(date.year+(date.month==12),date.month%12+1)
    if relative:
        expression=relative[0];start=now.replace(hour=0,minute=0,second=0,microsecond=0)
        period=None
        if expression=='TODAY':end=start+timedelta(days=1)
        elif expression=='THIS_WEEK':start-=timedelta(days=start.weekday());end=start+timedelta(days=7)
        else:
            start=month(now.year,now.month)
            if expression=='LAST_MONTH':start=month(start.year-(start.month==1),(start.month-2)%12+1)
            end=next_month(start);period=f'{start.year}-{start.month:02d}'
        return TimeFilter(expression=expression,start=start,end=end,period=period),basis
    if quarters:
        quarter,year=quarters[0];year=int(year) if year else now.year;quarter=int(quarter)
        start=month(year,3*quarter-2);end=month(year+1,1) if quarter==4 else month(year,3*quarter+1)
        return TimeFilter(expression='QUARTER',start=start,end=end,period=f'{year}-Q{quarter}'),basis
    if explicit:
        start=month(int(explicit[1]),int(explicit[2]));return TimeFilter(expression='MONTH',start=start,end=next_month(start),period=explicit[0]),basis
    return TimeFilter(),basis
