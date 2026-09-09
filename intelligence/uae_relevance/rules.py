"""Finite stage9-v1 relevance lexicon. Labels are evidence, not entities."""
GEO = {
    'uae': ('uae', 'united arab emirates', 'الإمارات العربية المتحدة', 'الإمارات'),
    'dubai': ('dubai', 'دبي'),
    'abu_dhabi': ('abu dhabi', 'abudhabi', 'أبوظبي', 'أبو ظبي'),
    'sharjah': ('sharjah', 'الشارقة'),
    'ajman': ('ajman', 'عجمان'),
    'ras_al_khaimah': ('ras al khaimah', 'ras al-khaimah', 'رأس الخيمة'),
    'fujairah': ('fujairah', 'الفجيرة'),
    'umm_al_quwain': ('umm al quwain', 'umm al-quwain', 'أم القيوين'),
}
INCIDENTAL = {
    'incidental_office_location': ('office in', 'offices in', 'office location', 'headquarters', 'headquartered', 'based in'),
    'incidental_commentator': ('analyst', 'analysts', 'commented', 'author', 'byline', 'reporting from'),
    'incidental_corporate_background': ('biography', 'founded in', 'stock exchange listing', 'listed on', 'corporate profile'),
    'incidental_venue_route': ('conference', 'summit', 'airline route', 'flight to', 'flights to'),
    'incidental_footer': ('contact us', 'all rights reserved', 'subscribe', 'navigation', 'follow us', 'footer'),
    'uae_list_only': ('briefly lists', 'briefly mentions', 'markets include', 'markets including', 'among 20 markets', 'outlook covers', 'comparison footnote'),
    'ambiguous_emirates_brand': ('emirates airline', 'emirates airlines', 'emirates nbd', 'emirates group', 'طيران الإمارات'),
}
FOREIGN = ('london', 'new york', 'singapore', 'australia', 'australian', 'uk', 'united kingdom',
           'us', 'united states', 'europe', 'european', 'paris', 'sydney', 'لندن', 'سنغافورة')
PROPERTY_EXTRA = ('villa prices', 'luxury property', 'residential sales', 'residential transactions',
                  'residential demand', 'tenancy rules', 'rents increase', 'housing', 'العقارات',
                  'الايجارات', 'سكني')
PROXIMITY_TOKENS = 8
BODY_DIRECT_MIN_SHARE = 0.15
BODY_MATERIAL_MIN_SHARE = 0.25
MAX_EVIDENCE = 24
