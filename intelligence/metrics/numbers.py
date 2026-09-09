"""Conservative decimal grammar. No locale guessing, FX or area conversion."""
import re
import unicodedata
from decimal import Decimal, localcontext

NUMBER = re.compile(r'(?<![\w.,٫٬])[-+−]?\d+(?:[,.٫٬]\d+)*(?![\d.,٫٬]\d)')
SCALE = re.compile(r'\s*(billion|million|thousand|bn|mn|k|M|مليار|مليون|الف|ألف)(?!\w)',re.I)
FACTORS = {'ONE':1,'THOUSAND':1000,'MILLION':1000000,'BILLION':1000000000}


def parse_number(text):
    converted = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    converted = converted.replace('−','-').replace('٬',',').replace('٫','.')
    if not re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,6})?',converted):
        raise ValueError('Ambiguous numeric separators')
    # A lone period with exactly three trailing digits could be grouping.
    if re.fullmatch(r'[+-]?\d{1,3}\.\d{3}',converted):
        raise ValueError('Ambiguous decimal/grouping notation')
    if len(converted.replace(',','').replace('.','').lstrip('+-'))>24:
        raise ValueError('Number exceeds precision bound')
    return Decimal(converted.replace(',',''))


def number_at(text,match):
    value = parse_number(match.group())
    scale = 'ONE'; end = match.end()
    suffix = SCALE.match(text,end)
    if suffix:
        token = suffix.group(1)
        if token == 'm':
            raise ValueError('Lowercase m is ambiguous')
        scale = ('BILLION' if token.lower() in ('billion','bn','مليار') else
                 'MILLION' if token.lower() in ('million','mn','m','مليون') else 'THOUSAND')
        end = suffix.end()
    elif (end<len(text) and text[end].isalpha()) or re.match(r'\s*(?:trillion|lakh|crore|b|t)(?!\w)',text[end:],re.I):
        raise ValueError('Unsupported or ambiguous numeric suffix')
    with localcontext() as context:
        context.prec = 40
        normalized = value * FACTORS[scale]
    return value,normalized,scale,end
