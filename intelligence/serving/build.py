"""Validate accepted upstream evidence, then construct the entire serving build."""
from collections import defaultdict, Counter
from dataclasses import dataclass
from intelligence.db.intelligence import decode_metric, VERSION_FIELDS
from intelligence.metrics.extract import validate_input, validate_observations
from intelligence.pipeline.metrics import _contexts, MetricReport
from intelligence.serving.periods import resolve_period
from intelligence.serving.series import geography, family, exclusion, Series, Point
from intelligence.serving.movements import calculate
from intelligence.serving.rankings import rank
from intelligence.serving.policy import identity
from intelligence.schemas import CleanArticle, EntityExtractionResult, EventExtractionResult, MetricExtractionResult, UAERealEstateRelevanceResult, RealEstateRelevanceResult


@dataclass(frozen=True)
class Context:
    article: CleanArticle
    entities: EntityExtractionResult
    events: EventExtractionResult
    metrics: MetricExtractionResult
    stage9: UAERealEstateRelevanceResult
    stage8: RealEstateRelevanceResult


@dataclass(frozen=True)
class Bundle:
    articles: tuple
    entities: tuple
    events: tuple
    event_links: tuple
    observations: tuple
    series: tuple
    movements: tuple
    unavailable: tuple
    rankings: tuple


def contexts(value,report):
    run,rows,observations,links,events,upstream,pointers=value
    if run is None: return (),identity(('EMPTY',report.versions)),{}
    report.stage12_run_id=run['run_id']
    audit=MetricReport(report.run_id,report.started_at,*(getattr(report,k) for k in VERSION_FIELDS))
    valid={e.event_result_id:(a,u,e,s9,s8) for _,a,u,e,s9,s8 in _contexts(upstream,audit)} if upstream else {}
    grouped=defaultdict(list);by_link=defaultdict(list);by_event=defaultdict(list)
    for row in observations: grouped[row['metric_result_id']].append(row)
    for row in links: by_link[row['observation_id']].append(row)
    for row in events: by_event[row['observation_id']].append(row)
    result=[]
    for ordinal,row in enumerate(rows,1):
        report.active_record=ordinal
        article,entities,event,s9,s8=valid[row['event_result_id']]
        metric=decode_metric(row,grouped[row['metric_result_id']],by_link,by_event,entities,event)
        if any(getattr(metric,k)!=getattr(report,k) for k in VERSION_FIELDS): raise ValueError('Stage 12 version mismatch')
        if metric.source_id!=article.source_id: raise ValueError('Source mismatch')
        # Exact Stage 11 context, including cohort identity and article scope.
        for key in ('article_id','raw_hash','context_id','group_id','extraction_id','event_result_id','location_scope'):
            if getattr(metric,key)!=getattr(event,key): raise ValueError('Stage 12 context mismatch')
        validate_input(article,entities,event,s9,s8)
        validate_observations(metric.observations,article,entities,event,metric.metric_extraction_version)
        result.append(Context(article,entities,event,metric,s9,s8))
    # Invalid selected Stage 12 records fail the whole build; upstream records
    # absent from this selected cohort are historical and not serving inputs.
    def semantic_model(model):
        data=model.model_dump(mode='json');data.pop('evaluated_at',None)
        return data
    semantic=[tuple(semantic_model(model) for model in (c.article,c.entities,c.events,c.metrics,c.stage9,c.stage8)) for c in result]
    upstream_entities=upstream[4] if upstream else None
    exclusions=dict(excluded_foreign=sum(not r['is_uae_real_estate_relevant'] for r in upstream_entities[5]) if upstream_entities else 0,
                    excluded_ineligible=sum(not r['is_real_estate_relevant'] for r in upstream_entities[6]) if upstream_entities else 0)
    return tuple(result),identity((semantic,exclusions)),exclusions


