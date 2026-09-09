"""240 editorial question definitions; IDs are stable, never array positions."""
from intelligence import config as cfg
from string import Formatter
from types import MappingProxyType
from pydantic import Field,model_validator
from intelligence.query.models import Model,Intent,PageContext
from intelligence.query.registry import ACTIONS
from intelligence.query.resolution import context_ids
from intelligence.entities.registry import REGISTRY

class PredefinedQuestion(Model):
    question_id: str=Field(pattern=r'^[a-z0-9][a-z0-9_.-]+$')
    label: str
    question_template: str
    category: str
    intent: Intent
    action_id: str
    supported_contexts: tuple[str,...]=('GLOBAL','EMIRATE','AREA','PROJECT','DEVELOPER','OUTLOOK','DASHBOARD')
    required_context: tuple[str,...]=()
    default_filters: dict[str,str]=Field(default_factory=dict)
    expected_output_type: str
    display_priority: int=100
    suggested_for_chat: bool=True
    enabled: bool=True
    property_type: str | None=None
    time_basis: str='LATEST'
    question_version: str=cfg.PREDEFINED_QUESTION_VERSION

    @model_validator(mode='after')
    def contract(self):
        definition=ACTIONS.get(self.action_id)
        if definition is None or self.intent not in definition.supported_intents or self.expected_output_type!=definition.expected_output_type:raise ValueError('Invalid question action/output mapping')
        fields={field for _,field,_,_ in Formatter().parse(self.question_template) if field}
        if not fields<={'emirate','area','project','developer','emirate_1','emirate_2','area_1','area_2'} or fields!=set(self.required_context):raise ValueError('Invalid template placeholders')
        return self

GEOGRAPHIES=(('uae','UAE','UAE_WIDE'),('dubai','Dubai','DUBAI'),('abu_dhabi','Abu Dhabi','ABU_DHABI'),('sharjah','Sharjah','SHARJAH'),('rak','Ras Al Khaimah','RAS_AL_KHAIMAH'),('ajman','Ajman','AJMAN'),('fujairah','Fujairah','FUJAIRAH'),('uaq','Umm Al Quwain','UMM_AL_QUWAIN'))
BASE=(
 ('overview','What is happening in {e} real estate?','MARKET_OVERVIEW','MARKET_STATUS','get_market_snapshot'),
 ('news','Latest {e} real-estate news','NEWS','CURRENT_NEWS','get_latest_news'),
 ('prices','How are property prices moving in {e}?','PRICES','PRICE_MOVEMENT','get_price_history'),
 ('rents','How are rents moving in {e}?','RENTS','RENTAL_MOVEMENT','get_rental_history'),
 ('yields','What rental yields were reported in {e}?','RENTAL_YIELD','RENTAL_MOVEMENT','get_rental_history'),
 ('transaction_value','Show {e} transaction values','TRANSACTIONS','TRANSACTION_VALUE','get_transaction_history'),
 ('transaction_volume','Show {e} transaction volumes','TRANSACTIONS','TRANSACTION_VOLUME','get_transaction_history'),
 ('projects','Latest {e} projects','PROJECTS','PROJECT_NEWS','get_latest_projects'),
 ('off_plan','What is happening with {e} off-plan activity?','OFF_PLAN','OFF_PLAN','get_off_plan_activity'),
 ('ready','What is happening with {e} ready-property activity?','READY_PROPERTY','LATEST_EVENTS','get_ready_property_activity'),
 ('supply','What is happening with {e} housing supply?','SUPPLY','SUPPLY','get_supply_activity'),
 ('demand','What is happening with {e} property demand?','DEMAND','DEMAND','get_demand_activity'),
 ('investors','Show {e} real estate investor activity','INVESTMENT','INVESTOR_ACTIVITY','get_investor_activity'),
 ('foreign_investment','Show foreign investment into {e} property','FOREIGN_INVESTMENT','INVESTOR_ACTIVITY','get_foreign_investment_activity'),
 ('regulations','Latest {e} property regulations','REGULATIONS','REGULATION','get_regulations'),
 ('infrastructure','What infrastructure developments are relevant to {e} real estate?','INFRASTRUCTURE','INFRASTRUCTURE','get_infrastructure_activity'),
 ('outlook','What is the {e} market outlook?','MARKET_OUTLOOK','MARKET_OUTLOOK','get_market_outlook'),
 ('events','Latest {e} real estate events','NEWS','LATEST_EVENTS','get_latest_events'),
 ('sources','What sources report on {e} real estate?','SOURCES','SOURCE_DETAILS','get_source_details'),
 ('increases','Which {e} areas have the largest YoY price increases?','RANKINGS','TOP_INCREASE','get_top_price_increases'),
 ('decreases','Which {e} areas have the largest YoY price decreases?','RANKINGS','TOP_DECREASE','get_top_price_decreases'),
 ('mom','How are {e} property prices moving MoM?','MOVEMENTS','PRICE_MOVEMENT','get_price_history'),
 ('qoq','How are {e} property prices moving QoQ?','MOVEMENTS','PRICE_MOVEMENT','get_price_history'),
 ('annual_rent','Show {e} annual rent observations','RENTS','RENTAL_PRICE','get_rental_history'),
 ('sentiment','What is the {e} property market sentiment?','MARKET_SENTIMENT','MARKET_OUTLOOK','get_market_outlook'),
)

