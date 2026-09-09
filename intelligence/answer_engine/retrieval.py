"""Read-only adapters over Stage 14 actions; no new SQL or calculations."""
import re
from intelligence.query import service
from intelligence.query.models import QueryRequest,PageContext
from intelligence.query.service import QueryResponse
from intelligence.query.resolution import page,resolve_one
from intelligence.entities.registry import REGISTRY
from intelligence.answer_engine.models import DashboardFact,Fact,Package,MAX_FACTS

STOP={'NO_DATA':'NO_DATA','OUT_OF_SCOPE':'OUT_OF_SCOPE','AMBIGUOUS':'AMBIGUOUS','UNSUPPORTED':'UNSUPPORTED','NOT_COMPARABLE':'NOT_COMPARABLE'}

def context(value):
    return page(value) if isinstance(value,str) else PageContext.model_validate(value) if value is not None else None

def location_name(value):
    return REGISTRY.entities[resolve_one(value)].canonical_name

def compatible(location,decision):
    entity=REGISTRY.entities[resolve_one(location)]
    scope=decision.filters.emirate.value
    if scope not in ('UAE_WIDE','MULTI_EMIRATE') and entity.emirate and entity.emirate.value!=scope:return False
    targets=decision.filters.entity_ids
    if targets:
        ancestors={entity.entity_id};parent=entity.parent_entity_id
        while parent:
            ancestors.add(parent);parent=REGISTRY.entities[parent].parent_entity_id
        if not set(targets)&ancestors:return False
    return True

def _order(f):
    priority={'RANKING':0,'MOVEMENT':1,'OBSERVATION':2,'EVENT':3,'NEWS':4,'SOURCE':5}
    return (priority.get(f.kind,6),tuple(-ord(c) for c in (f.period or f.published_at or '')),
        f.group_id or '',f.position or f.rank or 0,f.identity)

def _group(f):
    if f.rank is not None:return ('RANKING',f.group_id)
    if f.value is None:return (f.kind,f.identity)
    return (f.kind,f.location,f.metric,f.unit,f.currency,f.property_type,f.statistic,
            f.period,f.basis,f.nature,f.provenance)

def _bounded(facts,*,must_preserve_all=False,limit=MAX_FACTS):
    unique={}
    for fact in facts:
        key=(fact.origin,fact.kind,fact.identity)
        if key in unique and unique[key].model_dump(exclude={'evidence_id'})!=fact.model_dump(exclude={'evidence_id'}):raise ValueError('CONFLICTING_IDENTITY')
        unique[key]=fact
    ordered=sorted(unique.values(),key=_order)
    if len(ordered)>limit and must_preserve_all:raise ValueError('ATOMIC_EVIDENCE_LIMIT')
    groups={}
    for fact in ordered:groups.setdefault(_group(fact),[]).append(fact)
    # A conflict or ranking group is indivisible. Include conflicting source
    # groups first, then the existing deterministic priority/recency order.
    grouped=sorted(groups.values(),key=lambda group:(not len({f.value for f in group})>1 if group[0].rank is None else True,_order(group[0])))
    selected=[]
    for group in grouped:
        if len(group)>MAX_FACTS:raise ValueError('ATOMIC_EVIDENCE_LIMIT')
        if len(selected)+len(group)<=limit:selected.extend(group)
    selected.sort(key=_order)
    return tuple(f.model_copy(update={'evidence_id':'E'+str(i+1)}) for i,f in enumerate(selected)),len(selected)<len(ordered)

def from_response(response,mode='HELP',*,max_facts=MAX_FACTS):
    response=QueryResponse.model_validate(response);result=response.result;route=response.route
    scope=REGISTRY.entities[route.filters.entity_ids[0]].canonical_name if route.filters.entity_ids else route.filters.emirate.value.replace('_',' ').title()
    if scope=='Uae Wide':scope='UAE'
    base=dict(question=response.request.question,mode=mode,intent=route.intent.value,action=route.action_id,scope=scope)
    if result.status.value in STOP:return Package(status=STOP[result.status.value],**base)
    references={e.reference_id:e for e in result.evidence};facts=[]
    records=result.records+tuple(r for section in result.sections for r in section.records)
    for record in records:
        lineage=tuple(references[i] for i in record.evidence_ids)
        entity_ids=lineage[0].entity_ids
        location=REGISTRY.entities[entity_ids[0]].canonical_name if entity_ids else scope
        if entity_ids and not compatible(location,route):raise ValueError('RETRIEVAL_SCOPE_MISMATCH')
        facts.append(Fact(evidence_id='E1',identity=record.identity,origin='INTELLIGENCE',kind=record.kind,
            location=location,metric=record.metric.value if record.metric else None,value=record.value,unit=record.unit,
            currency=record.currency,property_type=record.property_type.value if record.property_type else None,
            statistic=record.statistic,period=record.period,basis=record.movement_basis,
            provenance=record.provenance or 'SOURCE_REPORTED',nature=record.nature or 'OBSERVED',
            rank=record.rank_number,position=record.position,group_id=record.group_id,title=record.title,
            source=lineage[0].source_name,published_at=lineage[0].published_at.isoformat() if lineage[0].published_at else None,lineage=lineage))
    facts,truncated=_bounded(facts,must_preserve_all=route.intent.value.startswith('COMPARE'),limit=max_facts)
    missing=tuple(REGISTRY.entities[s.name].canonical_name if s.name in REGISTRY.entities else s.name.replace('_',' ')
                  for s in result.sections if s.status.value!='AVAILABLE')
    partial=result.status.value=='PARTIAL' or truncated
    if truncated:missing+=('additional evidence outside the context limit',)
    if partial and not missing:missing=('requested comparable data or complete coverage',)
    return Package(status='PARTIAL_DATA' if partial else 'ANSWER',facts=facts,missing=missing,
        source_disagreement=result.source_disagreement,truncated=result.truncated or truncated,**base)

