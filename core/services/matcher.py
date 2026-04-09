import difflib
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence


ACCESSORY_KEYWORDS = {
    'accessory',
    'adapter',
    'backcover',
    'bag',
    'battery',
    'bundle',
    'cable',
    'case',
    'charger',
    'cover',
    'glass',
    'guard',
    'keyboard',
    'mount',
    'mouse',
    'pouch',
    'protector',
    'replacement',
    'screen',
    'skin',
    'sleeve',
    'strap',
}

ACCESSORY_PHRASES = {
    'screen protector',
    'tempered glass',
    'back cover',
    'phone case',
    'laptop sleeve',
    'replacement battery',
}

REFURBISHED_KEYWORDS = {
    'refurbished',
    'renewed',
    'preowned',
    'pre-owned',
    'used',
    'secondhand',
    'second-hand',
    'openbox',
    'open-box',
}

SOFT_VARIANT_KEYWORDS = {
    'black',
    'blue',
    'gold',
    'gray',
    'green',
    'grey',
    'midnight',
    'natural',
    'navy',
    'pink',
    'purple',
    'red',
    'rose',
    'silver',
    'space',
    'starlight',
    'teal',
    'titanium',
    'violet',
    'white',
    'yellow',
}

MAJOR_VARIANT_KEYWORDS = {
    'air',
    'classic',
    'edge',
    'fan',
    'fe',
    'flip',
    'fold',
    'lite',
    'max',
    'mini',
    'neo',
    'note',
    'plus',
    'prime',
    'pro',
    'slim',
    'ultra',
}

STOPWORDS = {
    'a',
    'all',
    'and',
    'edition',
    'for',
    'inch',
    'inches',
    'latest',
    'new',
    'of',
    'series',
    'smartphone',
    'the',
    'with',
}

TECHNICAL_VARIANT_PATTERN = re.compile(
    r'\b(?:\d+(?:\.\d+)?(?:gb|tb|inch|in|cm|mm|mah|hz)|[a-z]{1,3}\d{1,4}|gen\d+)\b'
)

TOKEN_PATTERN = re.compile(r'[a-z0-9]+(?:\.[a-z0-9]+)?')


@dataclass
class QueryProfile:
    raw_query: str
    normalized_query: str
    tokens: set[str]
    family_tokens: set[str]
    core_tokens: set[str]
    major_variant_tokens: set[str]
    technical_variant_tokens: set[str]
    hard_variant_tokens: set[str]
    soft_variant_tokens: set[str]
    accessory_requested: bool
    refurbished_requested: bool


@dataclass
class CandidateProfile:
    title: str
    normalized_title: str
    tokens: set[str]
    family_tokens: set[str]
    major_variant_tokens: set[str]
    technical_variant_tokens: set[str]
    hard_variant_tokens: set[str]
    soft_variant_tokens: set[str]
    has_accessory_keywords: bool
    has_refurbished_keywords: bool


@dataclass
class CandidateAssessment:
    candidate: object
    profile: CandidateProfile
    kind: str
    confidence: float
    reason: str
    signature: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class MatchDecision:
    state: str
    accepted_candidate: Optional[object] = None
    confidence: Optional[float] = None
    diagnostic_message: str = ''
    matched_title: str = ''
    candidate_count: int = 0


