"""Business-facing prose built only from the verified answer's immutable facts.

Model drafts and backend diagnostic text are never displayed. Technical IDs,
provenance, and exact validation results remain on the original Answer object.
"""
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import html,re
from intelligence.production.store import safe_url

DISPLAY_ZONE=ZoneInfo('Asia/Dubai')
TECH=re.compile(r'\b(?:RSS|Stage\s+\d+|Qwen|OpenRouter|CURRENT_RSS|SOURCE_REPORTED|SYSTEM_CALCULATED|evidence package|build ID|retrieval|pipeline|processed_at|provider|validation|cache|evidence ID|production classification)\b',re.I)
MESSAGES={
 'NO_DATA':"I couldn't find enough verified information to answer that reliably. Try a different location or one of the suggested questions below.",
 'OUT_OF_SCOPE':'I can help with UAE property markets, projects, prices, rents, transactions and recent real-estate developments.',
 'AMBIGUOUS':'Please include the UAE location, project or type of market information you would like to explore.',
 'UNSUPPORTED':"I can't answer that request reliably. Try asking about a UAE property market or a recent development.",
 'NOT_COMPARABLE':"The available figures cover different conditions or reporting periods, so a reliable comparison isn't possible.",
 'TEMPORARILY_UNAVAILABLE':'The Market Assistant is temporarily unavailable. Please try again shortly.',
 'VALIDATION_FAILED':"I couldn't verify that answer confidently enough to show it. Please try rephrasing your question."}

def clean(value):
    value=re.sub(r'\[E\d+\]|[\r\n`]|\bE\d+\b',' ',html.unescape(str(value or '')))
    value=re.sub(r'\b20\d{2}-\d\d-\d\dT[\d:.]+(?:Z|[+-]\d\d:\d\d)?','',value)
    if TECH.search(value):return ''
    return re.sub(r'([\[\]_*<>])',r'\\\1',html.unescape(value)).strip()

def publisher(value):
    if value.startswith('Khaleej Times'):return 'Khaleej Times'
    if value.startswith('Emirates 24'):return 'Emirates 24/7'
    if value.startswith('BBC News'):return 'BBC News'
    if value.startswith('CNBC'):return 'CNBC'
    return clean(value.split(' — ')[0]) or 'Publisher'

