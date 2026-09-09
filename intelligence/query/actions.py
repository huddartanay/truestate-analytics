"""Fixed SQL over the published Stage 13 build. No writes or market calculations."""
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import hashlib
from intelligence import config as cfg
from intelligence.entities.registry import REGISTRY as ENTITIES
from intelligence.sources.registry import REGISTRY as SOURCES
from intelligence.query.models import Evidence,Record,Section,Status,ActionResult,OUTPUTS,Filters
from intelligence.query.registry import ACTIONS

_TABLES={'intelligence_current','intelligence_builds','intelligence_articles','intelligence_article_entities','intelligence_events',
    'intelligence_event_entities','intelligence_observations','market_series','market_movements','market_movement_unavailable','market_rankings','market_ranking_entries',
    'intelligence_news','intelligence_facts','intelligence_price_observations','intelligence_rent_observations','intelligence_transaction_observations'}
_VIEW_PARENTS={'intelligence_news':{'metric_extraction_results','cleaned_articles'},'intelligence_facts':{'market_observations'}}

def authorize(operation,arg1,arg2,database,source):
    if operation==sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if arg1 in _TABLES or arg1 in _VIEW_PARENTS.get(source,set()) else sqlite3.SQLITE_DENY
    if operation in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_RECURSIVE):return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY

@contextmanager
def read_snapshot():
    path=Path(cfg.DB_PATH)
    conn=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    conn.row_factory=sqlite3.Row
    try:
        conn.execute('PRAGMA query_only=ON');conn.set_authorizer(authorize);conn.execute('BEGIN')
        yield conn
    finally:conn.close()

def _where(filters,kind):
    """Only owned SQL fragments; parameters carry all supplied filter values."""
    conditions=['n.build_id=:build'];params={'limit':filters.limit+1}
    if filters.source_id:conditions.append('n.source_id=:source');params['source']=filters.source_id
    if filters.emirate.value not in ('UAE_WIDE','UNKNOWN','MULTI_EMIRATE'):
        params['scope']=filters.emirate.value
        if kind in ('fact','movement','ranking'):conditions.append('f.scope=:scope')
        else:
            ids=[e.entity_id for e in ENTITIES.entities.values() if e.emirate==filters.emirate]
            names=[]
            for i,e in enumerate(ids):params['scope_entity'+str(i)]=e;names.append(':scope_entity'+str(i))
            conditions.append("(n.location_scope=:scope OR (n.location_scope='MULTI_EMIRATE' AND EXISTS (SELECT 1 FROM intelligence_article_entities ge WHERE ge.build_id=n.build_id AND ge.metric_result_id=n.metric_result_id AND ge.entity_id IN ("+','.join(names)+'))))')
    for index,entity in enumerate(filters.entity_ids):
        key='entity'+str(index);params[key]=entity
        if kind in ('fact','movement','ranking'):conditions.append('f.entity_id=:'+key)
        elif kind=='event':conditions.append('EXISTS (SELECT 1 FROM intelligence_event_entities ge WHERE ge.build_id=e.build_id AND ge.event_id=e.event_id AND ge.entity_id=:'+key+')')
        else:conditions.append('EXISTS (SELECT 1 FROM intelligence_article_entities ge WHERE ge.build_id=n.build_id AND ge.metric_result_id=n.metric_result_id AND ge.entity_id=:'+key+')')
    if filters.property_type:
        params['property']=filters.property_type.value
        if kind in ('fact','movement','ranking'):conditions.append('f.property_type=:property')
        else:conditions.append('EXISTS (SELECT 1 FROM intelligence_observations po WHERE po.build_id=n.build_id AND po.metric_result_id=n.metric_result_id AND po.property_type=:property)')
    if filters.metric and kind in ('fact','movement','ranking'):conditions.append('f.metric=:metric');params['metric']=filters.metric.value
    if filters.time.start and (kind in ('news','event','source') or (kind=='fact' and not filters.time.period)):
        conditions.extend(('julianday(n.published_at)>=julianday(:start)','julianday(n.published_at)<julianday(:end)'))
        params.update(start=filters.time.start.isoformat(),end=filters.time.end.isoformat())
    if filters.time.period and kind in ('fact','movement','ranking'):conditions.append('f.period=:period');params['period']=filters.time.period
    if filters.movement_basis and kind in ('movement','ranking'):conditions.append('m.basis=:basis');params['basis']=filters.movement_basis
    return conditions,params

