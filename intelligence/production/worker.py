"""JSON-only isolated serving process. No ingestion or fixture imports.

Configuration is changed only in this disposable process, never in Streamlit or
in the Stage 3–14 modules. stdout carries validated contracts, not diagnostics.
"""
import json
import sys
from intelligence.production.store import load_build


def dispatch(payload):
    from intelligence import config as cfg
    from intelligence.query.models import QueryRequest,PageContext
    from intelligence.query.service import query
    from intelligence.current.suggestions import available_suggestions
    from intelligence.query.suggestions import SuggestionResult
    from intelligence.answer_engine import AnswerEngine
    if payload['operation']=='suggestions' and payload.get('artifact') is None:
        return SuggestionResult(suggestions=(),status='NO_AVAILABLE_QUESTIONS').model_dump(mode='json')
    build=load_build(payload['root'])
    if build.sha256!=payload['artifact']:return {'error':'BUILD_CHANGED'}
    cfg.DB_PATH=build.path
    request=QueryRequest.model_validate(payload['request']) if payload.get('request') else None
    context=PageContext.model_validate(payload['context']) if payload.get('context') else None
    operation=payload['operation']
    if operation=='suggestions':return available_suggestions(context,as_of=payload.get('as_of')).model_dump(mode='json')
    if operation=='query':return query(request).model_dump(mode='json')
    if operation not in ('summary','help'):return {'error':'INVALID_OPERATION'}
    # Cross-process concurrency = 1 on this host. No waiting queue or UI retries.
    import fcntl
    import tempfile
    from pathlib import Path
    with (Path(tempfile.gettempdir())/'truestate-stage18-inference.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'error':'BUSY'}
        engine=AnswerEngine()
        from intelligence.current.retrieval import summary_package,help_package
        if operation=='summary':result=engine._answer(lambda:summary_package(context,payload['facts']))
        else:result=engine._answer(lambda:help_package(request))
        return result.model_dump(mode='json')


def main():
    try:
        payload=json.loads(sys.stdin.read(100000))
        response=dispatch(payload)
    except Exception:response={'error':'TEMPORARILY_UNAVAILABLE'}
    print(json.dumps(response))

if __name__=='__main__':main()