def build(contexts,urls,report,policy):
    articles=[];entities=[];events=[];event_links=[];observations=[];series={};points=[]
    counts=Counter({key:0 for key in ('qualified_articles','missing_article_url','price_observations','rent_observations',
        'transaction_observations','resolved_periods','unresolved_periods','FORECAST','SOURCE_REPORTED_CHANGE','NON_EXACT',
        'UNRESOLVED_PERIOD','UNKNOWN_GEOGRAPHY','indexed_points','period_lookups','conflicting_observations',
        'MISSING_COMPARISON_PERIOD','ZERO_DENOMINATOR','SOURCE_CONFLICT','MOM','QOQ','YOY')})
    counts.update(report.counts)
    for ordinal,c in enumerate(contexts,1):
        report.active_record=ordinal
        a,u,e,m=c.article,c.entities,c.events,c.metrics
        articles.append(dict(metric_result_id=m.metric_result_id,source_id=a.source_id,source_name=a.source_name,rss_url=str(a.rss_url),
            article_url=urls.get((a.source_id,a.article_id,a.raw_hash)),published_at=a.normalized_published_at.isoformat() if a.normalized_published_at else None,
            retrieved_at=a.retrieved_at.isoformat(),location_scope=u.location_scope.value,stage8_accepted=1,stage9_accepted=1))
        counts['qualified_articles']+=1
        counts['missing_article_url']+=int(articles[-1]['article_url'] is None)
        seen=set()
        for index,mention in enumerate(u.mentions):
            if mention.entity_id in seen: continue
            seen.add(mention.entity_id)
            entities.append(dict(metric_result_id=m.metric_result_id,entity_id=mention.entity_id,extraction_id=u.extraction_id,mention_index=index))
        for event in e.events:
            events.append(dict(event_id=event.event_id,metric_result_id=m.metric_result_id,event_type=event.event_type.value))
            event_links.extend(dict(event_id=event.event_id,entity_id=link.entity_id) for link in event.entity_links)
        for o in m.observations:
            report.active_component='PERIOD_RESOLUTION'
            period=resolve_period(o.reported_period_text)
            report.active_component='SERIES'
            geo=geography(o.entity_links)
            report.active_component='COMPARABILITY'
            reason=exclusion(o,period,geo);s=None
            if reason is None:
                report.active_component='SERIES'
                s=Series(*geo,a.source_id,o.metric.value,o.property_type.value,o.statistic,o.currency.value if o.currency else '',o.unit.value,o.nature.value,period.frequency)
                series[s.series_id]=s;points.append(Point(o.observation_id,s,period,o.value))
            observations.append(dict(observation_id=o.observation_id,metric_result_id=m.metric_result_id,family=family(o.metric.value),
                metric=o.metric.value,property_type=o.property_type.value,nature=o.nature.value,provenance='SOURCE_REPORTED',
                entity_id=geo[0],entity_type=geo[1],scope=geo[2],period=period.label if period else None,
                frequency=period.frequency if period else None,period_ordinal=period.ordinal if period else None,
                series_id=s.series_id if s else None,exclusion_reason=reason))
            counts[family(o.metric.value).lower()+'_observations']+=1
            counts['resolved_periods' if period else 'unresolved_periods']+=1
            if reason: counts[reason]+=1
    report.active_record=None
    report.active_component='MOVEMENT'
    movements,movement_counts,unavailable=calculate(points,report.market_movement_version,policy)
    counts.update(movement_counts)
    report.active_component='RANKING'
    rankings=rank(movements,report.ranking_version)
    counts.update(events=len(events),observations=len(observations),series=len(series),movements=len(movements),rankings=len(rankings),
                  ranking_candidates=sum(len(r['entries']) for r in rankings),
                  increase_entries=sum(len(r['entries']) for r in rankings if r['dimensions']['direction']=='INCREASE'),
                  decrease_entries=sum(len(r['entries']) for r in rankings if r['dimensions']['direction']=='DECREASE'))
    report.counts=dict(counts)
    return Bundle(tuple(articles),tuple(entities),tuple(events),tuple(event_links),tuple(observations),tuple(series.values()),movements,unavailable,rankings)