def parsed(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result.astimezone(DISPLAY_ZONE) if result.tzinfo else result.replace(tzinfo=DISPLAY_ZONE)
    except (ValueError,TypeError,AttributeError):return None

def date_label(value):
    d=parsed(value)
    return f'{d.day} {d:%b %Y}' if d else ''

def freshness(value,now=None):
    d=parsed(value)
    if not d:return ''
    now=(now or datetime.now(DISPLAY_ZONE)).astimezone(DISPLAY_ZONE)
    when='today' if d.date()==now.date() else 'yesterday' if d.date()==(now-timedelta(days=1)).date() else None
    return f'Market intelligence updated {when} at {d:%I:%M %p}'.replace('at 0','at ')+' (UAE time)' if when else 'Market intelligence updated '+date_label(value)

METRICS={
 'PRICE_CHANGE_PCT':'sale prices','SALE_PRICE_CHANGE':'sale prices','SALE_PRICE_PER_SQFT':'sale price per square foot',
 'SALE_PRICE_PER_SQM':'sale price per square metre','SALE_PRICE':'sale price','AVERAGE_SALE_PRICE':'average sale price',
 'MEDIAN_SALE_PRICE':'median sale price','RENT_CHANGE_PCT':'rents','RENTAL_PRICE':'rents','ANNUAL_RENT':'annual rent',
 'MONTHLY_RENT':'monthly rent','RENTAL_YIELD':'rental yield','TRANSACTION_VALUE':'transaction value',
 'TRANSACTION_VOLUME':'transaction volume','PRICE_GROWTH':'price growth'}

def number(value):
    try:return format(Decimal(value),',f')
    except Exception:return clean(value)

def period_label(value):
    if not value:return ''
    m=re.fullmatch(r'(20\d{2})-(\d\d)',value)
    if m:
        try:return datetime(int(m[1]),int(m[2]),1).strftime('%B %Y')
        except ValueError:pass
    return clean(value.replace('-Q',' Q'))

def attribution(f):
    return 'Based on TruEstate analytics' if f.provenance=='SYSTEM_CALCULATED' else 'According to '+publisher(f.source)

def numeric(f):
    key=(f.metric or '').upper().replace(' ','_')
    metric=METRICS.get(key,clean((f.metric or 'reported figure').replace('_',' ').lower()))
    statistic={'AVERAGE':'average','MEAN':'average','MEDIAN':'median','TOTAL':'total'}.get(f.statistic,clean((f.statistic or '').replace('_',' ').lower()))
    if statistic and statistic not in ('unspecified','unknown') and statistic not in metric:metric=statistic+' '+metric
    location=clean(f.location);period=period_label(f.period)
    amount=number(f.value);percent=f.unit in ('PERCENT','percent','%')
    unit={'CURRENCY_AMOUNT':'AED' if f.currency=='AED' else clean(f.currency or ''),
          'CURRENCY_PER_SQFT':clean(f.currency or '')+' per square foot',
          'CURRENCY_PER_SQM':clean(f.currency or '')+' per square metre',
          'COUNT':'','transactions':'transactions','AED/m²':'AED per square metre','AED/sqft':'AED per square foot'}.get(f.unit,clean(f.unit or ''))
    money=re.fullmatch(r'(AED|USD|EUR|GBP)(?: (billion|million))?',unit)
    value=amount+'%' if percent else (money[1]+' '+amount+(' '+money[2] if money[2] else '') if money else amount+(' '+unit if unit else ''))
    plural=metric.endswith('s')
    verb='were' if plural else 'was'
    comparison={'YOY':' compared with the same period a year earlier','MOM':' compared with the previous month','QOQ':' compared with the previous quarter','YTD':' for the year to date'}.get(f.basis,'')
    if f.basis and not comparison and f.basis not in ('UNSPECIFIED','UNKNOWN'):comparison=' ('+clean(f.basis.replace('_',' ').lower())+')'
    if percent and ('CHANGE' in key or f.kind in ('MOVEMENT','RANKING')):
        change=Decimal(f.value);direction='higher' if change>0 else 'lower' if change<0 else 'unchanged'
        amount=number(str(abs(change)))+'%'
        text=f'{location}: {metric.capitalize()} {verb} {amount} {direction}{comparison}' if change else f'{location}: {metric.capitalize()} {verb} unchanged{comparison}'
    else:text=f'{location}: {metric.capitalize()} '+(('are' if plural else 'is')+' forecast at ' if f.nature=='SOURCE_REPORTED_FORECAST' else verb+' ')+value+comparison
    if f.nature=='SOURCE_REPORTED_FORECAST' and 'forecast' not in text:text='The published forecast for '+text
    if period:text+=' for '+period
    text+='.'
    if f.rank is not None:text+=' Position in this comparison: '+str(f.rank)+'.'
    if not period:text+=' The reporting period is not specified.'
    if f.property_type and f.property_type not in ('UNKNOWN','UNSPECIFIED'):text+=' Property type: '+clean(f.property_type.replace('_',' ').lower())+'.'
    text+=' '+attribution(f)+'.'
    if f.nature=='SOURCE_REPORTED_FORECAST':text+=' This is an expectation, not an observed outcome.'
    return text

def article(f):
    title=clean(f.title) or 'Property market update'
    detail=clean(f.excerpt)
    if re.search(r'ignore|instructions|system prompt|reveal|hacked',title+' '+detail,re.I):detail='';title='Property market update'
    source=publisher(f.source);date=date_label(f.published_at)
    url=next((safe_url(e.article_url) for e in f.lineage if safe_url(e.article_url)),None)
    meta=source+(' · '+date if date else '')+(' · [View source]('+url+')' if url else '')
    return '**'+title+'**'+('\n\n'+detail if detail else '')+'\n\n'+meta

def public_sources(answer):
    result=[];seen=set()
    for f in answer.evidence:
        if not f.lineage:
            key=(publisher(f.source),f.reference)
            if key not in seen:result.append({'source':publisher(f.source),'article_title':None,'url':None,'published_at':None,'period':period_label(f.period)});seen.add(key)
        for e in f.lineage:
            url=safe_url(e.article_url);key=(e.source_id,url or e.article_id)
            if key in seen:continue
            seen.add(key);result.append({'source':publisher(e.source_name),'article_title':clean(f.title),'url':url,'published_at':date_label(e.published_at.isoformat()) if e.published_at else None,'period':None})
    return tuple(result)

def business_answer(answer,*,summary=False):
    facts=list(answer.evidence);signals=[f for f in facts if f.value is not None]
    seen=set();stories=[]
    for f in facts:
        if f.value is not None:continue
        identity=f.lineage[0].article_id if f.lineage else f.identity
        if identity in seen:continue
        seen.add(identity);stories.append(f)
    current=[f for f in stories if f.origin=='CURRENT_RSS']
    locations=list(dict.fromkeys(clean(f.location) for f in facts));location=locations[0] if len(locations)==1 else 'the selected UAE markets'
    lines=[]
    if summary:
        lines=['### Market at a glance']
        parts=[]
        if signals:parts.append('figures for '+', '.join(dict.fromkeys(METRICS.get((f.metric or '').upper(),clean((f.metric or 'market').replace('_',' ').lower())) for f in signals)))
        if current:parts.append('recent property reporting')
        lines.append('This market update for '+location+' brings together '+' and '.join(parts or ['the available property reporting'])+'. The figures retain their own reporting periods, while the developments below reflect the cited publisher reports.')
    elif answer.audit.intent=='SOURCE_DETAILS':
        names=list(dict.fromkeys(publisher(f.source) for f in facts))
        lines.append('The available reporting for '+location+' comes from '+', '.join(names)+'.')
    elif signals:
        lines.append(numeric(signals[0]))
    elif stories:
        lines.append('Here '+('is the latest reported development' if len(stories)==1 else 'are the latest reported developments')+' for '+location+'.')
    if answer.status=='PARTIAL_DATA':lines.append('Some requested information is not available. The update below covers what can be supported by the available sources.')
    # Retain disagreement without combining conflicting measurements.
    from intelligence.answer_engine.retrieval import _group
    groups={}
    for f in signals:
        if f.rank is None:groups.setdefault(_group(f),set()).add(f.value)
    if any(len(values)>1 for values in groups.values()):lines.append('Sources report different figures. Their values are shown separately and have not been averaged.')
    details=signals if summary else signals[1:]
    if details:lines+=['### Key market signals' if summary else '### Key details']+['- '+numeric(f) for f in details]
    if summary:
        historical=[f for f in stories if f.origin!='CURRENT_RSS']
        if current and historical:lines+=['### Market context']+[article(f) for f in historical]
        if current:lines+=['### What’s happening now','Recent reporting adds the property developments below to the market picture. Each item includes its publisher and publication date where available.']
        watch=[]
        if any('RENT' in (f.metric or '').upper() for f in signals):watch.append('Watch for the next comparable rental report before drawing a conclusion about the direction of rents.')
        if any('PRICE' in (f.metric or '').upper() for f in signals):watch.append('Watch whether the next price report covers the same location, property type and period before comparing figures.')
        if current:watch.append('Follow subsequent announcements on the developments below; a launch announcement does not establish completion.')
        if any(f.nature=='SOURCE_REPORTED_FORECAST' for f in facts):watch.append('Compare published expectations with actual outcomes as new reports become available.')
        if watch:lines+=['### What to watch']+['- '+w for w in watch[:4]]
        projects=[f for f in current if re.search(r'project|development|launch',f.title or '',re.I)][:4]
        news=[f for f in (current or stories) if f not in projects][:5]
        if projects:lines+=['### Projects & developments']+[article(f) for f in projects]
        if news:lines+=['### Latest property news']+[article(f) for f in news]
    elif stories:lines+=['### Latest developments']+[article(f) for f in stories]
    return '\n\n'.join(lines)
