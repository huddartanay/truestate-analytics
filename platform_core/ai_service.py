"""Website adapter: verified production build → existing backend → safe display.

No raw drafts, prompts, credentials or backend exception details are returned.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from intelligence.answer_engine.models import ANSWER_ENGINE_VERSION,Answer,DashboardFact
from intelligence.answer_engine.engine import STOP_TEXT
from intelligence.production.store import ROOT,load_build,production_root,safe_url,ProductionUnavailable
from intelligence.query.models import PageContext,QueryRequest
from intelligence.query.suggestions import SuggestionResult

@dataclass(frozen=True)
class View:
    status: str
    answer: str
    sources: tuple=()


def context_key(context,facts,selection,build,as_of):
    value=dict(context=context.model_dump(mode='json'),facts=[f.model_dump(mode='json') for f in facts],
        selection=selection,build_id=build.build_id if build else None,artifact=build.sha256 if build else None,as_of=as_of,engine=ANSWER_ENGINE_VERSION,current_contract='current-rss-rich-summary-v1')
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


def display_result(raw):
    if raw.get('stopped') in ('NO_DATA','OUT_OF_SCOPE'):return View(raw['stopped'],STOP_TEXT[raw['stopped']])
    if 'error' in raw:return View('TEMPORARILY_UNAVAILABLE',STOP_TEXT['TEMPORARILY_UNAVAILABLE'])
    try:answer=Answer.model_validate(raw)
    except Exception:return View('VALIDATION_FAILED',STOP_TEXT['VALIDATION_FAILED'])
    if answer.status not in ('ANSWER','PARTIAL_DATA'):
        status=answer.status if answer.status in STOP_TEXT else 'TEMPORARILY_UNAVAILABLE'
        return View(status,STOP_TEXT[status])
    if answer.audit.validation!='PASS' or not answer.claims:return View('VALIDATION_FAILED',STOP_TEXT['VALIDATION_FAILED'])
    sources=[]
    for f in answer.evidence:
        if not f.lineage:
            sources.append(dict(evidence_id=f.evidence_id,source=f.source,reference=f.reference,url=None,
                published_at=None,retrieved_at=None))
        for e in f.lineage:
            sources.append(dict(evidence_id=f.evidence_id,source=e.source_name,reference=e.reference_id,
                url=safe_url(e.article_url),source_id=e.source_id,article_title=f.title,published_at=e.published_at.isoformat() if e.published_at else None,
                retrieved_at=e.retrieved_at.isoformat()))
    return View(answer.status,answer.answer,tuple(sources))


def suggestions(build,context,as_of):
    result=call('suggestions',build,context=context,as_of=as_of)
    try:
        typed=SuggestionResult.model_validate(result)
        return typed.suggestions if len(typed.suggestions)==5 else ()
    except Exception:return ()
