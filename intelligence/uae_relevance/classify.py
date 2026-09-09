"""Pure Stage 9 decision from validated, eligible Stage 8 input and clean text."""
from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass

from intelligence.enums import Region, SourceTier
from intelligence.errors import UAERelevanceError
from intelligence.relevance.classify import normalize, pattern, HIGH, CONTEXT, MASKS
from intelligence.schemas import CleanArticle, RealEstateRelevanceResult
from intelligence.sources.registry import all_sources
from intelligence.uae_relevance import rules

GEO = tuple((label, pattern(phrase)) for label, phrases in rules.GEO.items() for phrase in phrases)
SUPPRESS = tuple((label, pattern(phrase)) for label, phrases in rules.INCIDENTAL.items() for phrase in phrases)
FOREIGN = tuple(pattern(phrase) for phrase in rules.FOREIGN)
PROPERTY = tuple(regex for _, _, regex in HIGH) + tuple(pattern(p) for p in rules.PROPERTY_EXTRA) + (CONTEXT,)


@dataclass(frozen=True)
class Decision:
    uae_relevance_score: int
    is_uae_real_estate_relevant: bool
    confidence: str
    source_context: str
    acceptance_threshold: int
    matched_uae_signals: tuple[str, ...]
    matched_exclusion_signals: tuple[str, ...]
    decision_reason: str


def source_policy(source_id):
    source = next((s for s in all_sources() if s.source_id == source_id), None)
    if source is None:
        raise UAERelevanceError('Canonical source is not registered')
    local = source.country == 'AE' and source.region != Region.INTERNATIONAL and source.source_tier != SourceTier.TIER_3
    return ('LOCAL_UAE', 3) if local else ('INTERNATIONAL', 4)


def _scan(text, location):
    positive, negative, direct = set(), set(), {}
    geo_seen = False
    total = max(1, len(normalize(text).split()))
    # No co-occurrence across sentence/semicolon/newline boundaries. Commas
    # remain within a sentence to permit material multi-emirate discussion.
    for sentence in re.split(r'[.!?;\n؛。！？]+', text):
        value = normalize(sentence)
        if not value:
            continue
        hits = [(label, match) for label, regex in GEO for match in regex.finditer(value)]
        prop = [m for regex in PROPERTY for m in regex.finditer(value)]
        for token in ('RAK', 'UAQ'):
            if re.search(r'(?<!\w)'+token+r'(?!\w)', sentence) and prop:
                hits.extend((token.lower(), m) for m in pattern(token).finditer(value))
        if pattern('emirates').search(value) and not pattern('united arab emirates').search(value):
            if re.search(r'\b(?:in|across|throughout) the emirates\b', value) and prop:
                hits.extend(('uae', m) for m in pattern('emirates').finditer(value))
            else:
                negative.add('ambiguous_emirates_brand')
        geo_seen |= bool(hits)
        blocked = {label for label, regex in SUPPRESS if regex.search(value)}
        if any(regex.search(value) for _, regex in MASKS):
            blocked.add('non_property_collision')
        # A country list or foreign-property clause is ambiguous even when
        # geography and property happen to be close. A separate UAE sentence
        # can establish material focus without this sentence supplying points.
        if hits and any(regex.search(value) for regex in FOREIGN):
            blocked.add('mixed_foreign_context')
        if blocked:
            negative.update(blocked)
            continue
        starts = [m.start() for m in re.finditer(r'\S+', value)]
        matched = set()
        for label, geo in hits:
            gs, ge = bisect_left(starts, geo.start()), bisect_left(starts, geo.end())
            for p in prop:
                ps, pe = bisect_left(starts, p.start()), bisect_left(starts, p.end())
                if max(0, ps-ge, gs-pe) <= rules.PROXIMITY_TOKENS:
                    matched.add(label)
                    break
        if matched:
            positive.update('geo:'+label for label in matched)
            positive.add(location+'_geo_property_proximity')
            # Identical repeated sentences cannot manufacture material focus.
            direct[value] = len(starts)
    return geo_seen, direct, sum(direct.values()) / total, positive, negative


def classify(article: CleanArticle, upstream: RealEstateRelevanceResult) -> Decision:
    if not isinstance(article, CleanArticle) or not isinstance(upstream, RealEstateRelevanceResult):
        raise UAERelevanceError('Validated clean article and Stage 8 result required')
    if not upstream.is_real_estate_relevant:
        raise UAERelevanceError('Stage 8 rejected context is ineligible')
    if (article.article_id, article.raw_hash, article.cleaning_version) != (upstream.article_id, upstream.raw_hash, upstream.cleaning_version):
        raise UAERelevanceError('Stage 8 identity does not match cleaned evidence')
    source_context, threshold = source_policy(article.source_id)
    tg, td, _, tp, tn = _scan(article.clean_title, 'title')
    bg, bd, share, bp, bn = _scan(article.clean_body, 'body')
    positives, negatives = tp | bp, tn | bn
    if td:
        score, reason = (5, 'Direct title and body UAE property focus') if bd and share >= rules.BODY_DIRECT_MIN_SHARE else (4, 'Direct UAE property title')
    elif len(bd) >= 2 and share >= rules.BODY_MATERIAL_MIN_SHARE:
        score, reason = 4, 'Material UAE property body section'
    elif bd and share >= rules.BODY_DIRECT_MIN_SHARE:
        score, reason = 3, 'Clear body UAE property connection'
    elif bd:
        score, reason = 2, 'Direct body evidence diluted below focus threshold'
        negatives.add('insufficient_uae_focus')
    elif tg or bg or 'ambiguous_emirates_brand' in negatives:
        score, reason = 1, 'Incidental or ambiguous UAE context'
        negatives.add('weak_geo_context')
    else:
        score, reason = 0, 'No UAE geographic property connection'
        negatives.add('international_property_without_uae_focus')
    if source_context == 'INTERNATIONAL' and score == 3:
        negatives.add('international_requires_stronger_focus')
    return Decision(score, score >= threshold,
                    'HIGH' if score in (0, 4, 5) else 'MEDIUM' if score == 3 else 'LOW',
                    source_context, threshold,
                    tuple(sorted(positives)[:rules.MAX_EVIDENCE]), tuple(sorted(negatives)[:rules.MAX_EVIDENCE]),
                    f'score={score}; {reason}; body_direct={len(bd)}; body_share={share:.6f}; threshold={threshold}')
