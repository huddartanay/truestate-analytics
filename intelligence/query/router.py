"""Precision-first lexical router. Scope rejection always precedes catalog/action lookup."""
import re
from intelligence.enums import Emirate,PropertyType,MetricType
from intelligence.entities.registry import REGISTRY
from intelligence.query.models import QueryRequest,RouteDecision,Filters,Intent
from intelligence.query.registry import ACTIONS
from intelligence.query.resolution import entities,context_ids,resolve_one,time_filter

FOREIGN=r'\b(?:singapore|london|uk|united kingdom|us (?:housing|real estate|mortgage|property|rents?|market)|usa|united states|american|australia|australian|europe|european|india|indian|saudi|riyadh|qatar|bahrain|paris|france|canada|china|new york|tokyo|japan|germany|berlin|brazil|south africa|egypt|canadian|chinese|japanese|german|british|french|kenya|nairobi|pakistan|turkey|russia|spain|portugal|italy|malaysia|indonesia|thailand|new zealand|hong kong)\b'
GENERAL=r'\b(?:stocks?|crypto|bitcoin|weather|sports?|cricket|football|politics|coding|code|python|sql|career|study abroad|medical|headache|restaurants?|tourism|holiday|travel|quantum|capital of|tell me about ai|gold|silver|petrol|gasoline|bread|cars?|iphone|phones?|groceries|medicine|elections?)\b'
PROPERTY=r'\b(?:real[ -]estate|propert(?:y|ies)|housing|homes?|villas?|apartments?|rents?|rental|yields?|transactions?|off[ -]?plan|ready[ -]propert|supply|demand|investors?|investment|regulations?|projects?|launches|developers?|prices?|market|areas?|community|communities|buildings?)\b'

def stopped(status,reason):
    return RouteDecision(scope_status=status,intent=Intent(status),reason_code=reason,confidence='LOW')

