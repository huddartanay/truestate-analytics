"""Fixed, versioned action definitions. Handlers are named allowlisted capabilities."""
from intelligence import config as cfg
from types import MappingProxyType
from intelligence.query.models import Model,Intent,OUTPUTS

class ActionDefinition(Model):
    action_id: str
    supported_intents: tuple[Intent,...]
    expected_output_type: str
    handler: str
    required_filters: tuple[str,...]=()
    optional_filters: tuple[str,...]=('emirate','entity_ids','property_type','metric','source_id','time','movement_basis','limit')
    default_limit: int=10
    maximum_limit: int=50
    supported_contexts: tuple[str,...]=('GLOBAL','EMIRATE','AREA','PROJECT','DEVELOPER','OUTLOOK','DASHBOARD')
    event_types: tuple[str,...]=()
    action_version: str=cfg.INTELLIGENCE_ACTION_VERSION

_DEFINITIONS=(
 ('get_latest_news',('CURRENT_NEWS',),'NewsResult','news',()),
 ('get_news_by_emirate',('CURRENT_NEWS',),'NewsResult','news',()),
 ('get_news_by_area',('CURRENT_NEWS',),'NewsResult','news',()),
 ('get_price_history',('PRICE_MOVEMENT','PROPERTY_PRICE'),'PriceHistoryResult','price',()),
 ('get_rental_history',('RENTAL_MOVEMENT','RENTAL_PRICE'),'RentalHistoryResult','rent',()),
 ('get_transaction_history',('TRANSACTION_TREND','TRANSACTION_VALUE','TRANSACTION_VOLUME'),'TransactionHistoryResult','transaction',()),
 ('get_top_price_increases',('TOP_INCREASE',),'RankingResult','increase',()),
 ('get_top_price_decreases',('TOP_DECREASE',),'RankingResult','decrease',()),
 ('get_market_snapshot',('MARKET_STATUS','EMIRATE_ANALYSIS','AREA_ANALYSIS'),'MarketSnapshotResult','snapshot',()),
 ('get_latest_projects',('PROJECT_NEWS',),'ProjectResult','events',('NEW_PROJECT','PROJECT_LAUNCH','PROJECT_COMPLETION')),
 ('get_regulations',('REGULATION',),'RegulationResult','events',('REGULATION',)),
 ('get_market_outlook',('MARKET_OUTLOOK',),'OutlookResult','outlook',('MARKET_OUTLOOK','MARKET_SENTIMENT')),
 ('compare_emirates',('COMPARE_EMIRATES',),'ComparisonResult','compare',()),
 ('compare_areas',('COMPARE_AREAS',),'ComparisonResult','compare',()),
 ('get_source_details',('SOURCE_DETAILS',),'SourceDetailsResult','source',()),
 ('get_latest_events',('LATEST_EVENTS',),'EventActivityResult','events',()),
 ('get_off_plan_activity',('OFF_PLAN',),'EventActivityResult','events',('OFF_PLAN_ACTIVITY',)),
 ('get_ready_property_activity',('LATEST_EVENTS',),'EventActivityResult','events',('READY_PROPERTY_ACTIVITY',)),
 ('get_supply_activity',('SUPPLY',),'EventActivityResult','events',('NEW_SUPPLY','SUPPLY_PIPELINE')),
 ('get_demand_activity',('DEMAND',),'EventActivityResult','events',('DEMAND_CHANGE',)),
 ('get_investor_activity',('INVESTOR_ACTIVITY',),'EventActivityResult','events',('INVESTOR_ACTIVITY',)),
 ('get_foreign_investment_activity',('INVESTOR_ACTIVITY',),'EventActivityResult','events',('FOREIGN_INVESTMENT',)),
 ('get_infrastructure_activity',('INFRASTRUCTURE',),'EventActivityResult','events',('INFRASTRUCTURE',)),
 ('get_developer_activity',('LATEST_EVENTS',),'EventActivityResult','events',('DEVELOPER_ACTIVITY',)),
)
ACTIONS=MappingProxyType({a:ActionDefinition(action_id=a,supported_intents=i,expected_output_type=o,handler=h,event_types=e,
    required_filters=('comparison_targets',) if h=='compare' else ('entity_ids',) if a=='get_news_by_area' else ('emirate',) if a=='get_news_by_emirate' else ()) for a,i,o,h,e in _DEFINITIONS})
assert all(a.expected_output_type in OUTPUTS for a in ACTIONS.values())
