"""Website adapter: verified production build → existing backend → safe display.

No raw drafts, prompts, credentials or backend exception details are returned.
"""
from dataclasses import dataclass
import hashlib
import json
import os
import subprocess
import sys
from intelligence.answer_engine.models import ANSWER_ENGINE_VERSION,Answer
from platform_core import ai_presentation as presentation
from intelligence.production.store import ROOT,production_root
from intelligence.query.models import QueryRequest
from intelligence.query.suggestions import SuggestionResult

@dataclass(frozen=True)
class View:
    status: str
    answer: str
    sources: tuple=()
    alternatives: tuple=()


def context_key(context,facts,selection,build,as_of,*,current_fingerprint=None):
    value=dict(context=context.model_dump(mode='json'),facts=[f.model_dump(mode='json') for f in facts],
        selection=selection,build_id=build.build_id if build else None,artifact=build.sha256 if build else None,as_of=as_of,engine=ANSWER_ENGINE_VERSION,current_contract='market-assistant-ux-v1',current_fingerprint=current_fingerprint)
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def credential(secrets=None):
    # Read only on an explicit answer request. Nothing enters session_state.
    value=os.environ.get('OPENROUTER_API_KEY')
    if value:return value
    try:
        value=secrets.get('OPENROUTER_API_KEY') if secrets is not None else None
        return value if isinstance(value,str) and value.strip() else None
    except Exception:return None


def call(operation,build,*,context=None,facts=(),request=None,as_of=None,secrets=None):
    if build is None and operation in ('summary','help'):
        from intelligence.query.router import route
        status='OUT_OF_SCOPE' if request and route(request).scope_status=='OUT_OF_SCOPE' else 'NO_DATA'
        return {'stopped':status}
    env=os.environ.copy();env.pop('OPENROUTER_API_KEY',None)
    if operation in ('summary','help'):
        value=credential(secrets)
        if value:env['OPENROUTER_API_KEY']=value
    payload=dict(operation=operation,root=str(production_root()),artifact=build.sha256 if build else None,
        context=context.model_dump(mode='json') if context else None,
        facts=[f.model_dump(mode='json') for f in facts],
        request=request.model_dump(mode='json') if request else None,as_of=as_of)
    try:
        result=subprocess.run([sys.executable,'-m','intelligence.production.worker'],
            input=json.dumps(payload),capture_output=True,text=True,cwd=ROOT,env=env,
            timeout=650 if operation in ('help','summary') else 20)
        return json.loads(result.stdout) if result.returncode==0 else {'error':'TEMPORARILY_UNAVAILABLE'}
    except Exception:return {'error':'TEMPORARILY_UNAVAILABLE'}


def request_key(request,build,current_fingerprint=None):
    """Identity for audit/history only; generated chat answers are never reused."""
    import unicodedata
    data=QueryRequest.model_validate(request).model_dump(mode='json')
    data['question']=' '.join(unicodedata.normalize('NFKC',data['question']).casefold().split())
    return hashlib.sha256(json.dumps({'request':data,'historical':build.sha256 if build else None,
        'current':current_fingerprint},sort_keys=True).encode()).hexdigest()


def display_result(raw,*,summary=False,request=None,alternatives=()):
    def stopped(status):
        text=presentation.MESSAGES.get(status,presentation.MESSAGES['TEMPORARILY_UNAVAILABLE'])
        if status=='NO_DATA' and request:
            from intelligence.current.retrieval import subject
            from intelligence.query.router import route
            name=subject(request);decision=route(request)
            if name:text="I couldn't find enough verified information about "+presentation.clean(name)+" in the available market information."
            elif decision.action_id=='get_latest_projects':
                location=decision.filters.emirate.value.replace('_',' ').title().replace('Uae Wide','the UAE')
                text="I don't currently have enough verified project information for "+location+" to answer that reliably."
        return View(status,text,alternatives=tuple(alternatives[:3]) if status=='NO_DATA' else ())
    if raw.get('stopped') in ('NO_DATA','OUT_OF_SCOPE'):return stopped(raw['stopped'])
    if 'error' in raw:return stopped('TEMPORARILY_UNAVAILABLE')
    try:answer=Answer.model_validate(raw)
    except Exception:return stopped('VALIDATION_FAILED')
    if answer.status not in ('ANSWER','PARTIAL_DATA'):return stopped(answer.status if answer.status in presentation.MESSAGES else 'TEMPORARILY_UNAVAILABLE')
    if answer.audit.validation!='PASS' or not answer.claims:return stopped('VALIDATION_FAILED')
    # Exact IDs/claims remain internal. Only already-validated facts enter the
    # plain-language presenter; raw model drafts and exception bodies never do.
    return View(answer.status,presentation.business_answer(answer,summary=summary),presentation.public_sources(answer))


def suggestions(build,context,as_of):
    result=call('suggestions',build,context=context,as_of=as_of)
    try:
        typed=SuggestionResult.model_validate(result)
        return tuple(s for s in typed.suggestions if s.data_status.value in ('AVAILABLE','PARTIAL'))
    except Exception:return ()