def definition(key,text,category,intent,action,**kw):
    return PredefinedQuestion(question_id=key,label=text,question_template=text,category=category,intent=intent,action_id=action,expected_output_type=ACTIONS[action].expected_output_type,**kw)

_questions=[]
for slug,name,scope in GEOGRAPHIES:
    for priority,(key,text,category,intent,action) in enumerate(BASE):
        if action=='get_latest_news' and scope!='UAE_WIDE':action='get_news_by_emirate'
        _questions.append(definition(slug+'.'+key,text.format(e=name),category,intent,action,default_filters={'emirate':scope},display_priority=priority,
            time_basis='YOY' if key in ('increases','decreases') else key.upper() if key in ('mom','qoq') else 'LATEST'))
for slug,name in (('dubai','Dubai'),('abu_dhabi','Abu Dhabi')):
    for suffix,time in (('today','today'),('week','this week'),('month','this month'),('last_month','last month'),('q1','in Q1')):
        _questions.append(definition(slug+'.news_'+suffix,f'Latest {name} property news {time}','NEWS','CURRENT_NEWS','get_news_by_emirate',default_filters={'emirate':slug.upper()},time_basis=time.upper().replace(' ','_')))
for prop in ('apartment','villa','townhouse','land','office','retail','warehouse','commercial'):
    _questions.append(definition('template.price_'+prop,f'How are {prop} prices moving in '+'{emirate}?','PRICES','PRICE_MOVEMENT','get_price_history',required_context=('emirate',),property_type=prop.upper()))
for key,text,category,intent,action in (
 ('overview','What is happening in {area}?','AREAS','MARKET_STATUS','get_market_snapshot'),
 ('news','Latest real-estate news for {area}','NEWS','CURRENT_NEWS','get_news_by_area'),
 ('prices','How are property prices moving in {area}?','PRICES','PRICE_MOVEMENT','get_price_history'),
 ('rents','How are rents moving in {area}?','RENTS','RENTAL_MOVEMENT','get_rental_history'),
 ('transactions','What transactions were reported in {area}?','TRANSACTIONS','TRANSACTION_TREND','get_transaction_history'),
 ('projects','Latest projects in {area}','PROJECTS','PROJECT_NEWS','get_latest_projects'),
 ('outlook','What is the market outlook for {area}?','MARKET_OUTLOOK','MARKET_OUTLOOK','get_market_outlook')):
    _questions.append(definition('template.area_'+key,text,category,intent,action,required_context=('area',),supported_contexts=('AREA',),display_priority=len(_questions)-218))
for key,text,category,action,required in (
 ('project','Latest project news for {project}','PROJECTS','get_latest_projects','project'),
 ('developer','What recent developer activity is associated with {developer}?','DEVELOPERS','get_developer_activity','developer'),
 ('developer_projects','What projects are associated with {developer}?','DEVELOPERS','get_latest_projects','developer')):
    _questions.append(definition('template.'+key,text,category,'LATEST_EVENTS' if action=='get_developer_activity' else 'PROJECT_NEWS',action,required_context=(required,)))
for key,left,right in (('dubai_abu_dhabi','Dubai','Abu Dhabi'),('dubai_sharjah','Dubai','Sharjah'),('dubai_rak','Dubai','RAK'),('abu_dhabi_sharjah','Abu Dhabi','Sharjah')):
    _questions.append(definition('compare.'+key,f'Compare {left} and {right}','COMPARISONS','COMPARE_EMIRATES','compare_emirates'))
for kind in ('emirate','area'):
    _questions.append(definition('template.compare_'+kind,'Compare {'+kind+'_1} and {'+kind+'_2}','COMPARISONS','COMPARE_EMIRATES' if kind=='emirate' else 'COMPARE_AREAS','compare_emirates' if kind=='emirate' else 'compare_areas',required_context=(kind+'_1',kind+'_2'),suggested_for_chat=False))
for key,text,intent,action in (
 ('status','How is the market here?','MARKET_STATUS','get_market_snapshot'),
 ('prices','How are prices moving here?','PRICE_MOVEMENT','get_price_history'),
 ('rents','How are rents moving here?','RENTAL_MOVEMENT','get_rental_history'),
 ('events','Latest property events here','LATEST_EVENTS','get_latest_events'),
 ('projects','Latest projects here','PROJECT_NEWS','get_latest_projects'),
 ('outlook','What is the market outlook here?','MARKET_OUTLOOK','get_market_outlook')):
    _questions.append(definition('context.'+key,text,'PAGE_CONTEXT',intent,action,supported_contexts=('EMIRATE','AREA','PROJECT','DEVELOPER'),suggested_for_chat=False))
QUESTIONS=MappingProxyType({q.question_id:q for q in _questions})
assert len(QUESTIONS)==len(_questions)==240

def render(question,context=None,bindings=None):
    if 'here' in question.question_template and not context_ids(context):raise ValueError('Page context required')
    values=dict(bindings or {})
    if context:
        if context.emirate:values.setdefault('emirate','UAE' if context.emirate.value=='UAE_WIDE' else context.emirate.value.replace('_',' ').title())
        for entity_id in context_ids(context):
            entity=REGISTRY.entities[entity_id];key=entity.entity_type.value.lower()
            if key=='community':key='area'
            values.setdefault(key,entity.canonical_name)
    if not set(question.required_context)<=set(values):raise ValueError('Required template context missing')
    return question.question_template.format_map(values)