def retrieve(question,page_context=None,*,as_of=None,limit=MAX_FACTS):
    request=QueryRequest(question=question,page_context=context(page_context),as_of=as_of,limit=limit)
    response=service.query(request)
    # Exact product paraphrases only. Every replacement is routed by Stage 14;
    # out-of-scope/ambiguous decisions and arbitrary queries remain untouched.
    text=question.strip().lower()
    replacement=None
    if response.route.scope_status=='UNSUPPORTED':
        replacement={
            'which dubai areas increased the most?':'Which Dubai areas have the largest price increases?',
            'how is rak property doing?':'RAK property market summary',
        }.get(text)
    elif text=='show me areas where prices dropped.' and response.route.scope_status=='IN_SCOPE' and response.route.action_id=='get_price_history':
        replacement='Which property areas have the largest price decreases?'
    if replacement:
        response=service.query(request.model_copy(update={'question':replacement}))
    return from_response(response).model_copy(update={'question':question}),response

def dashboard(page_context,dashboard_facts,intelligence_context=None,*,summary_limit=MAX_FACTS):
    ctx=context(page_context)
    if ctx is None:raise ValueError('DASHBOARD_CONTEXT_REQUIRED')
    question='UAE market outlook' if ctx.page_type=='OUTLOOK' else 'How is the property market here?'
    request=QueryRequest(question=question,page_context=ctx,limit=MAX_FACTS)
    # The existing Stage 14 gate and router are authoritative even for dashboards.
    response=service.query(request)
    if response.route.scope_status!='IN_SCOPE':return from_response(response,'DASHBOARD')
    supplied=tuple(DashboardFact.model_validate(f) for f in dashboard_facts)
    if len(supplied)>MAX_FACTS:raise ValueError('DASHBOARD_EVIDENCE_LIMIT')
    facts=[]
    for f in supplied:
        location=location_name(f.location)
        if not compatible(location,response.route):raise ValueError('DASHBOARD_SCOPE_MISMATCH')
        if not re.fullmatch(r'20\d{2}(?:-(?:0[1-9]|1[0-2]|Q[1-4]))?',f.period):raise ValueError('DASHBOARD_PERIOD_REQUIRED')
        facts.append(Fact(evidence_id='E1',identity=f.identity,origin='DASHBOARD',kind='RANKING' if f.rank else 'OBSERVATION',
            location=location,metric=f.metric,value=f.value,unit=f.unit,period=f.period,provenance=f.provenance,nature=f.nature,
            rank=f.rank,position=f.rank,group_id=f.group_id,basis=f.basis,source=f.source,reference=f.reference))
    # Supplement only with a genuine Stage 14 response whose route matches this scope.
    supplemental=QueryResponse.model_validate(intelligence_context) if intelligence_context is not None else response
    if supplemental.route.filters.emirate!=response.route.filters.emirate or supplemental.route.filters.entity_ids!=response.route.filters.entity_ids:
        raise ValueError('SUPPLEMENT_SCOPE_MISMATCH')
    extra=from_response(supplemental,'DASHBOARD',max_facts=summary_limit)
    available=list(extra.facts)
    room=summary_limit-len(facts)
    selected,extra_truncated=_bounded(available,limit=room) if room else ((),bool(available))
    # Website analytics always have priority; never replace or recompute them.
    facts.extend(selected);facts,truncated=_bounded(facts,must_preserve_all=True,limit=summary_limit)
    groups={}
    for f in facts:
        if f.value is not None and f.rank is None:groups.setdefault(_group(f),set()).add(f.value)
    conflict=any(len(v)>1 for v in groups.values())
    partial=len(available)>room or (bool(extra.facts) and extra.status=='PARTIAL_DATA')
    missing=extra.missing if partial else ()
    if extra.source_disagreement and not conflict:
        partial=True;missing+=('additional conflicting source evidence',)
    return Package(status='NO_DATA' if not facts else 'PARTIAL_DATA' if partial or conflict else 'ANSWER',question=question,mode='DASHBOARD',
        intent=response.route.intent.value,action=response.route.action_id,scope=extra.scope,facts=facts,
        missing=missing,source_disagreement=conflict,truncated=truncated or len(available)>room)
