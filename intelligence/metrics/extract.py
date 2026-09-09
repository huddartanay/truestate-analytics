"""Pure Stage 12 extraction from validated Stage 11 + Stage 10 evidence."""
import re
from intelligence import config as cfg
from intelligence.entities.normalize import normalize
from intelligence.events.extract import clauses,associations,validate_input as validate_upstream
from intelligence.events import rules as event_rules
from intelligence.events.identity import UPSTREAM_KEY
from intelligence.errors import MetricExtractionError
from intelligence.schemas import MarketObservation,EventExtractionResult
from intelligence.metrics import rules as r
from intelligence.metrics.numbers import NUMBER,number_at
from intelligence.metrics.identity import result_id,observation_id,decimal_text


def _currency(text,start,end):
    found=[]
    for m in r.CURRENCY.finditer(text):
        gap=text[m.end():start] if m.end()<=start else text[end:m.start()] if m.start()>=end else 'INVALID'
        if not gap.strip():
            token=m.group().upper()
            found.append('AED' if token in ('DH','DHS','درهم','دراهم') else token)
    return found[0] if len(found)==1 else None


def _nearest(pattern,text,start,end):
    found=[]
    for m in pattern.finditer(text):
        distance=len(re.findall(r'\w+',text[m.end():start] if m.end()<=start else text[end:m.start()]))
        if distance<=8:
            found.append((distance,abs(m.start()-start),m))
    return min(found,key=lambda v:v[:2])[2] if found else None


