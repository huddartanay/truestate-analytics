"""Current article retrieval alongside the unchanged historical query path.

Runs only in the isolated answer worker. Registered scope/actions still come
from Stage 14. Unregistered subject lookup requires exact processed article
text, UAE/RE acceptance and a narrow question form; it cannot borrow UAE scope
for foreign/general questions. No raw feed or model knowledge is consulted.
"""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import re
from intelligence import config as cfg
from intelligence.answer_engine import retrieval as old
from intelligence.answer_engine.models import Package,MAX_FACTS,MAX_SUMMARY_FACTS
from intelligence.query.models import QueryRequest,Status
from intelligence.query.router import route,FOREIGN,GENERAL
from intelligence.query.service import query
from intelligence.query.actions import execute
from intelligence.query.registry import ACTIONS
from intelligence.query.resolution import entities
from intelligence.entities.registry import REGISTRY
from intelligence.production.store import readonly
from intelligence.sources.registry import enabled_sources
from intelligence.current import cache

ARTICLE_ACTIONS=frozenset(('get_latest_news','get_news_by_emirate','get_news_by_area','get_latest_projects',
    'get_developer_activity','get_regulations','get_infrastructure_activity','get_market_snapshot',
    'get_latest_events','get_supply_activity','get_demand_activity','get_off_plan_activity',
    'get_ready_property_activity','get_investor_activity','get_foreign_investment_activity','get_market_outlook','get_source_details'))

def subject(request):
    if request.selected_question_id:return None
    text=request.question.strip().rstrip('?.!')
    if re.search(FOREIGN+'|'+GENERAL,text,re.I) or re.search(r'ignore|instructions|prompt|reveal|[;{}]|--',text,re.I):return None
    m=re.fullmatch(r'(?:what is|tell me about|latest (?:news|updates) (?:on|about))\s+([\w -]{4,100})',text,re.I)
    if not m:return None
    name=m[1].strip()
    if len(name.split())<2 or re.search(r'\b(?:market|prices?|rents?|weather|guarantee|investment advice)\b',name,re.I):return None
    return name

def eligible(request):
    d=route(request)
    # Explicit historical date/window, movement basis, metrics and comparisons
    # stay on the persistent historical path, even for otherwise current actions.
    if d.scope_status=='IN_SCOPE':
        return d.action_id in ARTICLE_ACTIONS and not d.filters.movement_basis and d.filters.time.expression in ('LATEST','TODAY','THIS_WEEK','THIS_MONTH')
    return d.reason_code in ('OUTSIDE_TRUESTATE_DOMAIN','UNRESOLVED_LOCATION','UNRECOGNIZED_SUPPORTED_ACTION') and bool(subject(request))

@contextmanager
def database(path):
    before=cfg.DB_PATH;cfg.DB_PATH=path
    try:yield
    finally:cfg.DB_PATH=before

def normalized(s):return re.sub(r'[^\w]+',' ',s.casefold()).strip()

def excerpt(body,term=None):
    if re.search(r'ignore.{0,40}instructions|system prompt|reveal.{0,30}key|hacked|<script',body,re.I):return None
    parts=re.split(r'\n+|(?<=[.!?])\s+',body)
    part=next((s for s in parts if term and normalized(term) in normalized(s)),None)
    part=part or next((s for s in parts if len(s)>70),None)
    if not part:return None
    return part[:500]+('…' if len(part)>500 else '')

def current_package(request,build,mode='HELP'):
    d=route(request);term=subject(request) if d.scope_status!='IN_SCOPE' else None
    if term:
        request=request.model_copy(update={'question':'Latest UAE real-estate news','selected_question_id':None})
    with database(build.path):
        response=query(request.model_copy(update={'limit':50}))
        if response.route.action_id=='get_market_snapshot':
            decision=response.route.model_copy(update={'action_id':'get_latest_news','intent':ACTIONS['get_latest_news'].supported_intents[0],'expected_output_type':'NewsResult'})
            response=response.model_copy(update={'route':decision,'result':execute(decision,request.as_of)})
        package=old.from_response(response,'DASHBOARD',max_facts=MAX_SUMMARY_FACTS)
        # Filter the full bounded action result BEFORE applying the answer cap.
        # Converting one record at a time reuses Stage 16's lineage adapter;
        # otherwise unrelated early rows could hide a later exact subject match.
        facts=[]
        records=response.result.records+tuple(r for section in response.result.sections for r in section.records)
        for record in records:
            if record.value is not None:continue
            evidence=tuple(e for e in response.result.evidence if e.reference_id in record.evidence_ids)
            single=response.result.model_copy(update={'status':Status.AVAILABLE,'answer_policy':'EVIDENCE_ONLY',
                'records':(record,),'sections':(),'evidence':evidence,'result_count':1,'evidence_count':len(evidence),
                'source_disagreement':False,'truncated':False})
            facts.extend(old.from_response(response.model_copy(update={'result':single}),'DASHBOARD').facts)
    now=request.as_of or datetime.now(timezone.utc)
    with readonly(build.path) as db:
        articles={r['metric_result_id']:dict(r) for r in db.execute('SELECT * FROM intelligence_news WHERE build_id=?',(build.build_id,))}
    residual=request.question.casefold()
    for eid in entities(residual):
        ent=REGISTRY.entities[eid]
        for name in (ent.canonical_name,*(a.text for a in ent.aliases)):residual=residual.replace(name.casefold(),' ')
    stop=set('what is are the latest current new recent news updates happening in on for about show me tell projects project real estate property developments developer activity regulations regulation laws infrastructure market summary overview outlook sources reports report which how here uae dubai abu dhabi sharjah rak ras al khaimah today this week month supply demand off plan ready foreign investment investors'.split())
    terms=[t for t in re.findall(r'\b[a-z]{3,}\b',residual) if t not in stop] if not term else []
    candidates=[];seen=set();trust={s.source_id:s.trust_score for s in enabled_sources()}
    for fact in facts:
        if fact.value is not None or not fact.lineage:continue
        e=fact.lineage[0];a=articles.get(e.metric_result_id)
        if a is None or e.metric_result_id in seen:continue
        if re.search(r'ignore.{0,40}instructions|system prompt|reveal.{0,30}key|hacked',a['clean_title'],re.I):continue
        # Missing dates never become fresh; future dates cannot masquerade as current.
        if not e.published_at or not now-timedelta(days=30)<=e.published_at<=now:continue
        content=normalized(a['clean_title']+' '+a['clean_body'])
        title_scopes={REGISTRY.entities[eid].emirate.value for eid in entities(a['clean_title']) if REGISTRY.entities[eid].emirate is not None}
        requested=response.route.filters.emirate.value
        if requested not in ('UAE_WIDE','MULTI_EMIRATE','UNKNOWN') and title_scopes and requested not in title_scopes:continue
        if term and normalized(term) not in content:continue
        if terms and not re.search(r'\b'+r'\s+'.join(re.escape(t) for t in terms)+r'\b',content):continue
        seen.add(e.metric_result_id)
        candidates.append(fact.model_copy(update={'origin':'CURRENT_RSS','title':fact.title or a['clean_title'],'excerpt':excerpt(a['clean_body'],term)}))
    candidates.sort(key=lambda f:(f.published_at or '',trust.get(f.lineage[0].source_id,0),f.identity),reverse=True)
    bound=5 if mode=='DASHBOARD' else MAX_FACTS
    selected=candidates[:bound]
    facts=tuple(f.model_copy(update={'evidence_id':'E'+str(i+1)}) for i,f in enumerate(selected))
    return package.model_copy(update={'mode':mode,'question':request.question if not term else 'What is '+term+'?',
        'facts':facts,'status':'ANSWER' if facts else 'NO_DATA','missing':(),
        'truncated':len(candidates)>bound,'source_disagreement':False})

