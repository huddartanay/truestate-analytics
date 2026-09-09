"""Pure clause-bounded event instances with exact clean-text evidence."""
from __future__ import annotations
import re

from intelligence import config as cfg
from intelligence.enums import EventDirection
from intelligence.errors import EventExtractionError
from intelligence.schemas import (CleanArticle, EntityExtractionResult, RealEstateRelevanceResult,
                                  UAERealEstateRelevanceResult, EventEntityLink, RealEstateEvent)
from intelligence.entities.normalize import mapped_normalize
from intelligence.events import rules
from intelligence.events.identity import event_id, result_id

# Conjunction splitting deliberately favors conservative independent subjects;
# pronouns and omitted subjects never inherit entities from another clause.
BREAK = re.compile(r'(?<!\d)[.,،]|[.,،](?!\d)|[!?;\n؛。！？]+|\b(?:while|whereas|but|and|as|بينما|ولكن|لكن)\b', re.I)


def clauses(text):
    start = 0
    for match in BREAK.finditer(text):
        if match.start() > start:
            yield start, match.start()
        start = match.end()
    if start < len(text):
        yield start, len(text)


def associations(article, upstream, field, clause_start, clause_end, start, end):
    text = article.clean_title if field == 'TITLE' else article.clean_body
    found = {}
    for index, mention in enumerate(upstream.mentions):
        if mention.source_field != field or mention.start_offset < clause_start or mention.end_offset > clause_end:
            continue
        left, right = (mention.end_offset, start) if mention.end_offset <= start else (end, mention.start_offset)
        distance = len(re.findall(r'\w+', text[left:right])) if right > left else 0
        if distance <= 12:
            rank = (distance, index)
            if mention.entity_id not in found or rank < found[mention.entity_id][0]:
                found[mention.entity_id] = (rank, index)
    if len(found) > 32:
        raise EventExtractionError('Event association limit exceeded')
    return tuple(EventEntityLink(entity_id=identity, mention_index=found[identity][1]) for identity in sorted(found))


def candidates(article, upstream, version=cfg.EVENT_EXTRACTION_VERSION):
    """Mechanics for already validated evidence; public extract checks gates."""
    identity = result_id(upstream.extraction_id, version)
    events = []
    for field, text in (('TITLE', article.clean_title), ('BODY', article.clean_body)):
        for left, right in clauses(text):
            value, mapping = mapped_normalize(text[left:right])
            if rules.NEGATION.search(value) or rules.HISTORICAL.search(value) or rules.COLLISION.search(value):
                continue
            forward = bool(rules.FORWARD.search(value))
            selected = []
            for rule in rules.RULES:
                if field not in rule.fields or (forward and not rule.forecast_allowed):
                    continue
                if rule.context and not rule.context.search(value):
                    continue
                match = rule.pattern.search(value)
                if match:
                    selected.append((rule, match))
            kinds = {r.event_type for r, _ in selected}
            suppressed = set().union(*(rules.SUPPRESSES.get(kind, set()) for kind in kinds))
            for rule, match in sorted(selected, key=lambda item: (-item[0].priority, item[0].rule_id)):
                if rule.event_type in suppressed:
                    continue
                start, end = left + mapping[match.start()][0], left + mapping[match.end()-1][1]
                evidence = text[start:end]
                if len(evidence) > 640:
                    raise EventExtractionError('Event evidence limit exceeded')
                directions = {name for name, pattern in rules.DIRECTIONS if rule.directional and pattern.search(match.group())}
                direction = next(iter(directions)) if len(directions) == 1 else 'UNKNOWN'
                links = associations(article, upstream, field, left, right, start, end)
                events.append(RealEstateEvent(event_id=event_id(identity,rule.event_type.value,field,start,end,
                    rule.rule_id,direction,evidence,links),event_result_id=identity,event_type=rule.event_type,
                    rule_id=rule.rule_id,source_field=field,matched_text=evidence,start_offset=start,end_offset=end,
                    confidence='HIGH' if field=='TITLE' else 'MEDIUM',direction=direction,entity_links=links))
                if len(events) > 128:
                    raise EventExtractionError('Event count limit exceeded')
    return tuple(sorted(events,key=lambda e:(e.source_field!='TITLE',e.start_offset,e.end_offset,e.event_type.value,e.event_id)))


