"""Exact alias mentions and registry-derived scope; no event interpretation."""
from __future__ import annotations
import re
from bisect import bisect_left
from dataclasses import dataclass

from intelligence.enums import Emirate, EntityType
from intelligence.errors import EntityExtractionError
from intelligence.schemas import CleanArticle, RealEstateRelevanceResult, UAERealEstateRelevanceResult, EntityMention
from intelligence.entities.normalize import normalize, mapped_normalize
from intelligence.entities.registry import REGISTRY
from intelligence.relevance.classify import HIGH, CONTEXT


@dataclass(frozen=True)
class Extraction:
    location_scope: Emirate
    mentions: tuple[EntityMention,...]
    entity_ids: tuple[str,...]


def _abbreviation_context(text,start,end,matched):
    if matched not in ('RAK','UAQ'):return False
    left=max([m.end() for m in re.finditer(r'[.!?;\n؛]',text[:start])] or [0])
    stop=re.search(r'[.!?;\n؛]',text[end:]);right=end+stop.start() if stop else len(text)
    value,mapping=mapped_normalize(text[left:right])
    indexes=[i for i,(s,e) in enumerate(mapping) if s < end-left and e > start-left]
    if not indexes:return False
    starts=[m.start() for m in re.finditer(r'\S+',value)]
    a,b=bisect_left(starts,min(indexes)),bisect_left(starts,max(indexes)+1)
    for regex in tuple(r for _,_,r in HIGH)+(CONTEXT,):
        for match in regex.finditer(value):
            c,d=bisect_left(starts,match.start()),bisect_left(starts,match.end())
            if max(0,c-b,a-d)<=8:return True
    return False


def _mentions(text,source_field,registry):
    value,mapping=mapped_normalize(text);candidates=[]
    for alias,entity,policy,regex in registry.matchers:
        for match in regex.finditer(value):
            start,end=mapping[match.start()][0],mapping[match.end()-1][1]
            matched=text[start:end]
            if len(matched)>160:raise EntityExtractionError('Matched span exceeds bounded mention contract')
            if policy.abbreviation and not _abbreviation_context(text,start,end,matched):continue
            # Arabic country alias must not normalize an airline brand as country.
            if entity.entity_type==EntityType.COUNTRY and normalize(matched)=='الامارات' and normalize(text[max(0,start-12):start]).endswith('طيران'):
                continue
            candidates.append((match.start(),match.end(),start,end,alias,entity,policy))
    # Globally prefer longer overlapping aliases. Equal lengths use position
    # and stable entity ID. Distinct non-overlapping occurrences survive.
    occupied=set();selected=[]
    for a,b,start,end,alias,entity,policy in sorted(candidates,key=lambda c:(-(c[1]-c[0]),c[0],c[5].entity_id)):
        positions=range(a,b)
        if any(i in occupied for i in positions):continue
        occupied.update(positions)
        selected.append(EntityMention(entity_id=entity.entity_id,canonical_name=entity.canonical_name,
            entity_type=entity.entity_type,parent_entity_id=entity.parent_entity_id,matched_text=text[start:end],
            normalized_alias=alias,source_field=source_field,start_offset=start,end_offset=end,
            confidence='MEDIUM' if policy.abbreviation else 'HIGH',
            extraction_method='CONTEXT_ABBREVIATION' if policy.abbreviation else 'EXACT_ALIAS'))
    return tuple(sorted(selected,key=lambda m:(m.start_offset,m.end_offset,m.entity_id)))


def scope_for(mentions,registry=REGISTRY):
    emirates={registry.entities[m.entity_id].emirate for m in mentions
              if registry.entities[m.entity_id].entity_type not in (EntityType.COUNTRY,EntityType.DEVELOPER)}
    emirates.discard(None)
    if len(emirates)>1:return Emirate.MULTI_EMIRATE
    if emirates:return next(iter(emirates))
    if any(m.entity_type==EntityType.COUNTRY for m in mentions):return Emirate.UAE_WIDE
    return Emirate.UNKNOWN


def extract(article: CleanArticle, upstream: UAERealEstateRelevanceResult,
            stage8: RealEstateRelevanceResult, *, registry=REGISTRY):
    if not isinstance(article,CleanArticle) or not isinstance(upstream,UAERealEstateRelevanceResult) or not isinstance(stage8,RealEstateRelevanceResult):
        raise EntityExtractionError('Validated Stage 8/9 context and clean evidence required')
    if not upstream.is_uae_real_estate_relevant or not stage8.is_real_estate_relevant:
        raise EntityExtractionError('Both upstream relevance gates must accept')
    for field in ('article_id','raw_hash','cleaning_version','dedup_version','relevance_version','context_id','group_id'):
        if getattr(upstream,field)!=getattr(stage8,field):raise EntityExtractionError('Upstream identity mismatch')
    if (article.article_id,article.raw_hash,article.cleaning_version)!=(upstream.article_id,upstream.raw_hash,upstream.cleaning_version):
        raise EntityExtractionError('Cleaned identity mismatch')
    mentions=_mentions(article.clean_title,'TITLE',registry)+_mentions(article.clean_body,'BODY',registry)
    if len(mentions)>256:raise EntityExtractionError('Mention count exceeds bounded extraction contract')
    return Extraction(scope_for(mentions,registry),mentions,tuple(sorted({m.entity_id for m in mentions})))


def validate_extraction(output,article,registry=REGISTRY):
    """Validate canonical typing, scope and exact clean-text offsets at boundary."""
    if len(output.mentions)>256:raise EntityExtractionError('Mention limit exceeded')
    for mention in output.mentions:
        entity=registry.entities.get(mention.entity_id)
        if entity is None or not entity.active or (mention.canonical_name,mention.entity_type,mention.parent_entity_id)!=(entity.canonical_name,entity.entity_type,entity.parent_entity_id):
            raise EntityExtractionError('Mention does not match canonical definition')
        text=article.clean_title if mention.source_field=='TITLE' else article.clean_body
        if text[mention.start_offset:mention.end_offset]!=mention.matched_text or normalize(mention.matched_text)!=mention.normalized_alias:
            raise EntityExtractionError('Mention offsets or alias do not match clean evidence')
        if mention.normalized_alias not in {normalize(a.text) for a in entity.aliases}:
            raise EntityExtractionError('Unregistered mention alias')
    if output.location_scope!=scope_for(output.mentions,registry) or output.entity_ids!=tuple(sorted({m.entity_id for m in output.mentions})):
        raise EntityExtractionError('Scope or entity identities disagree with mentions')
