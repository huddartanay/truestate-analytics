"""Stage 16 orchestration. Reuses Stage 14 retrieval and the Stage 15 transport."""
import json
import logging
import math
import threading
import time
import uuid
from datetime import datetime,timezone
from decimal import InvalidOperation
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from intelligence.llm import openrouter_settings as settings
from intelligence.llm.openrouter import OpenRouterClient,ProviderError,InvalidStructuredOutput
from intelligence.answer_engine import retrieval
from intelligence.answer_engine.models import Answer,Audit,Generated,RichGenerated,Package
from intelligence.answer_engine.prompt import messages
from intelligence.answer_engine.rendering import render

MODEL='qwen/qwen3-235b-a22b-2507'
_PROVIDER_SLOT=threading.BoundedSemaphore(1)
LOG=logging.getLogger('truestate.answer_engine')
STOP_TEXT={
    'NO_DATA':"I don't have enough TruEstate data to answer that question currently.",
    'OUT_OF_SCOPE':'TruEstate supports UAE real-estate questions only.',
    'AMBIGUOUS':'Please clarify the UAE location, metric or period for this question.',
    'UNSUPPORTED':'The requested answer is not supported by the available TruEstate actions.',
    'NOT_COMPARABLE':'The supplied evidence is not comparable; no combined market conclusion is available.',
    'TEMPORARILY_UNAVAILABLE':'AI assistance is temporarily unavailable. Please try again shortly.',
    'VALIDATION_FAILED':'The generated answer could not be verified against TruEstate evidence. Please try again later.'}

def retry_after(value,now=None):
    if value is None:return None
    try:
        seconds=float(value)
    except (ValueError,TypeError):
        try:seconds=(parsedate_to_datetime(value)-(now or datetime.now(timezone.utc))).total_seconds()
        except (ValueError,TypeError,OverflowError):return float('inf')
    return max(0,seconds) if math.isfinite(seconds) else float('inf')

class HeaderObserver:
    """Capture only Retry-After. No error body, credentials or new HTTP client."""
    def __init__(self,opener):self.opener=opener;self.delay=None
    def open(self,request,**kwargs):
        self.delay=None
        try:response=self.opener.open(request,**kwargs)
        except HTTPError as exc:
            self.delay=retry_after(exc.headers.get('Retry-After') if exc.headers else None);raise
        self.delay=retry_after(response.headers.get('Retry-After'));return response

