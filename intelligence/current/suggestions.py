"""Answerable website shortcuts from the existing catalog, without acquisition.

Uses the same deterministic hybrid retrieval as a submitted question. A missing
current cache is an explicit empty snapshot, never a request to refresh feeds.
"""
from datetime import datetime,timezone
from intelligence.query.catalog import QUESTIONS,render
from intelligence.query.models import PageContext,QueryRequest,Status
from intelligence.query.suggestions import Suggestion,SuggestionResult
from intelligence.current.cache import read,root_path
from intelligence.current.retrieval import help_package


def available_suggestions(context=None,*,as_of=None,current=None):
    context=PageContext.model_validate(context) if context is not None else None
    now=datetime.fromisoformat(as_of) if isinstance(as_of,str) else as_of or datetime.now(timezone.utc)
    state=current if current is not None else read(root_path()) or ()
    scope=context.emirate.value if context and context.emirate else 'UAE_WIDE'
    candidates=[]
    for q in QUESTIONS.values():
        if not q.enabled or not q.suggested_for_chat:continue
        fallback=False
        if q.required_context:
            if not context or context.page_type not in q.supported_contexts:continue
            if context.page_type in ('AREA','PROJECT','DEVELOPER') and q.required_context==('emirate',):continue
            try:text=render(q,context)
            except ValueError:continue
            priority=0
        elif q.default_filters.get('emirate')==scope and not(context and context.page_type in ('AREA','PROJECT','DEVELOPER')):
            text=q.question_template;priority=1
        elif q.default_filters.get('emirate')=='UAE_WIDE':
            text=q.question_template;priority=2;fallback=scope!='UAE_WIDE' or bool(context and context.page_type in ('AREA','PROJECT','DEVELOPER'))
        else:continue
        request=QueryRequest(question=text,selected_question_id=q.question_id,page_context=None if fallback else context,as_of=now)
        candidates.append((priority,q.display_priority,q.question_id,q,request,fallback))
    candidates.sort(key=lambda row:row[:3])
    selected=[];used=set();signatures=set()
    # Prefer one useful shortcut per action; UAE expansion stays explicit in the
    # original catalog wording. Do not pad with dates or synonym variants.
    for _,_,_,q,request,fallback in candidates:
        if q.action_id in used:continue
        package=help_package(request,current=state)
        if package.status not in ('ANSWER','PARTIAL_DATA') or not package.facts:continue
        signature=tuple((f.kind,f.identity) for f in package.facts)
        if signature in signatures:continue
        if package.action is None or package.action in used:continue
        selected.append(Suggestion(question_id=q.question_id,question=request.question,category=q.category,
            action_id=package.action,expected_output_type=q.expected_output_type,
            data_status=Status.PARTIAL if package.status=='PARTIAL_DATA' else Status.AVAILABLE,
            fallback=fallback,request=request))
        used.add(package.action);signatures.add(signature)
        if len(selected)==5:break
    return SuggestionResult(suggestions=tuple(selected),status='AVAILABLE' if len(selected)==5 else 'LIMITED_AVAILABLE_QUESTIONS')