NEWS_ORDER=' ORDER BY n.published_at DESC,n.retrieved_at DESC,n.article_id,n.metric_result_id LIMIT :limit'
_PREVIOUS='''pf.observation_id AS p_observation_id,pn.metric_result_id AS p_metric_result_id,pn.article_id AS p_article_id,
 pn.raw_hash AS p_raw_hash,pn.source_id AS p_source_id,pn.source_name AS p_source_name,pn.article_url AS p_article_url,
 pn.rss_url AS p_rss_url,pn.published_at AS p_published_at,pn.retrieved_at AS p_retrieved_at,pf.entity_id AS p_entity_id'''

class Reader:
    def __init__(self,conn,build):self.conn=conn;self.build=build;self.evidence={};self.truncated=False;self.disagreement=False

    def evidence_for(self,row,kind,prefix=''):
        def get(key,default=None):return row.get(prefix+key,default)
        oid=get('observation_id');eid=get('event_id')
        ref=hashlib.sha256(((prefix or 'c:')+row['metric_result_id']+':'+str(oid or eid or 'article')+':'+str(row.get('movement_id',''))+':'+str(row.get('ranking_id',''))).encode()).hexdigest()
        entities=tuple(e for e in (get('entity_id'),) if e and e!='UNKNOWN')
        evidence=Evidence(reference_id=ref,build_id=self.build,metric_result_id=get('metric_result_id'),article_id=get('article_id'),raw_hash=get('raw_hash'),
            source_id=get('source_id'),source_name=get('source_name'),article_url=get('article_url'),rss_url=get('rss_url'),published_at=get('published_at'),retrieved_at=get('retrieved_at'),
            entity_ids=entities,event_id=eid,observation_id=oid,movement_id=row.get('movement_id'),ranking_id=row.get('ranking_id'))
        self.evidence[ref]=evidence;return ref

    def select(self,filters,kind,extra=(),extra_params=None):
        conditions,params=_where(filters,kind);params.update(build=self.build);params.update(extra_params or {});conditions.extend(extra)
        if kind in ('news','source'):sql='SELECT n.* FROM intelligence_news n'
        elif kind=='event':sql='SELECT n.*,e.event_id,e.event_type FROM intelligence_events e JOIN intelligence_news n ON n.build_id=e.build_id AND n.metric_result_id=e.metric_result_id'
        elif kind=='fact':sql='SELECT n.*,f.* FROM intelligence_facts f JOIN intelligence_news n ON n.build_id=f.build_id AND n.metric_result_id=f.metric_result_id'
        else:
            sql='SELECT n.*,f.*,m.*,'+_PREVIOUS
            if kind=='ranking':sql+=',r.ranking_id,re.rank_number,re.position'
            sql+=' FROM market_movements m JOIN intelligence_facts f ON f.build_id=m.build_id AND f.observation_id=m.current_observation_id JOIN intelligence_news n ON n.build_id=f.build_id AND n.metric_result_id=f.metric_result_id JOIN intelligence_facts pf ON pf.build_id=m.build_id AND pf.observation_id=m.comparison_observation_id JOIN intelligence_news pn ON pn.build_id=pf.build_id AND pn.metric_result_id=pf.metric_result_id'
            if kind=='ranking':sql+=' JOIN market_ranking_entries re ON re.build_id=m.build_id AND re.movement_id=m.movement_id JOIN market_rankings r ON r.build_id=re.build_id AND r.ranking_id=re.ranking_id'
        if kind=='ranking':order=' ORDER BY r.period DESC,r.ranking_id,re.position,re.entity_id LIMIT :limit'
        elif kind in ('fact','movement'):order=' ORDER BY f.period_ordinal DESC,n.published_at DESC,n.retrieved_at DESC,f.observation_id'+(',m.movement_id' if kind=='movement' else '')+' LIMIT :limit'
        elif kind=='event':order=NEWS_ORDER.replace(' LIMIT',',e.event_id LIMIT')
        else:order=NEWS_ORDER
        rows=[dict(r) for r in self.conn.execute(sql+' WHERE '+' AND '.join(conditions)+order,params)]
        if len(rows)>filters.limit:self.truncated=True
        rows=rows[:filters.limit];result=[]
        sources={s.source_id:s for s in SOURCES}
        for row in rows:
            refs=[self.evidence_for(row,kind)]
            if kind in ('movement','ranking'):refs.append(self.evidence_for(row,kind,'p_'))
            data=dict(kind={'news':'NEWS','event':'EVENT','fact':'OBSERVATION','movement':'MOVEMENT','ranking':'RANKING','source':'SOURCE'}[kind],
                identity=row.get('movement_id') or row.get('observation_id') or row.get('event_id') or row['metric_result_id'],evidence_ids=tuple(refs))
            if kind=='news':data['title']=row['clean_title']
            elif kind=='event':data.update(title=row['clean_title'],event_type=row['event_type'])
            elif kind=='source':
                source=sources.get(row['source_id'])
                data.update(source_tier=source.source_tier.value if source else None,trust_metadata=(('registry_trust_score:'+str(source.trust_score)),) if source else ())
            else:
                data.update(metric=row['metric'],value=row['change_pct'] if kind!='fact' else row['value'],unit='PERCENT' if kind!='fact' else row['unit'],currency=row['currency'],property_type=row['property_type'],statistic=row['statistic'],nature=row['nature'],provenance='SYSTEM_CALCULATED' if kind!='fact' else 'SOURCE_REPORTED',period=row['period'],frequency=row['frequency'],exclusion_reason=row.get('exclusion_reason'))
                if kind!='fact':data.update(movement_basis=row['basis'],classification=row['classification'])
                if kind=='ranking':data.update(rank_number=row['rank_number'],position=row['position'],group_id=row['ranking_id'])
            result.append(Record(**data))
        if kind=='fact':
            groups=defaultdict(set)
            for row in rows:
                key=tuple(row.get(k) for k in ('entity_id','metric','period','property_type','statistic','currency','unit','nature'))
                if row['period'] is not None:groups[key].add(row['value'])
            self.disagreement|=any(len(v)>1 for v in groups.values())
        return tuple(result)

    def events(self,filters,event_types=()):
        types=filters.event_types or event_types
        if not types:return self.select(filters,'event')
        return self.select(filters,'event',('e.event_type IN ('+','.join(':type'+str(i) for i in range(len(types)))+')',),{'type'+str(i):t for i,t in enumerate(types)})

    def history(self,filters,family):
        facts=self.select(filters,'fact',('f.family=:family',),{'family':family})
        movements=self.select(filters,'movement',('f.family=:family',),{'family':family})
        # A specifically requested basis with no matching movement is partial
        # evidence, even if source observations exist; no recalculation.
        return facts+movements

    def handle(self,definition,filters,targets=()):
        handler=definition.handler
        if handler=='news':return self.select(filters,'news'),()
        if handler=='source':return self.select(filters,'source'),()
        if handler=='events':return self.events(filters,definition.event_types),()
        if handler in ('price','rent','transaction'):return self.history(filters,handler.upper()),()
        if handler in ('increase','decrease'):
            extra=['r.direction=:direction','f.family=\'PRICE\''];params={'direction':handler.upper()}
            if filters.hierarchy:extra.append('r.entity_type=:hierarchy');params['hierarchy']=filters.hierarchy
            return self.select(filters,'ranking',extra,params),()
        if handler=='outlook':return self.events(filters,definition.event_types)+self.select(filters,'fact',("f.nature='SOURCE_REPORTED_FORECAST'",)),()
        if handler=='snapshot':
            parts=(('news','get_latest_news'),('events','get_latest_events'),('prices','get_price_history'),('rents','get_rental_history'),('transactions','get_transaction_history'),('projects','get_latest_projects'),('regulations','get_regulations'),('outlook','get_market_outlook'))
            sections=[]
            for name,action in parts:
                if filters.time.expression in ('TODAY','THIS_WEEK') and name in ('prices','rents','transactions'):
                    sections.append(Section(name=name,status='UNSUPPORTED'));continue
                before=self.truncated;prior_disagreement=self.disagreement;self.truncated=False;self.disagreement=False
                records,_=self.handle(ACTIONS[action],filters)
                status='PARTIAL' if records and (self.truncated or self.disagreement or (filters.movement_basis and name in ('prices','rents','transactions') and not any(r.kind=='MOVEMENT' for r in records))) else 'AVAILABLE' if records else 'NO_DATA'
                sections.append(Section(name=name,status=status,records=records));self.truncated|=before;self.disagreement|=prior_disagreement
            return (),tuple(sections)
        if handler=='compare':
            sides=[]
            for entity_id in targets:
                entity=ENTITIES.entities[entity_id]
                side=Filters(**(filters.model_dump()|dict(emirate=entity.emirate or 'UAE_WIDE',entity_ids=() if entity.entity_type.value=='EMIRATE' else (entity_id,))))
                family=filters.family or ('RENT' if filters.metric and filters.metric.value.startswith(('RENT','ANNUAL_RENT','MONTHLY_RENT')) else 'TRANSACTION' if filters.metric and filters.metric.value.startswith('TRANSACTION') else 'PRICE')
                before=self.truncated;prior_disagreement=self.disagreement;self.truncated=False;self.disagreement=False
                records=self.history(side,family)
                sides.append(Section(name=entity_id,status='PARTIAL' if records and (self.truncated or self.disagreement or (filters.movement_basis and not any(r.kind=='MOVEMENT' for r in records))) else 'AVAILABLE' if records else 'NO_DATA',records=records))
                self.truncated|=before;self.disagreement|=prior_disagreement
            return (),tuple(sides)
        raise ValueError('Unregistered handler')

