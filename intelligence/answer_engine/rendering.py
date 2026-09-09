"""Fail-closed factual validation; final prose contains no untrusted model draft."""
import html
import re
from decimal import Decimal
from intelligence.query.resolution import entities
from intelligence.answer_engine.models import Generated,RenderedClaim

FIELDS=('value','unit','location','period','provenance','nature','rank')

def _numbers(text):
    text=re.sub(r'\[E\d+\]','',text)
    return {Decimal(n.replace(',','')) for n in re.findall(r'(?<![\w])[+-]?\d[\d,]*(?:\.\d+)?',text)}

def validate(package,generated):
    generated=Generated.model_validate(generated)
    if generated.status!=package.status:raise ValueError('STATUS_MISMATCH')
    if [c.evidence_id for c in generated.claims]!=[f.evidence_id for f in package.facts]:raise ValueError('CLAIM_COVERAGE_OR_ORDER')
    for claim,fact in zip(generated.claims,package.facts):
        if any(getattr(claim,k)!=getattr(fact,k) for k in FIELDS):raise ValueError('FACT_FIELD_MISMATCH')
        if claim.text:
            # Drafts are advisory and never published. Reject detectable contradictory factual content too.
            text=claim.text
            if set(re.findall(r'\bE\d+\b',text))-{fact.evidence_id}:raise ValueError('DRAFT_CITATION_MISMATCH')
            allowed=' '.join(str(getattr(fact,k) or '') for k in ('value','period','rank','title'))
            if _numbers(text)-_numbers(allowed):raise ValueError('DRAFT_NUMBER_MISMATCH')
            remainder=text.replace(fact.location,'').replace(fact.title or '\0','')
            if entities(remainder):raise ValueError('DRAFT_LOCATION_MISMATCH')
            if re.search(r'\b(?:Singapore|London|Saudi|India|Tokyo|Abu Dhabi|Dubai|Sharjah|RAK)\b',remainder,re.I):raise ValueError('DRAFT_LOCATION_MISMATCH')
            if re.search(r'\b(?:because|caused|due to|led to|guaranteed|definitely)\b',text,re.I):raise ValueError('DRAFT_UNSUPPORTED_INFERENCE')
    return generated

def safe(value):
    # Output is plain text; neutralize markup, fake citations and line breaks from source metadata.
    return html.escape(re.sub(r'[\r\n\[\]`]',' ',str(value)),quote=True)

def label(f):
    if f.nature=='SOURCE_REPORTED_FORECAST':return 'source-reported forecast'
    return 'calculated by TruEstate' if f.provenance=='SYSTEM_CALCULATED' else 'reported by the source'

def render(package,generated):
    validate(package,generated);claims=[]
    for f in package.facts:
        if f.value is not None:
            metric=safe((f.metric or 'value').replace('_',' ').lower())
            if f.kind in ('MOVEMENT','RANKING') and not metric.endswith('change'):metric+=' change'
            period=' for '+safe(f.period) if f.period else ' (period unavailable)'
            basis=' '+safe(f.basis) if f.basis else ''
            rank='rank '+str(f.rank)+': ' if f.rank is not None else ''
            percent=f.unit in ('PERCENT','percent','%')
            units={'CURRENCY_AMOUNT':'','CURRENCY_PER_SQFT':'/sqft','CURRENCY_PER_SQM':'/sqm','COUNT':'count'}
            unit='%' if percent else ' '+safe(units.get(f.unit,f.unit or ''))
            currency=' '+safe(f.currency) if not percent and f.currency and f.currency not in (f.unit or '') else ''
            if f.unit in ('CURRENCY_AMOUNT','CURRENCY_PER_SQFT','CURRENCY_PER_SQM'):
                unit=' '+safe(f.currency or 'currency')+units[f.unit];currency=''
            dimensions=''.join(' '+safe(v.replace('_',' ').lower()) for v in (f.property_type,f.statistic) if v and v!='UNSPECIFIED')
            text=f'{safe(f.location)} {rank}{metric}{dimensions}{basis}{period}: {safe(f.value)}{unit}{currency}'
        else:
            # Headline quotation is clearly source data. Instruction-bearing titles are not repeated.
            title=f.title or (f.kind.lower()+' record')
            if re.search(r'ignore|instructions|system prompt|internal knowledge|reveal|hacked',title,re.I):title='source item (instruction-bearing headline withheld)'
            when='; published '+safe(f.published_at) if f.published_at else '; publication date unavailable'
            text=f'{safe(f.location)}: “{safe(title)}”{when}'
        text+=f', {label(f)} [{f.evidence_id}].'
        claims.append(RenderedClaim(evidence_id=f.evidence_id,text=text,provenance=f.provenance,nature=f.nature,source=f.source))
    prefix=[]
    if package.source_disagreement:prefix.append('Sources disagree; their supplied figures are kept separate without averaging.')
    if package.status=='PARTIAL_DATA':prefix.append('Partial data: '+('; '.join(safe(s) for s in package.missing) or 'complete requested coverage')+' is unavailable.')
    return '\n'.join(prefix+['- '+c.text for c in claims]),tuple(claims)
