"""Reviewable Stage 11 v1 rules. Patterns operate on mapped normalized text.

Numbers can occur in evidence grammar; no numeric value is parsed or returned.
Every rule requires an explicit subject/action relation within a bounded clause.
"""
from dataclasses import dataclass
import re

from intelligence.enums import EventType


def boundary(value):
    return re.compile(r'(?<!\w)(?:' + value + r')(?!\w)')


INCREASE = r'increas(?:e|es|ed|ing)|ris(?:e|es|ing)|rose|growth|grew|grow(?:s|ing)?|climb(?:ed|s|ing)?|higher|surg(?:e|ed|es)|improv(?:e|ed|es)|ارتفع(?:ت)?|ارتفاع|زاد(?:ت)?|زيادة|نمو'
DECREASE = r'decreas(?:e|ed|es|ing)|declin(?:e|ed|es|ing)|fell|fall(?:s|ing)?|lower|drop(?:ped|s)?|contract(?:ed|s)?|slow(?:ed|s)?|weaken(?:ed|s)?|انخفض(?:ت)?|انخفاض|تراجع(?:ت)?'
STABLE = r'stable|unchanged|flat|steady|استقر(?:ت)?|مستقر(?:ة)?|ثابت(?:ة)?'
MOVEMENT = '(?:' + '|'.join((INCREASE, DECREASE, STABLE)) + ')'
DIRECTIONS = tuple((name, boundary(pattern)) for name, pattern in (
    ('INCREASE', INCREASE), ('DECREASE', DECREASE), ('STABLE', STABLE)))
PROPERTY = boundary(r'property|properties|real estate|housing|homes?|houses?|residential|apartments?|villas?|rents?|rental|tenancy|mortgage|land registration|عقارات|العقارات|عقارية|العقارية|سكني|السكني|الشقق|الايجارات|العقاري')
NEGATION = boundary(r'not|no|without|never|didn t|doesn t|don t|hasn t|haven t|wasn t|weren t|isn t|aren t|won t|wouldn t|لم|لن|لا|ليس|بدون|غير')
HISTORICAL = boundary(r'last year|last month|previous year|previously|historically|العام الماضي|الشهر الماضي')
FORECAST = r'forecast(?:s|ed)?|expected|expects?|projected|projection|outlook|anticipat(?:es|ed)|يتوقع|متوقع|توقعات'
FORWARD = boundary(FORECAST + r'|will|would|plans|planned|upcoming|future|سوف|سيتم|مخطط')
COLLISION = boundary(r'oil|crude|fuel|stocks?|shares?|car rental|vehicle rental|software developer|intellectual property|banking regulation|corporate law|construction safety|اسعار النفط')


def pair(subject, action, gap=6):
    bridge = r'(?: \w+){0,' + str(gap) + r'}? '
    return '(?:' + subject + ')' + bridge + '(?:' + action + ')|(?:' + action + ')' + bridge + '(?:' + subject + ')'


@dataclass(frozen=True)
class Rule:
    rule_id: str
    event_type: EventType
    pattern: re.Pattern
    context: re.Pattern | None = None
    directional: bool = False
    priority: int = 50
    forecast_allowed: bool = False
    fields: tuple[str, ...] = ('TITLE', 'BODY')


def rule(kind, pattern, *, context=None, directional=False, priority=50, forecast_allowed=False):
    return Rule(kind.lower() + '-v1', EventType(kind), boundary(pattern), context,
                directional, priority, forecast_allowed)


