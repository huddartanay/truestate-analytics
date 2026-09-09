"""Explicit contexts and dimensional vocabulary. Precision favored over recall."""
import re


def rx(pattern):
    return re.compile(pattern,re.I)

CURRENCY = rx(r'(?<!\w)(AED|Dhs?|USD|EUR|GBP|درهم|دراهم)(?!\w)')
PRICE = rx(r'\b(?:prices?|sale values?|home values?)\b|(?:اسعار|أسعار|سعر)')
RENT = rx(r'\b(?:rents?|rental(?: prices?| rates?)?)\b|(?:الايجارات|الإيجارات|ايجار|إيجار)')
YIELD = rx(r'\b(?:rental yields?|rent yields?)\b|العائد الايجاري')
TRANSACTION = rx(r'\b(?:property )?transactions?\b|التصرفات العقارية|المعاملات العقارية|معاملة عقارية')
BLOCK = rx(r'\b(?:revenue|profit|earnings|costs?|budget|mortgage|GDP|interest|salary|salaries|stock|shares?|oil|crude|hotel room|car rental|vehicle rental|exchange rate)\b|الرهن|ارباح|تكلفة')
RANGE = rx(r'\b(?:rang(?:e|es|ed|ing)|between|starting|starts? from|from.+\bto)\b|\d\s*[-–—]\s*\d')
AREA = rx(r'\s*(?:/|per\s+)?\s*(sq\s*ft|sqft|psf|square feet|square foot|ft²|sq\s*m|sqm|square metr[es]+|square meters?|m²)(?!\w)')
ANNUAL = rx(r'\bannual(?:ly)?\b|(?:/|per\s+)\s*year\b|سنويا')
MONTHLY = rx(r'\bmonthly\b|(?:/|per\s+)\s*month\b|شهريا')
PERIOD = rx(r'\b(?:Q[1-4]\s+20\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}|(?:first|second) half(?: of)?\s+20\d{2}|(?:next|last|this|previous) (?:year|month|quarter)|(?:in|during|for)\s+20\d{2})\b|العام الماضي')
BASES = [('YOY',rx(r'\b(?:yoy|year[- ]on[- ]year|year over year)\b')),
         ('MOM',rx(r'\b(?:mom|month[- ]on[- ]month|month over month)\b')),
         ('QOQ',rx(r'\b(?:qoq|quarter[- ]on[- ]quarter|quarter over quarter)\b')),
         ('CURRENT',rx(r'\b(?:currently|current|now)\b')),
         ('QUARTERLY',rx(r'\bquarterly\b'))]
PROPERTIES = [('COMMERCIAL_PROPERTY',rx(r'\bcommercial propert(?:y|ies)\b')),
    ('APARTMENT',rx(r'\bapartments?\b|الشقق|شقة')),('VILLA',rx(r'\bvillas?\b|فلل|فيلا')),
    ('TOWNHOUSE',rx(r'\btownhouses?\b')),('LAND',rx(r'\bland\b')),
    ('OFFICE',rx(r'\boffices?\b')),('RETAIL',rx(r'\bretail\b')),('WAREHOUSE',rx(r'\bwarehouses?\b')),
    ('RESIDENTIAL',rx(r'\bresidential\b')),('COMMERCIAL',rx(r'\bcommercial\b'))]
QUALIFIERS = [('APPROXIMATE',rx(r'\b(?:about|approximately|around|nearly)\b')),
              ('GREATER_THAN',rx(r'\b(?:more than|over)\b')),
              ('LESS_THAN',rx(r'\b(?:less than|under)\b'))]
