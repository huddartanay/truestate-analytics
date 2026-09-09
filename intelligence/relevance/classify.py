"""Pure deterministic score; runtime timestamps and persistence are external."""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass

from intelligence import config as cfg
from intelligence.errors import RelevanceError
from intelligence.relevance import rules
from intelligence.schemas import CleanArticle


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub('[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآ', 'ااا'))
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def pattern(phrase):
    return re.compile(r'(?<!\w)' + re.escape(normalize(phrase)) + r'(?!\w)')


HIGH = tuple((category, phrase, pattern(phrase)) for category, phrases in rules.PHRASES.items() for phrase in phrases)
WEAK = tuple((phrase, pattern(phrase)) for phrase in rules.WEAK)
MASKS = tuple((category, pattern(phrase)) for category, phrases in rules.COLLISIONS.items() for phrase in phrases)
INCIDENTAL = tuple((category, pattern(phrase)) for category, phrases in rules.INCIDENTAL.items() for phrase in phrases)
BACKGROUND = tuple((category, pattern(phrase)) for category, phrases in rules.BACKGROUND.items() for phrase in phrases)
_types = '(?:' + '|'.join(re.escape(normalize(p)) for p in rules.PROPERTY_TYPES) + ')'
_actions = '(?:' + '|'.join(re.escape(normalize(p)) for p in rules.PROPERTY_ACTIONS) + ')'
_gap = r'(?:\s+\w+){0,' + str(cfg.RELEVANCE_CONTEXT_WINDOW) + r'}\s+'
CONTEXT = re.compile(r'(?<!\w)(?:' + _types + _gap + _actions + '|' + _actions + _gap + _types + r')(?!\w)')


@dataclass(frozen=True)
class Decision:
    relevance_score: int
    is_real_estate_relevant: bool
    confidence: str
    matched_positive_signals: tuple[str, ...]
    matched_negative_signals: tuple[str, ...]
    decision_reason: str


def _scan(text, location):
    positives, negatives, categories, phrases = set(), set(), set(), set()
    high_words = 0
    weak = False
    contextual = False
    # Sentence scope prevents joining a road-contract sentence to an unrelated
    # apartment mention elsewhere. Sentence suppression is intentionally strict.
    for sentence in re.split(r'[.!?;\n،؛。！？]+', text):
        value = normalize(sentence)
        for category, regex in BACKGROUND:
            if regex.search(value): negatives.add(f'{location}:{category}')
        for category, regex in MASKS:
            if regex.search(value):
                negatives.add(f'{location}:{category}')
                value = regex.sub(' ', value)
        incidental = {category for category, regex in INCIDENTAL if regex.search(value)}
        if incidental:
            negatives.update(f'{location}:{category}' for category in incidental)
            continue
        spans = set()
        starts = [m.start() for m in re.finditer(r'\S+', value)]
        for category, phrase, regex in HIGH:
            matches = list(regex.finditer(value))
            if matches:
                categories.add(category); phrases.add(phrase)
                positives.add(f'{location}:{category}:{phrase}')
                for match in matches:
                    # Count distinct token positions once even for nested phrases.
                    spans.update(range(bisect_left(starts, match.start()), bisect_left(starts, match.end())))
        high_words += len(spans)
        # A housing company's road construction is not a housing project.
        context_matches = list(CONTEXT.finditer(value))
        if any(not any(regex.search(match.group()) for category, regex in BACKGROUND if category == 'infrastructure')
               for match in context_matches):
            contextual = True
            positives.add(f'{location}:property_activity:nearby_type_and_action')
        for phrase, regex in WEAK:
            if regex.search(value):
                weak = True
                positives.add(f'{location}:weak:{phrase}')
    density = high_words / max(1, len(normalize(text).split()))
    return categories, phrases, density, weak, contextual, positives, negatives


def classify(article: CleanArticle) -> Decision:
    if not isinstance(article, CleanArticle):
        raise RelevanceError('Classification requires a validated CleanArticle')
    tc, tp, _, tw, tx, pos_t, neg_t = _scan(article.clean_title, 'title')
    bc, bp, density, bw, bx, pos_b, neg_b = _scan(article.clean_body, 'body')
    strong_body = len(bc) >= 2 and len(bp) >= 2 and density >= cfg.RELEVANCE_BODY_DENSITY
    if tc:
        score, reason = 4, 'Direct high-precision title focus'
        if strong_body and len(tc | bc) >= 2:
            score, reason = 5, 'Direct title focus supported by diverse dense body signals'
    elif tx:
        score, reason = (4, 'Property type and activity in title supported by body focus') if strong_body else (3, 'Property type and activity co-occur in title')
    elif strong_body:
        score, reason = (4, 'At least three property categories in a dense body') if len(bc) >= 3 and density >= cfg.RELEVANCE_BODY_STRONG_DENSITY else (3, 'At least two property categories in a focused body')
    elif bc or bx:
        score, reason = 2, 'Body property context lacks sufficient centrality or diversity'
    elif tw or bw:
        score, reason = 1, 'Weak terminology without direct property focus'
    else:
        score, reason = 0, 'No qualifying property focus after context safeguards'
    positives = pos_t | pos_b
    negatives = neg_t | neg_b
    if (bc or bx) and not strong_body and not (tc or tx):
        negatives.add('body:insufficient_focus')
    # Prefer high precision/context evidence over weak terms within the bound.
    evidence = sorted(positives, key=lambda s: (':weak:' in s, s))[:cfg.RELEVANCE_MAX_EVIDENCE]
    return Decision(score, score >= cfg.RELEVANCE_ACCEPT_SCORE,
                    'HIGH' if score in (0, 4, 5) else 'MEDIUM' if score == 3 else 'LOW',
                    tuple(evidence), tuple(sorted(negatives)[:cfg.RELEVANCE_MAX_EVIDENCE]),
                    f'score={score}; {reason}; title_categories={len(tc)}; '
                    f'body_categories={len(bc)}; body_density={density:.6f}')