def _normalize_text(text: str) -> str:
    text = (text or '').lower()
    text = text.replace('&', ' and ')
    text = text.replace('+', ' plus ')
    text = text.replace('/', ' ')
    text = text.replace('-', ' ')
    text = text.replace('(', ' ')
    text = text.replace(')', ' ')
    text = text.replace(',', ' ')
    text = text.replace('"', ' inch ')
    text = text.replace("'", ' ')
    text = re.sub(r'(\d+(?:\.\d+)?)\s*(gb|tb|inch|in|cm|mm|mah|hz)\b', r'\1\2', text)
    text = re.sub(r'gen\s+(\d+)\b', r'gen\1', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _contains_phrase(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_text(text)
    return {token for token in TOKEN_PATTERN.findall(normalized) if len(token) > 1}


def _extract_technical_variants(text: str) -> set[str]:
    normalized = _normalize_text(text)
    return {match.group(0) for match in TECHNICAL_VARIANT_PATTERN.finditer(normalized)}


def _extract_major_variants(tokens: Iterable[str]) -> set[str]:
    return {token for token in tokens if token in MAJOR_VARIANT_KEYWORDS}


def _extract_soft_variants(tokens: Iterable[str]) -> set[str]:
    return {token for token in tokens if token in SOFT_VARIANT_KEYWORDS}


def _build_profile(text: str, *, raw_query: Optional[str] = None) -> QueryProfile | CandidateProfile:
    normalized = _normalize_text(text)
    tokens = _tokenize(text)
    technical_variant_tokens = _extract_technical_variants(text)
    major_variant_tokens = _extract_major_variants(tokens)
    soft_variant_tokens = _extract_soft_variants(tokens)
    family_tokens = {
        token for token in tokens
        if token not in STOPWORDS
        and token not in ACCESSORY_KEYWORDS
        and token not in REFURBISHED_KEYWORDS
        and token not in SOFT_VARIANT_KEYWORDS
    }
    core_tokens = family_tokens - technical_variant_tokens
    hard_variant_tokens = technical_variant_tokens | major_variant_tokens
    accessory_requested = _contains_phrase(normalized, ACCESSORY_PHRASES) or bool(tokens & ACCESSORY_KEYWORDS)
    refurbished_requested = bool(tokens & REFURBISHED_KEYWORDS)

    if raw_query is not None:
        return QueryProfile(
            raw_query=raw_query,
            normalized_query=normalized,
            tokens=tokens,
            family_tokens=family_tokens,
            core_tokens=core_tokens,
            major_variant_tokens=major_variant_tokens,
            technical_variant_tokens=technical_variant_tokens,
            hard_variant_tokens=hard_variant_tokens,
            soft_variant_tokens=soft_variant_tokens,
            accessory_requested=accessory_requested,
            refurbished_requested=refurbished_requested,
        )

    return CandidateProfile(
        title=text,
        normalized_title=normalized,
        tokens=tokens,
        family_tokens=family_tokens,
        major_variant_tokens=major_variant_tokens,
        technical_variant_tokens=technical_variant_tokens,
        hard_variant_tokens=hard_variant_tokens,
        soft_variant_tokens=soft_variant_tokens,
        has_accessory_keywords=_contains_phrase(normalized, ACCESSORY_PHRASES) or bool(tokens & ACCESSORY_KEYWORDS),
        has_refurbished_keywords=bool(tokens & REFURBISHED_KEYWORDS),
    )


def build_query_profile(query: str) -> QueryProfile:
    return _build_profile(query, raw_query=query)


def build_candidate_profile(title: str) -> CandidateProfile:
    return _build_profile(title)


def calculate_match_score(query, title):
    """
    Fuzzy similarity used only as a tiebreaker between already-eligible candidates.
    """
    if not query or not title:
        return 0.0

    query = _normalize_text(query)
    title = _normalize_text(title)

    if query in title:
        return 1.0

    query_tokens = [t for t in query.split() if len(t) > 1]
    if not query_tokens:
        return difflib.SequenceMatcher(None, query, title).ratio()

    matches = sum(1 for token in query_tokens if token in title)
    token_score = matches / len(query_tokens)
    seq_score = difflib.SequenceMatcher(None, query, title).ratio()
    return (token_score * 0.7) + (seq_score * 0.3)


def _variant_signature(profile: CandidateProfile) -> tuple[str, ...]:
    signature = sorted(profile.major_variant_tokens | profile.technical_variant_tokens)
    return tuple(signature) if signature else ('base',)


def _confidence_for(query: QueryProfile, candidate_title: str, *, exact: bool, is_sponsored: bool, rank: int) -> float:
    fuzzy = calculate_match_score(query.raw_query, candidate_title)
    base = 0.82 if exact else 0.58
    base += max(0.0, 0.1 - min(rank, 10) * 0.01)
    if query.hard_variant_tokens:
        base += 0.04
    if is_sponsored:
        base -= 0.08
    return round(max(0.0, min(0.99, base + (fuzzy * 0.08))), 3)


def evaluate_candidate(query: QueryProfile, candidate) -> Optional[CandidateAssessment]:
    profile = build_candidate_profile(candidate.title)

    if profile.has_accessory_keywords and not query.accessory_requested:
        return None

    if profile.has_refurbished_keywords and not query.refurbished_requested:
        return None

    if not query.core_tokens.issubset(profile.tokens):
        return None

    missing_hard_tokens = query.hard_variant_tokens - profile.hard_variant_tokens
    unexpected_major_variants = profile.major_variant_tokens - query.major_variant_tokens
    signature = _variant_signature(profile)

    if missing_hard_tokens or unexpected_major_variants:
        return CandidateAssessment(
            candidate=candidate,
            profile=profile,
            kind='family',
            confidence=_confidence_for(
                query,
                candidate.title,
                exact=False,
                is_sponsored=getattr(candidate, 'is_sponsored', False),
                rank=getattr(candidate, 'rank', 0),
            ),
            reason='Family match found, but the exact variant is unclear.',
            signature=signature,
        )

    return CandidateAssessment(
        candidate=candidate,
        profile=profile,
        kind='exact',
        confidence=_confidence_for(
            query,
            candidate.title,
            exact=True,
            is_sponsored=getattr(candidate, 'is_sponsored', False),
            rank=getattr(candidate, 'rank', 0),
        ),
        reason='Exact variant matched.',
        signature=signature,
    )


def choose_best_candidate(candidates: Sequence[CandidateAssessment]) -> CandidateAssessment:
    return sorted(
        candidates,
        key=lambda item: (
            item.confidence,
            -getattr(item.candidate, 'rank', 0),
            0 if getattr(item.candidate, 'is_sponsored', False) else 1,
        ),
        reverse=True,
    )[0]


def evaluate_scrape_candidates(query: str, candidates: Sequence[object]) -> MatchDecision:
    if not candidates:
        return MatchDecision(
            state='not_found',
            diagnostic_message='The source returned no product candidates.',
            candidate_count=0,
        )

    query_profile = build_query_profile(query)
    assessments: List[CandidateAssessment] = []
    for candidate in candidates:
        assessment = evaluate_candidate(query_profile, candidate)
        if assessment:
            assessments.append(assessment)

    if not assessments:
        return MatchDecision(
            state='not_found',
            diagnostic_message='No candidate covered all required model tokens.',
            candidate_count=len(candidates),
        )

    exact_matches = [item for item in assessments if item.kind == 'exact']
    family_matches = [item for item in assessments if item.kind == 'family']

    if exact_matches:
        signatures = {item.signature for item in exact_matches}
        if len(signatures) > 1:
            best_family = choose_best_candidate(exact_matches)
            return MatchDecision(
                state='ambiguous',
                diagnostic_message='Multiple plausible variants were found for this source.',
                matched_title=best_family.candidate.title,
                confidence=best_family.confidence,
                candidate_count=len(candidates),
            )

        best = choose_best_candidate(exact_matches)
        return MatchDecision(
            state='matched',
            accepted_candidate=best.candidate,
            confidence=best.confidence,
            diagnostic_message=best.reason,
            matched_title=best.candidate.title,
            candidate_count=len(candidates),
        )

    if family_matches:
        best_family = choose_best_candidate(family_matches)
        return MatchDecision(
            state='ambiguous',
            diagnostic_message='Matching family results were found, but the exact variant was unclear.',
            matched_title=best_family.candidate.title,
            confidence=best_family.confidence,
            candidate_count=len(candidates),
        )

    return MatchDecision(
        state='not_found',
        diagnostic_message='No confident candidate could be accepted for this source.',
        candidate_count=len(candidates),
    )