def validate_input(article, upstream, stage9, stage8):
    if not all(isinstance(obj, kind) for obj, kind in ((article,CleanArticle),(upstream,EntityExtractionResult),
            (stage9,UAERealEstateRelevanceResult),(stage8,RealEstateRelevanceResult))):
        raise EventExtractionError('Validated clean and Stage 8/9/10 evidence required')
    if not stage8.is_real_estate_relevant or not stage9.is_uae_real_estate_relevant:
        raise EventExtractionError('Upstream relevance gates must accept')
    for name in ('article_id','raw_hash','cleaning_version','dedup_version','relevance_version','context_id','group_id'):
        if not getattr(upstream,name)==getattr(stage9,name)==getattr(stage8,name):
            raise EventExtractionError('Upstream context mismatch')
    if (upstream.uae_relevance_version,upstream.registry_version)!=(stage9.uae_relevance_version,stage9.registry_version):
        raise EventExtractionError('Stage 9 versions mismatch')
    if (article.article_id,article.raw_hash,article.cleaning_version)!=(upstream.article_id,upstream.raw_hash,upstream.cleaning_version):
        raise EventExtractionError('Clean identity mismatch')
    for mention in upstream.mentions:
        text = article.clean_title if mention.source_field=='TITLE' else article.clean_body
        if text[mention.start_offset:mention.end_offset]!=mention.matched_text:
            raise EventExtractionError('Stage 10 mention disagrees with clean evidence')


def validate_events(events, article, upstream, version=cfg.EVENT_EXTRACTION_VERSION):
    known = {r.rule_id:r for r in rules.RULES}
    if len(events)>128:
        raise EventExtractionError('Event limit exceeded')
    for event in events:
        text = article.clean_title if event.source_field=='TITLE' else article.clean_body
        rule = known.get(event.rule_id)
        if rule is None or rule.event_type!=event.event_type or event.event_result_id!=result_id(upstream.extraction_id,version):
            raise EventExtractionError('Invalid rule or event lineage')
        if text[event.start_offset:event.end_offset]!=event.matched_text:
            raise EventExtractionError('Invalid event evidence offset')
        clause = next(((a,b) for a,b in clauses(text) if a<=event.start_offset<event.end_offset<=b), None)
        if clause is None or event.entity_links!=associations(article,upstream,event.source_field,*clause,event.start_offset,event.end_offset):
            raise EventExtractionError('Invalid event entity associations')
        evidence = mapped_normalize(event.matched_text)[0]
        value = mapped_normalize(text[clause[0]:clause[1]])[0]
        if (not rule.pattern.fullmatch(evidence) or rules.NEGATION.search(value)
            or rules.HISTORICAL.search(value) or rules.COLLISION.search(value)
            or (rules.FORWARD.search(value) and not rule.forecast_allowed)
            or (rule.context and not rule.context.search(value))):
            raise EventExtractionError('Evidence does not satisfy event rule safeguards')
        directions = {name for name, pattern in rules.DIRECTIONS if rule.directional and pattern.search(evidence)}
        expected = next(iter(directions)) if len(directions)==1 else 'UNKNOWN'
        if event.direction.value!=expected:
            raise EventExtractionError('Direction disagrees with event evidence')


def extract(article, upstream, stage9, stage8, *, version=cfg.EVENT_EXTRACTION_VERSION):
    validate_input(article,upstream,stage9,stage8)
    events = candidates(article,upstream,version)
    validate_events(events,article,upstream,version)
    return events