def help_package(request,current=None):
    request=QueryRequest.model_validate(request)
    historical=old.from_response(query(request))
    if not eligible(request):return historical
    state=current if current is not None else cache.ensure()
    if state:
        package=current_package(request,state[0])
        if package.facts:return package.model_copy(update={'question':request.question})
    # Unknown named subjects must never fall back to unrelated historical news.
    if subject(request) and route(request).scope_status!='IN_SCOPE':
        return historical.model_copy(update={'status':'NO_DATA'})
    # Apply the same recency, headline-location and question-text checks to
    # historical fallback news; never substitute unrelated article evidence.
    if historical.facts:
        import json
        from intelligence.production.store import inspect_database
        try:
            path=cfg.DB_PATH
            prior=inspect_database(path,json.loads(path.with_name('manifest.json').read_text()))
            filtered=current_package(request,prior)
            return filtered.model_copy(update={'question':request.question,'facts':tuple(f.model_copy(update={'origin':'INTELLIGENCE','excerpt':None}) for f in filtered.facts)})
        except (ValueError,OSError):return historical.model_copy(update={'status':'NO_DATA','facts':()})
    return historical

def summary_package(context,facts,current=None):
    historical=old.dashboard(context,facts,summary_limit=MAX_SUMMARY_FACTS)
    if historical.status in ('OUT_OF_SCOPE','AMBIGUOUS','UNSUPPORTED','NOT_COMPARABLE'):return historical
    ctx=old.context(context)
    req=QueryRequest(question='UAE market outlook' if ctx.page_type=='OUTLOOK' else 'How is the property market here?',page_context=ctx,limit=50)
    state=current if current is not None else cache.ensure()
    fresh=current_package(req,state[0],'DASHBOARD') if state else None
    if not fresh or not fresh.facts:return historical
    # Preserve trusted dashboard facts and atomic historical groups. Current
    # articles receive a reserved, bounded share without replacing calculations.
    current_articles={f.lineage[0].article_id for f in fresh.facts}
    prior=[f for f in historical.facts if f.value is not None or not f.lineage or f.lineage[0].article_id not in current_articles]
    unique=[];seen=set()
    for f in prior:
        key=f.lineage[0].article_id if f.value is None and f.lineage else None
        if key and key in seen:continue
        if key:seen.add(key)
        unique.append(f)
    trusted=[f for f in unique if f.origin=='DASHBOARD']
    fresh_facts=fresh.facts[:MAX_SUMMARY_FACTS-len(trusted)]
    other=[f for f in unique if f.origin!='DASHBOARD']
    room=MAX_SUMMARY_FACTS-len(trusted)-len(fresh_facts)
    selected,truncated=old._bounded(other,limit=room) if room else ((),bool(other))
    combined=tuple(f.model_copy(update={'evidence_id':'E'+str(i+1)}) for i,f in enumerate((*trusted,*selected,*fresh_facts)))
    groups={}
    for f in combined:
        if f.value is not None and f.rank is None:groups.setdefault(old._group(f),set()).add(f.value)
    conflict=any(len(v)>1 for v in groups.values())
    missing=tuple('historical '+m+' coverage' for m in historical.missing)
    if historical.source_disagreement and not conflict:missing+=('additional conflicting source evidence',)
    return Package.model_validate(historical.model_dump()|{'facts':combined,'status':'PARTIAL_DATA' if missing or truncated or conflict else 'ANSWER',
        'missing':missing,'source_disagreement':conflict,'truncated':historical.truncated or truncated})