def execute(decision,as_of=None):
    if decision.scope_status!='IN_SCOPE':
        return ActionResult(action_id=None,intent=decision.intent,status=decision.scope_status,filters_applied=decision.filters,result_count=0,evidence_count=0,
            reason_code=decision.reason_code,as_of=as_of,answer_policy={'OUT_OF_SCOPE':'REFUSE_SCOPE','AMBIGUOUS':'CLARIFY','UNSUPPORTED':'UNSUPPORTED'}[decision.scope_status])
    definition=ACTIONS.get(decision.action_id)
    if not definition or decision.intent not in definition.supported_intents or decision.expected_output_type!=definition.expected_output_type:raise ValueError('Invalid action registry contract')
    if 'entity_ids' in definition.required_filters and not decision.filters.entity_ids:raise ValueError('Area action requires an entity')
    if 'emirate' in definition.required_filters and decision.filters.emirate.value in ('UAE_WIDE','UNKNOWN','MULTI_EMIRATE'):raise ValueError('Emirate action requires one emirate')
    if 'comparison_targets' in definition.required_filters:
        targets=decision.comparison_targets
        kinds={'EMIRATE'} if definition.action_id=='compare_emirates' else {'AREA','COMMUNITY'}
        if len(set(targets))!=2 or any(t not in ENTITIES.entities or ENTITIES.entities[t].entity_type.value not in kinds for t in targets):raise ValueError('Two registered comparison targets required')
    model=OUTPUTS[definition.expected_output_type]
    metadata=dict(action_id=definition.action_id,intent=decision.intent,filters_applied=decision.filters,as_of=as_of)
    if not Path(cfg.DB_PATH).is_file():return model(**metadata,status='NO_DATA',reason_code='NO_PUBLISHED_BUILD',result_count=0,evidence_count=0,answer_policy='NO_DATA')
    with read_snapshot() as conn:
        current=conn.execute("SELECT build_id FROM intelligence_current WHERE channel='CURRENT'").fetchone()
        if current is None:return model(**metadata,status='NO_DATA',reason_code='NO_PUBLISHED_BUILD',result_count=0,evidence_count=0,answer_policy='NO_DATA')
        reader=Reader(conn,current[0]);records,sections=reader.handle(definition,decision.filters,decision.comparison_targets)
        all_records=records+tuple(r for section in sections for r in section.records)
        status='AVAILABLE' if all_records else 'NO_DATA'
        if all_records and (reader.truncated or reader.disagreement or any(s.status!='AVAILABLE' for s in sections)):status='PARTIAL'
        if all_records and decision.filters.movement_basis and definition.handler in ('price','rent','transaction') and not any(r.kind=='MOVEMENT' for r in records):status='PARTIAL'
        if definition.handler=='compare' and len(sections)==2 and all(s.records for s in sections):
            def keys(section):
                return {(r.kind,r.metric,r.unit,r.currency,r.property_type,r.statistic,r.nature,r.period,r.frequency,r.movement_basis,reader.evidence[r.evidence_ids[0]].source_id,ENTITIES.entities[section.name].entity_type) for r in section.records}
            if not keys(sections[0])&keys(sections[1]):status='NOT_COMPARABLE'
            elif keys(sections[0])!=keys(sections[1]):status='PARTIAL'
        dates=[e.published_at or e.retrieved_at for e in reader.evidence.values()]
        return model(**metadata,build_id=current[0],status=status,records=records,sections=sections,evidence=tuple(reader.evidence.values()),result_count=len(all_records),evidence_count=len(reader.evidence),
            latest_available_at=max(dates) if dates else None,source_disagreement=reader.disagreement,truncated=reader.truncated,answer_policy='NO_DATA' if status=='NO_DATA' else 'EVIDENCE_ONLY')