def route(request):
    request=QueryRequest.model_validate(request)
    text=request.question.lower().replace('’',"'")
    if re.search(FOREIGN,text) or re.search(GENERAL,text):return stopped('OUT_OF_SCOPE','OUTSIDE_TRUESTATE_DOMAIN')
    if re.search(r'(?:\bor\s+1\s*=\s*1|;|--|/\*|\bdrop\s+table\b)',text):return stopped('UNSUPPORTED','UNSAFE_QUERY_SYNTAX')
    if re.search(r'\b(?:guarantee|guaranteed|predict exactly|exactly what|should i buy|convert|recalculate|calculate)\b',text):return stopped('UNSUPPORTED','UNSUPPORTED_PREDICTION_OR_ADVICE')
    explicit=entities(text)
    try:
        request_ids=context_ids(request)
        page_ids=context_ids(request.page_context)
    except ValueError as exc:return stopped('AMBIGUOUS',str(exc))
    # Unregistered place names must never silently become UAE-wide evidence.
    for location in re.findall(r'\b(?:in|across|within|around)\s+([^?.,!]+)',text):
        location=location.strip()
        if not entities(location) and not re.match(r'(?:q[1-4]\b|20\d{2}\b|the (?:last|current|property|real)|this |last |real[ -]estate|property|housing)',location):
            return stopped('AMBIGUOUS','UNRESOLVED_LOCATION')
    # Foreign/general content cannot borrow scope from page context or a catalog ID.
    geo=bool(explicit or request_ids or page_ids)
    if re.search(r'\b(?:marina|downtown)\b',text) and not any('marina' in e or 'downtown' in e for e in explicit):return stopped('AMBIGUOUS','UNRESOLVED_ENTITY')
    if 'here' in text and not geo and re.search(r'prices?|rents?|market|property',text):return stopped('AMBIGUOUS','LOCATION_REQUIRED')
    property_scope=bool(re.search(PROPERTY,text))
    if not geo and not re.search(r'real[ -]estate|propert|housing|homes?|villas?|apartments?|rents?|rental|off[ -]?plan',text):property_scope=False
    website=bool(re.search(r'\btruestate\b',text))
    contextual=bool(geo and re.search(r'\b(?:news|updates|happening|new|compare|vs|events|rules|analysis|overview)\b',text))
    if not(property_scope or website or contextual):return stopped('OUT_OF_SCOPE','OUTSIDE_TRUESTATE_DOMAIN')
    if 'infrastructure' in text and not re.search(r'real[ -]estate|property|housing',text): return stopped('OUT_OF_SCOPE','PROPERTY_CONTEXT_REQUIRED')
    if re.search(r'\b(?:explain|help|navigate|how to use)\b',text) and website:return stopped('UNSUPPORTED','WEBSITE_EVIDENCE_NOT_SUPPLIED')
    if re.search(r'\b(?:marina|downtown)\b',text) and not any('marina' in e or 'downtown' in e for e in explicit):return stopped('AMBIGUOUS','UNRESOLVED_ENTITY')
    selected=None
    if request.selected_question_id:
        from intelligence.query.catalog import QUESTIONS,render
        selected=QUESTIONS.get(request.selected_question_id)
        if selected is None or not selected.enabled:return stopped('UNSUPPORTED','UNKNOWN_QUESTION_ID')
        try:
            bindings={}
            if request.comparison_targets:
                targets_for_template=tuple(resolve_one(v) for v in request.comparison_targets)
                kind='emirate' if all(REGISTRY.entities[e].entity_type.value=='EMIRATE' for e in targets_for_template) else 'area'
                bindings={kind+'_'+str(i):REGISTRY.entities[e].canonical_name for i,e in enumerate(targets_for_template,1)}
            expected=render(selected,request.page_context,bindings)
        except ValueError:return stopped('AMBIGUOUS','QUESTION_CONTEXT_REQUIRED')
        if expected.casefold()!=request.question.casefold():return stopped('UNSUPPORTED','SELECTED_QUESTION_MISMATCH')
    ids=explicit or request_ids or page_ids
    explicit_used=bool(explicit or request_ids)
    page_used=bool(not explicit_used and page_ids)
    if explicit and request_ids and set(explicit)!=set(request_ids):return stopped('AMBIGUOUS','CONFLICTING_EXPLICIT_CONTEXT')
    if 'here' in text and not ids:return stopped('AMBIGUOUS','LOCATION_REQUIRED')
    comparing=bool(re.search(r'\b(?:compare|versus|vs)\b',text))
    try:
        targets=tuple(resolve_one(x) for x in request.comparison_targets) if request.comparison_targets else ids if comparing else ()
    except ValueError:return stopped('AMBIGUOUS','UNRESOLVED_COMPARISON_TARGET')
    if comparing and (len(targets)!=2 or len(set(targets))!=2):return stopped('AMBIGUOUS','TWO_EXPLICIT_TARGETS_REQUIRED')
    if not comparing and len({REGISTRY.entities[e].emirate for e in ids if REGISTRY.entities[e].emirate})>1:return stopped('AMBIGUOUS','MULTIPLE_LOCATIONS_REQUIRE_COMPARISON')
    scope=next((REGISTRY.entities[e].emirate for e in ids if REGISTRY.entities[e].emirate),Emirate.UAE_WIDE)
    entity_ids=tuple(e for e in ids if REGISTRY.entities[e].entity_type.value not in ('COUNTRY','EMIRATE'))
    if explicit and 'country:uae' in explicit:scope=Emirate.UAE_WIDE;entity_ids=()
    props=[p for p in PropertyType if p.value not in ('UNKNOWN','COMMERCIAL_PROPERTY') and re.search(r'\b'+p.value.lower()+r's?\b',text)]
    if len(props)>1:return stopped('AMBIGUOUS','MULTIPLE_PROPERTY_TYPES')
    prop=props[0] if props else request.property_type or (request.page_context.property_type if request.page_context else None)
    if request.property_type and props and request.property_type!=props[0]:return stopped('AMBIGUOUS','CONFLICTING_PROPERTY_TYPE')
    if request.page_context and request.page_context.active_filters:
        # Website dataset filters cannot silently be applied to RSS evidence.
        return stopped('UNSUPPORTED','DASHBOARD_FILTERS_NOT_SUPPORTED')
    try:
        time,basis=time_filter(text,request.as_of)
        if request.time_expression:
            supplied,supplied_basis=time_filter(request.time_expression,request.as_of)
            if supplied.expression=='LATEST' and not supplied_basis and request.time_expression.upper() not in ('LATEST','CURRENT'):
                return stopped('UNSUPPORTED','UNSUPPORTED_TIME_EXPRESSION')
            if time.expression!='LATEST' and supplied.expression!='LATEST' and (time.start,time.end)!=(supplied.start,supplied.end):
                return stopped('AMBIGUOUS','CONFLICTING_TIME_FILTER')
            if basis and supplied_basis and basis!=supplied_basis:return stopped('AMBIGUOUS','CONFLICTING_TIME_BASIS')
            time=supplied if supplied.expression!='LATEST' else time
            basis=supplied_basis or basis
    except ValueError as exc:return stopped('AMBIGUOUS',str(exc))
    if time.expression=='LATEST' and re.search(r'\b(?:20\d{2}|yesterday|tomorrow|last week|last year|this year|next week|next month|next year)\b',text):
        return stopped('UNSUPPORTED','UNSUPPORTED_TIME_EXPRESSION')
    metric=request.metric
    for pattern,name in ((r'\byields?\b','RENTAL_YIELD'),(r'annual rent','ANNUAL_RENT'),(r'monthly rent','MONTHLY_RENT'),(r'sqft|square foot','SALE_PRICE_PER_SQFT'),(r'sqm|square met','SALE_PRICE_PER_SQM'),(r'average.*price','AVERAGE_SALE_PRICE'),(r'median.*price','MEDIAN_SALE_PRICE'),(r'transaction values?','TRANSACTION_VALUE'),(r'transaction volumes?|transaction counts?','TRANSACTION_VOLUME')):
        if re.search(pattern,text):
            if metric and metric!=name:return stopped('AMBIGUOUS','CONFLICTING_METRIC')
            metric=MetricType(name);break
    action=None;intent=None;hierarchy=None;event_types=()
    if comparing:
        types={REGISTRY.entities[e].entity_type.value for e in targets}
        if types=={'EMIRATE'}:intent='COMPARE_EMIRATES';action='compare_emirates'
        elif types<={'AREA','COMMUNITY'}:intent='COMPARE_AREAS';action='compare_areas'
        else:return stopped('UNSUPPORTED','UNSUPPORTED_COMPARISON_HIERARCHY')
    elif re.search(r'\b(?:top|largest|biggest|strongest|highest|lowest)\b',text) and re.search(r'areas?|growth|increases?|decreases?|declines?|drops',text):
        down=bool(re.search(r'decreas|declin|drop|lowest',text));intent='TOP_DECREASE' if down else 'TOP_INCREASE';action='get_top_price_decreases' if down else 'get_top_price_increases'
        hierarchy='AREA' if re.search(r'areas?',text) else 'EMIRATE'
        if re.search(r'rents?|yields?|transactions?',text):return stopped('UNSUPPORTED','PRICE_RANKING_ACTION_ONLY')
    else:
        rules=((r'source|publisher','SOURCE_DETAILS','get_source_details'),
            (r'foreign investment','INVESTOR_ACTIVITY','get_foreign_investment_activity'),
            (r'off[ -]?plan','OFF_PLAN','get_off_plan_activity'),
            (r'ready[ -]propert','LATEST_EVENTS','get_ready_property_activity'),
            (r'regulations?|rules?|laws?','REGULATION','get_regulations'),
            (r'infrastructure','INFRASTRUCTURE','get_infrastructure_activity'),
            (r'outlook|forecasts?|sentiment','MARKET_OUTLOOK','get_market_outlook'),
            (r'projects?|launches|complet','PROJECT_NEWS','get_latest_projects'),
            (r'developer','LATEST_EVENTS','get_developer_activity'),
            (r'supply','SUPPLY','get_supply_activity'),(r'demand','DEMAND','get_demand_activity'),
            (r'investors?|investment','INVESTOR_ACTIVITY','get_investor_activity'),
            (r'events','LATEST_EVENTS','get_latest_events'),
            (r'transaction values?','TRANSACTION_VALUE','get_transaction_history'),
            (r'transaction volumes?|transaction counts?','TRANSACTION_VOLUME','get_transaction_history'),
            (r'transactions?','TRANSACTION_TREND','get_transaction_history'),
            (r'rents?|rental|yields?','RENTAL_MOVEMENT','get_rental_history'),
            (r'prices?','PRICE_MOVEMENT','get_price_history'),
            (r'news|updates|what.?s new|what is new','CURRENT_NEWS','get_latest_news'),
            (r'happening','CURRENT_NEWS' if time.expression!='LATEST' else 'MARKET_STATUS','get_latest_news' if time.expression!='LATEST' else 'get_market_snapshot'),
            (r'overview|summary|status|analysis|market|real[ -]estate','MARKET_STATUS','get_market_snapshot'))
        for pattern,i,a in rules:
            if re.search(pattern,text):intent=i;action=a;break
        if intent=='PRICE_MOVEMENT' and re.search(r'\b(?:level|current price|price is|property price|sale price)\b',text) and not re.search(r'mov|trend|increas|decreas|growth',text):intent='PROPERTY_PRICE'
        if intent=='RENTAL_MOVEMENT' and re.search(r'annual rent|monthly rent|rental price|rent level',text):intent='RENTAL_PRICE'
        if action=='get_latest_projects':
            if 'complet' in text:event_types=('PROJECT_COMPLETION',)
            elif 'launch' in text:event_types=('PROJECT_LAUNCH',)
        if action=='get_latest_news':action='get_news_by_area' if any(REGISTRY.entities[e].entity_type.value in ('AREA','COMMUNITY') for e in entity_ids) else 'get_latest_news' if entity_ids else 'get_news_by_emirate' if scope!=Emirate.UAE_WIDE else action
        if action=='get_market_snapshot' and 'analysis' in text:intent='AREA_ANALYSIS' if entity_ids else 'EMIRATE_ANALYSIS'
    if action is None:return stopped('UNSUPPORTED','UNRECOGNIZED_SUPPORTED_ACTION')
    if selected and (selected.intent.value!=intent or selected.action_id!=action):return stopped('UNSUPPORTED','QUESTION_MAPPING_MISMATCH')
    if time.expression in ('TODAY','THIS_WEEK') and action in ('get_price_history','get_rental_history','get_transaction_history','get_top_price_increases','get_top_price_decreases','compare_emirates','compare_areas'):
        return stopped('UNSUPPORTED','OBSERVATION_TIME_GRANULARITY_UNSUPPORTED')
    family='RENT' if re.search(r'rents?|rental|yields?',text) else 'TRANSACTION' if re.search(r'transactions?',text) else 'PRICE' if re.search(r'prices?',text) else None
    definition=ACTIONS[action]
    return RouteDecision(scope_status='IN_SCOPE',intent=intent,action_id=action,
        filters=Filters(emirate=scope,entity_ids=entity_ids,property_type=prop,metric=metric,source_id=request.source_id,time=time,movement_basis=basis,hierarchy=hierarchy,family=family,event_types=event_types,limit=request.limit),
        resolved_entities=ids,comparison_targets=targets,page_context_used=page_used or bool(request.page_context and prop and not props and not request.property_type),explicit_context_used=explicit_used,
        reason_code='EXPLICIT_CONTEXT' if explicit_used else 'PAGE_CONTEXT' if page_used else 'UAE_DEFAULT',expected_output_type=definition.expected_output_type)
