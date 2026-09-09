"""Exactly five deterministic, diverse, context-compatible shortcuts; never UI."""
from intelligence import config as cfg
from datetime import datetime
from pydantic import Field
from intelligence.query.models import Model,PageContext,QueryRequest,Status
from intelligence.query.catalog import QUESTIONS,render
from intelligence.query.router import route
from intelligence.query.actions import execute
from intelligence.query.resolution import context_ids

class Suggestion(Model):
    question_id: str
    question: str
    category: str
    action_id: str
    expected_output_type: str
    data_status: Status
    fallback: bool=False
    request: QueryRequest

class SuggestionResult(Model):
    version: str=cfg.SUGGESTED_PROMPT_VERSION
    suggestions: tuple[Suggestion,...]=Field(max_length=5)
    status: str

def get_context_suggestions(context=None,*,as_of=None):
    context=PageContext.model_validate(context) if context is not None else None
    ids=context_ids(context)
    scope=context.emirate.value if context and context.emirate else 'UAE_WIDE'
    candidates=[]
    for q in QUESTIONS.values():
        if not q.enabled or not q.suggested_for_chat:continue
        if context and context.property_type and q.property_type and q.property_type!=context.property_type.value:continue
        fallback=False
        if q.required_context:
            if not context or context.page_type not in q.supported_contexts:continue
            if context.page_type in ('AREA','PROJECT','DEVELOPER') and q.required_context==('emirate',):continue
            try:text=render(q,context)
            except ValueError:continue
            priority=0
        else:
            qscope=q.default_filters.get('emirate')
            if qscope==scope and not (context and context.page_type in ('AREA','PROJECT','DEVELOPER')):priority=1
            elif qscope=='UAE_WIDE':priority=2;fallback=bool(ids)
            else:continue
            text=q.question_template
        request=QueryRequest(question=text,selected_question_id=q.question_id,page_context=None if fallback else context,as_of=as_of)
        decision=route(request)
        if decision.scope_status!='IN_SCOPE':continue
        candidates.append((priority,q.display_priority,q.question_id,q,request,decision,fallback))
    candidates.sort(key=lambda item:item[:3])
    # Bounded probing: at most one catalog representative per category and
    # context tier, not 240 executions. Availability changes order, never facts.
    pool=[];category_counts={}
    for candidate in candidates:
        group=(candidate[0],candidate[3].category)
        if category_counts.get(group,0)>=1:continue
        category_counts[group]=1;pool.append(candidate)
        if len(pool)>=32:break
    scored=[]
    for priority,order,key,q,request,decision,fallback in pool:
        result=execute(decision,as_of)
        available=result.status in (Status.AVAILABLE,Status.PARTIAL)
        scored.append((priority,not available,order,key,q,request,decision,result.status,fallback))
    scored.sort(key=lambda item:item[:4]);selected=[];categories=set();used=set()
    for diverse in (True,False):
        for _,_,_,key,q,request,decision,status,fallback in scored:
            if key in used or (diverse and q.category in categories):continue
            selected.append(Suggestion(question_id=key,question=request.question,category=q.category,action_id=decision.action_id,expected_output_type=decision.expected_output_type,data_status=status,fallback=fallback,request=request))
            used.add(key);categories.add(q.category)
            if len(selected)==5:return SuggestionResult(suggestions=tuple(selected),status='AVAILABLE')
    return SuggestionResult(suggestions=tuple(selected),status='INSUFFICIENT_VALID_SUGGESTIONS')