class AnswerEngine:
    def __init__(self,*,client_factory=OpenRouterClient,sleeper=time.sleep,max_attempts=3,logger=LOG):
        if type(max_attempts) is not int or not 1<=max_attempts<=3:raise ValueError('Bounded attempts required')
        self.client_factory=client_factory;self.sleeper=sleeper;self.max_attempts=max_attempts;self.logger=logger

    def _finish(self,package,start,retrieval_ms,status,*,attempts=0,validation='NOT_RUN',error=None,delay=None,text=None,claims=(),request_id=None):
        event=Audit(request_id=request_id or uuid.uuid4().hex,intent=package.intent,action=package.action,model=MODEL,
            evidence_count=len(package.facts),evidence_ids=tuple(f.evidence_id for f in package.facts),status=status,
            attempts=attempts,retry_count=max(0,attempts-1),latency_ms=round((time.perf_counter()-start)*1000,3),
            retrieval_ms=round(retrieval_ms,3),validation=validation,error_code=error,
            retry_after_seconds=delay if delay is not None and math.isfinite(delay) else None)
        self.logger.info(json.dumps(event.model_dump(),sort_keys=True))
        return Answer(status=status,answer=text or STOP_TEXT[status],claims=claims,evidence=package.facts,audit=event)

    def _answer(self,prepare):
        start=time.perf_counter();request_id=uuid.uuid4().hex
        try:package=prepare()
        except (ValueError,KeyError,InvalidOperation):
            package=Package(status='NO_DATA',question='',mode='HELP',intent='UNKNOWN',action=None,scope='UAE')
            return self._finish(package,start,(time.perf_counter()-start)*1000,'VALIDATION_FAILED',validation='FAIL',error='INVALID_RETRIEVAL_CONTRACT',request_id=request_id)
        except Exception:
            # Storage/provider detail and sensitive inputs never enter diagnostics.
            package=Package(status='NO_DATA',question='',mode='HELP',intent='UNKNOWN',action=None,scope='UAE')
            return self._finish(package,start,(time.perf_counter()-start)*1000,'TEMPORARILY_UNAVAILABLE',error='RETRIEVAL_UNAVAILABLE',request_id=request_id)
        retrieval_ms=(time.perf_counter()-start)*1000
        if package.status not in ('ANSWER','PARTIAL_DATA'):
            return self._finish(package,start,retrieval_ms,package.status,request_id=request_id)
        if not package.facts:return self._finish(package,start,retrieval_ms,'NO_DATA',request_id=request_id)
        if (settings.OPENROUTER_MODEL,settings.SELECTED_MODEL,settings.MVP_PRODUCTION_MODEL)!=(MODEL,MODEL,MODEL) or settings.SELECTED_PROMPT_STRATEGY!='STRUCTURED_GROUNDED_SAFETY' or settings.SELECTED_PROMPT_REVISION!='provenance-v1' or settings.SELECTION_STATUS!='MVP_ENGINEERING_EXCEPTION' or settings.STRICT_CERTIFICATION is not False:
            return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',error='CONFIGURATION_MISMATCH',request_id=request_id)
        if not isinstance(settings.SELECTED_PROVIDER,dict) or settings.SELECTED_PROVIDER.get('provider')!='parasail/fp8':return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',error='CONFIGURATION_MISMATCH',request_id=request_id)
        try:prompt=messages(package)
        except ValueError:return self._finish(package,start,retrieval_ms,'VALIDATION_FAILED',validation='FAIL',error='CONTEXT_LIMIT',request_id=request_id)
        if not _PROVIDER_SLOT.acquire(blocking=False):return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',error='PROVIDER_BUSY',request_id=request_id)
        try:
            client=self.client_factory(timeout=30)
            observer=HeaderObserver(client.opener) if hasattr(client,'opener') else None
            if observer:client.opener=observer
            for attempt in range(1,self.max_attempts+1):
                try:
                    output_type=RichGenerated if package.mode=='DASHBOARD' else Generated
                    result=client.structured(model=MODEL,messages=prompt,output_type=output_type,**settings.SELECTED_PROVIDER)
                    output=output_type.model_validate(result['contract'])
                    answer,claims=render(package,output)
                except (InvalidStructuredOutput,ValueError,KeyError,TypeError):
                    return self._finish(package,start,retrieval_ms,'VALIDATION_FAILED',attempts=attempt,validation='FAIL',error='GENERATED_CONTRACT_INVALID',request_id=request_id)
                except ProviderError as exc:
                    delay=observer.delay if observer else getattr(client,'retry_after_seconds',None)
                    retryable=exc.code in ('RATE_LIMITED','PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE')
                    if not retryable or attempt==self.max_attempts or (delay is not None and delay>120):
                        return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',attempts=attempt,error=exc.code,delay=delay,request_id=request_id)
                    wait=max(2**attempt,delay or 0)
                    self.sleeper(wait);continue
                return self._finish(package,start,retrieval_ms,package.status,attempts=attempt,validation='PASS',text=answer,claims=claims,request_id=request_id)
        except ProviderError as exc:
            return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',error=exc.code,request_id=request_id)
        except Exception:
            return self._finish(package,start,retrieval_ms,'TEMPORARILY_UNAVAILABLE',error='PROVIDER_UNEXPECTED_ERROR',request_id=request_id)
        finally:_PROVIDER_SLOT.release()

    def answer_question(self,question,page_context=None,*,as_of=None):
        return self._answer(lambda:retrieval.retrieve(question,page_context,as_of=as_of)[0])

    def answer_request(self,request):
        """Preserve every Stage 14 suggestion field at the website boundary."""
        from intelligence.query.models import QueryRequest
        from intelligence.query.service import query
        typed=QueryRequest.model_validate(request)
        # Free-form requests retain the Stage 17 paraphrase handling. Catalog
        # requests must keep their exact selected ID, filters, limit and as_of.
        if typed.selected_question_id is None and not any(
            getattr(typed,k) for k in ('emirate','city','area','community','project',
                'building','developer','property_type','metric','time_expression',
                'comparison_targets','source_id')) and typed.limit==10:
            return self.answer_question(typed.question,typed.page_context,as_of=typed.as_of)
        return self._answer(lambda:retrieval.from_response(query(typed)))

    def generate_dashboard_summary(self,page_context,dashboard_facts,intelligence_context=None):
        return self._answer(lambda:retrieval.dashboard(page_context,dashboard_facts,intelligence_context))

def answer_question(question,page_context=None,**kwargs):
    return AnswerEngine().answer_question(question,page_context,**kwargs)

def generate_dashboard_summary(page_context,dashboard_facts,intelligence_context=None):
    return AnswerEngine().generate_dashboard_summary(page_context,dashboard_facts,intelligence_context)