PROJECT = r'(?:new )?(?:residential )?projects?|development|مشروع(?: سكني)?(?: جديد)?'
UNITS = r'homes?|apartments?|units|villas?|الشقق|الوحدات|شقة'
TRANSACTIONS = r'(?:property )?transactions|معاملة عقارية|المعاملات العقارية|التصرفات العقارية'
RULES = (
    rule('PRICE_CHANGE', pair(r'(?:property |home |house |villa |apartment )?prices|home values|اسعار العقارات|اسعار الشقق', MOVEMENT), directional=True),
    rule('RENT_CHANGE', pair(r'rents|rental (?:prices|rates)|الايجارات|اسعار الايجارات', MOVEMENT), directional=True),
    rule('TRANSACTION_VALUE', pair(TRANSACTIONS, r'worth|aggregate value|total value|قيمة') + r'|(?:aggregate|total) (?:property )?transaction value'),
    rule('TRANSACTION_VOLUME', pair(TRANSACTIONS, r'count|number|volume|عدد|حجم') + r'|(?:recorded|registered|تسجيل)(?: \w+){0,3}? [\d]+(?: [\d]+)* (?:property )?transactions|[\d]+(?: [\d]+)* (?:property )?transactions (?:were )?(?:recorded|registered)|تسجيل [\d]+ معاملة عقارية'),
    rule('SALES_ACTIVITY', pair(r'home sales|property sales|villa sales|apartment sales|sales activity|مبيعات العقارات|مبيعات الشقق', MOVEMENT + r'|opened|recorded'), directional=True),
    rule('MORTGAGE_ACTIVITY', pair(r'mortgage (?:registrations|activity|demand|lending|applications)|تسجيلات الرهن العقاري|الرهن العقاري', MOVEMENT + r'|recorded|registered'), directional=True),
    rule('OFF_PLAN_ACTIVITY', pair(r'off plan (?:project )?(?:sales|activity|market)|المبيعات على الخارطة', MOVEMENT + r'|opened|opens|launch(?:es|ed)?|recorded'), directional=True, priority=80),
    rule('READY_PROPERTY_ACTIVITY', pair(r'ready (?:home|property) sales|secondary market activity|completed unit sales', MOVEMENT + r'|recorded'), directional=True, priority=80),
    rule('NEW_PROJECT', pair(r'new (?:residential )?project|مشروع(?: سكني)? جديد', r'announc(?:es|ed)|introduc(?:es|ed)|اعلنت|اعلن'), priority=70),
    rule('PROJECT_LAUNCH', pair(PROJECT, r'launch(?:es|ed)?|release(?:s|d)?|opened for sales?|opens for sales?|sales opened|اطلق(?:ت)?'), priority=100),
    rule('PROJECT_COMPLETION', '(?:' + PROJECT + '|' + UNITS + r')(?: \w+){0,4}? (?:completed|delivered|handed over|handover completed)|(?:تسليم|اكتمل)(?: \w+){0,3}? (?:' + PROJECT + '|' + UNITS + ')', priority=90),
    rule('NEW_SUPPLY', pair(UNITS + r'|housing supply', r'entered (?:the )?market|became available|added to (?:the )?market|دخلت السوق'), priority=80),
    rule('SUPPLY_PIPELINE', pair(UNITS + r'|housing supply|residential supply', r'planned|upcoming|future delivery|scheduled for delivery|مخطط'), forecast_allowed=True),
    rule('DEVELOPER_ACTIVITY', pair(r'developer|developers|المطور', r'expands?(?: its)? (?:uae )?(?:property )?portfolio|acquir(?:es|ed)|merg(?:es|ed)'), priority=20),
    rule('INVESTOR_ACTIVITY', pair(r'investor purchases|investor participation|investors|المستثمرين', MOVEMENT + r'|purchased|bought'), directional=True),
    rule('FOREIGN_INVESTMENT', pair(r'foreign buyers|international investors|overseas investment|cross border investment|المستثمرون الاجانب', r'purchases|purchased|bought|entered|increased|مشتريات'), priority=80),
    rule('REGULATION', pair(r'tenancy (?:rules|law)|property (?:registration rules|ownership regulation|ownership rules|regulation)|real estate regulation|rent regulation|قانون الايجارات|قانون العقارات', r'changed|updated|introduced|approved|enacted|amended|تعديل|اصدار')),
    rule('INFRASTRUCTURE', pair(r'metro (?:extension|expansion)|new road|transport link|airport development', r'announced|opened|approved|support(?:s|ing)?|completed')),
    rule('DEMAND_CHANGE', pair(r'buyer demand|housing demand|tenant demand|property demand|الطلب على العقارات', MOVEMENT), directional=True),
    rule('MARKET_SENTIMENT', pair(r'investor confidence|buyer confidence|market sentiment|property market sentiment|التفاؤل', MOVEMENT + r'|optimism|caution|positive|negative'), directional=True),
    rule('MARKET_OUTLOOK', pair(r'property prices|home prices|housing supply|real estate|property market|residential project|اسعار العقارات', FORECAST), forecast_allowed=True),
    rule('RENTAL_ACTIVITY', pair(r'leasing activity|tenant registrations|rental activity|rental market activity|tenancy agreements', MOVEMENT + r'|recorded|registered'), directional=True),
)

# Same-clause specificity only. Independent clauses retain separate events.
SUPPRESSES = {
    EventType.RENT_CHANGE: {EventType.PRICE_CHANGE},
    EventType.PROJECT_LAUNCH: {EventType.NEW_PROJECT, EventType.DEVELOPER_ACTIVITY},
    EventType.NEW_PROJECT: {EventType.DEVELOPER_ACTIVITY},
    EventType.PROJECT_COMPLETION: {EventType.DEVELOPER_ACTIVITY},
    EventType.OFF_PLAN_ACTIVITY: {EventType.SALES_ACTIVITY},
    EventType.READY_PROPERTY_ACTIVITY: {EventType.SALES_ACTIVITY},
    EventType.FOREIGN_INVESTMENT: {EventType.INVESTOR_ACTIVITY},
}

if {r.event_type for r in RULES} != set(EventType) or len({r.rule_id for r in RULES}) != len(RULES):
    raise ValueError('Event rule registry must cover the explicit taxonomy uniquely')