def candidates(article,entities,upstream,version=cfg.METRIC_EXTRACTION_VERSION):
    identity=result_id(upstream.event_result_id,version)
    observations=[]; title_semantics=set()
    for field,text in (('TITLE',article.clean_title),('BODY',article.clean_body)):
        for left,right in clauses(text):
            while left<right and text[left].isspace(): left+=1
            while right>left and text[right-1].isspace(): right-=1
            clause=text[left:right]; normalized=normalize(clause)
            if not clause or len(clause)>640 or r.BLOCK.search(clause) or r.RANGE.search(clause) or event_rules.NEGATION.search(normalized):
                continue
            forecast=bool(event_rules.FORWARD.search(normalized) or re.search(r'\bnext (?:year|month|quarter)\b',normalized))
            nature='SOURCE_REPORTED_FORECAST' if forecast else 'OBSERVED'
            period=r.PERIOD.search(clause)
            bases=[name for name,pattern in r.BASES if pattern.search(clause)]
            if len(bases)>1: continue
            basis=bases[0] if bases else 'UNKNOWN'
            clause_basis=basis
            for number in NUMBER.finditer(clause):
                basis=clause_basis
                try: reported,value,scale,end=number_at(clause,number)
                except ValueError: continue
                start=number.start()
                if period and period.start()<=start<period.end(): continue
                currency=_currency(clause,start,end)
                after=clause[end:]; before=clause[:start]
                percent=bool(re.match(r'\s*(?:%|٪|percent\b|per cent\b)',after,re.I))
                price=_nearest(r.PRICE,clause,start,end)
                rent=_nearest(r.RENT,clause,start,end)
                yield_match=_nearest(r.YIELD,clause,start,end)
                transaction=_nearest(r.TRANSACTION,clause,start,end)
                # Select the numeric subject locally when several metric nouns
                # share a clause. Rental-price and rental-yield spans take
                # precedence over the shorter overlapping price/rent nouns.
                if rent and price and rent.start()<=price.start()<rent.end(): price=None
                if yield_match and rent and yield_match.start()<=rent.start()<yield_match.end(): rent=None
                anchors=[('price',price),('rent',rent),('yield',yield_match),('transaction',transaction)]
                anchors=[(name,m) for name,m in anchors if m]
                subject=min(anchors,key=lambda item:(item[1].end()>start,abs(start-item[1].end())))[0] if anchors else None
                price=price if subject=='price' else None
                rent=rent if subject=='rent' else None
                yield_match=yield_match if subject=='yield' else None
                transaction=transaction if subject=='transaction' else None
                metric=None;unit=None;direction='UNKNOWN';statistic='UNSPECIFIED'; rule='explicit-level-v1'
                if percent and scale=='ONE' and currency is None:
                    if yield_match and (rent is None or yield_match.start()<=rent.start()<=yield_match.end()):
                        metric='RENTAL_YIELD';unit='PERCENT'
                    elif rent or price:
                        anchor=rent or price
                        window=normalize(clause[max(0,min(anchor.start(),start)-40):max(anchor.end(),end)])
                        directions={name for name,pattern in event_rules.DIRECTIONS if pattern.search(window)}
                        signed=number.group().startswith(('+','-','−'))
                        if not directions and signed:
                            direction='INCREASE' if reported>0 else 'DECREASE' if reported<0 else 'STABLE'
                        elif len(directions)==1:
                            direction=next(iter(directions))
                            if reported<0 or (direction=='DECREASE' and number.group().startswith('+')): continue
                        else: continue
                        if direction=='STABLE' and value!=0: continue
                        if direction!='STABLE' and value==0: continue
                        if direction=='DECREASE' and value>=0: value=value.copy_negate()
                        metric='RENT_CHANGE_PCT' if rent else 'PRICE_CHANGE_PCT';unit='PERCENT';rule='explicit-change-v1'
                    else: continue
                elif currency is not None and not percent:
                    if value<0: continue
                    if transaction:
                        metric='TRANSACTION_VALUE';unit='CURRENCY_AMOUNT';rule='explicit-transaction-value-v1'
                    elif rent or price:
                        unit='CURRENCY_AMOUNT'
                        if re.search(r'\b(?:average|mean)\b',clause,re.I): statistic='AVERAGE'
                        elif re.search(r'\bmedian\b',clause,re.I): statistic='MEDIAN'
                        area=r.AREA.match(after)
                        if rent:
                            if area: continue
                            annual=bool(r.ANNUAL.search(clause));monthly=bool(r.MONTHLY.search(clause))
                            if annual and monthly: continue
                            metric='ANNUAL_RENT' if annual else 'MONTHLY_RENT' if monthly else 'RENTAL_PRICE'
                            if annual: basis='ANNUAL'
                            if monthly: basis='MONTHLY'
                        elif area:
                            squarefoot=bool(re.search(r'ft|feet|foot|psf',area.group(),re.I))
                            metric='SALE_PRICE_PER_SQFT' if squarefoot else 'SALE_PRICE_PER_SQM'
                            unit='CURRENCY_PER_SQFT' if squarefoot else 'CURRENCY_PER_SQM'
                        else:
                            metric='AVERAGE_SALE_PRICE' if statistic=='AVERAGE' else 'MEDIAN_SALE_PRICE' if statistic=='MEDIAN' else 'SALE_PRICE'
                    else: continue
                elif transaction and not percent and value>=0 and value==value.to_integral_value():
                    # Counts require an adjacent transaction noun, or an explicit count/volume subject.
                    if not (re.match(r'\s*(?:property\s+)?transactions?\b|\s*معاملة عقارية',after,re.I) or
                            re.search(r'\b(?:transaction (?:count|volume)|(?:count|number|volume) of (?:property )?transactions)\b',before,re.I)):
                        continue
                    metric='TRANSACTION_VOLUME';unit='TRANSACTIONS';rule='explicit-transaction-count-v1'
                if not metric: continue
                expected_event={'PRICE_CHANGE_PCT':'PRICE_CHANGE','RENT_CHANGE_PCT':'RENT_CHANGE',
                    'TRANSACTION_VALUE':'TRANSACTION_VALUE','TRANSACTION_VOLUME':'TRANSACTION_VOLUME'}.get(metric)
                links=associations(article,entities,field,left,right,left+start,left+end)
                # Unsplit clauses with competing places are ambiguous. Retain
                # no observation instead of attaching the numeral to both.
                places=[link.entity_id for link in links]
                if len({p for p in places if p.startswith('emirate:')})>1 or len({p for p in places if p.startswith(('area:','community:'))})>1:
                    continue
                event_ids=tuple(sorted(e.event_id for e in upstream.events if e.source_field==field and
                    left<=e.start_offset<e.end_offset<=right and
                    (e.event_type.value==expected_event or (forecast and e.event_type.value=='MARKET_OUTLOOK'))))
                # Numeric changes absent from Stage 11 only bypass event gating for
                # explicit forecast/historical/signed grammar; no upstream labels are altered.
                if metric in ('PRICE_CHANGE_PCT','RENT_CHANGE_PCT') and not event_ids:
                    if not forecast and not event_rules.HISTORICAL.search(normalized) and not number.group().startswith(('+','-','−')): continue
                    rule='explicit-forecast-change-v1' if forecast else 'explicit-historical-change-v1' if event_rules.HISTORICAL.search(normalized) else 'explicit-signed-change-v1'
                property_matches=[(name,_nearest(pattern,clause,start,end)) for name,pattern in r.PROPERTIES]
                property_matches=[(name,m) for name,m in property_matches if m]
                prop=min(property_matches,key=lambda item:abs(item[1].start()-start))[0] if property_matches else 'UNKNOWN'
                # Qualified amounts retain their inequality/approximation. Avoid 'year over year'.
                qualifier_window=clause[max(0,start-30):start]
                qualifiers=[name for name,pattern in r.QUALIFIERS for match in pattern.finditer(qualifier_window)
                            if not r.CURRENCY.sub('',qualifier_window[match.end():]).strip()]
                if len(set(qualifiers))>1: continue
                qualifier=qualifiers[0] if qualifiers else 'EXACT'
                data=dict(metric_result_id=identity,metric=metric,value=decimal_text(value),reported_value=decimal_text(reported),
                    reported_value_text=clause[start:end],scale=scale,currency=currency,unit=unit,period_basis=basis,
                    reported_period_text=period.group() if period else None,property_type=prop,nature=nature,
                    qualifier=qualifier,statistic=statistic,direction=direction,rule_id=rule,source_field=field,
                    start_offset=left,end_offset=right,numeric_start=left+start,numeric_end=left+end,matched_text=clause,
                    confidence='HIGH' if field=='TITLE' else 'MEDIUM',entity_links=[l.model_dump(mode='json') for l in links],
                    associated_event_ids=list(event_ids))
                semantic=(metric,decimal_text(value),currency,unit,basis,data['reported_period_text'],prop,nature,qualifier,statistic,
                          tuple(l.entity_id for l in links),normalize(clause))
                if field=='BODY' and semantic in title_semantics: continue
                if field=='TITLE': title_semantics.add(semantic)
                observations.append(MarketObservation(observation_id=observation_id(data),**data))
                if len(observations)>256: raise MetricExtractionError('Observation limit exceeded')
    return tuple(sorted(observations,key=lambda o:(o.source_field!='TITLE',o.start_offset,o.numeric_start,o.metric.value,o.observation_id)))


def validate_observations(observations,article,entities,upstream,version=cfg.METRIC_EXTRACTION_VERSION):
    for o in observations:
        MarketObservation.model_validate(o.model_dump(mode='json'))
        text=article.clean_title if o.source_field=='TITLE' else article.clean_body
        if text[o.start_offset:o.end_offset]!=o.matched_text or o.metric_result_id!=result_id(upstream.event_result_id,version):
            raise MetricExtractionError('Metric evidence or context mismatch')
        if any(l.mention_index>=len(entities.mentions) or entities.mentions[l.mention_index].entity_id!=l.entity_id for l in o.entity_links):
            raise MetricExtractionError('Metric entity association mismatch')
        expected_links=associations(article,entities,o.source_field,o.start_offset,o.end_offset,o.numeric_start,o.numeric_end)
        if o.entity_links != expected_links:
            raise MetricExtractionError('Metric entities must match clause/proximity evidence')
        if not set(o.associated_event_ids)<={e.event_id for e in upstream.events if e.source_field==o.source_field and o.start_offset<=e.start_offset<e.end_offset<=o.end_offset}:
            raise MetricExtractionError('Metric event association mismatch')


def validate_input(article,entities,upstream,stage9,stage8):
    validate_upstream(article,entities,stage9,stage8)
    if not isinstance(upstream,EventExtractionResult) or upstream.extraction_id!=entities.extraction_id:
        raise MetricExtractionError('Stored Stage 11 context required')
    if any(getattr(upstream,k)!=getattr(entities,k) for k in UPSTREAM_KEY+('group_id','location_scope')):
        raise MetricExtractionError('Stage 11 lineage mismatch')
    EventExtractionResult.model_validate(upstream.model_dump(mode='json'))
    for event in upstream.events:
        text=article.clean_title if event.source_field=='TITLE' else article.clean_body
        if any(link.mention_index>=len(entities.mentions) or entities.mentions[link.mention_index].entity_id!=link.entity_id for link in event.entity_links):
            raise MetricExtractionError('Stage 11 entity evidence mismatch')
        if text[event.start_offset:event.end_offset]!=event.matched_text:
            raise MetricExtractionError('Stage 11 evidence mismatch')


def extract(article,entities,upstream,stage9,stage8,*,version=cfg.METRIC_EXTRACTION_VERSION):
    validate_input(article,entities,upstream,stage9,stage8)
    result=candidates(article,entities,upstream,version)
    validate_observations(result,article,entities,upstream,version)
    return result
