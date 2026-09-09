"""Typed adapters from existing structured analytics, never from rendered HTML.

Transaction dashboards expose the latest recorded year WITHIN their current
filtered frame. Whole-range figures are never mislabeled as one year's values.
Forecast API projections are not accepted as source-reported observations.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from intelligence.answer_engine.models import DashboardFact
from intelligence.query.models import PageContext

@dataclass(frozen=True)
class Snapshot:
    context: PageContext
    facts: tuple[DashboardFact,...]
    selection: str
    caption: str


def context(page,emirate,area=None):
    return PageContext(page_id=page,page_type='AREA' if area else 'OUTLOOK' if page=='forecast' else 'EMIRATE',
        emirate=emirate,area=area,dashboard_section='AI Market Summary')


def fact(identity,location,metric,value,unit,period,source,reference,provenance='SYSTEM_CALCULATED'):
    return DashboardFact(identity=identity,location=location,metric=metric,value=str(value),unit=unit,
        period=period,source=source,reference=reference,provenance=provenance,nature='OBSERVED')


def transactions(df,*,page,emirate,location,year_col,price_col,rate_col,reference,area=None,filters=None):
    ctx=context(page,emirate,area)
    if df is None or df.empty:return Snapshot(ctx,(),str(filters),'No recorded transactions in this selection.')
    year=int(df[year_col].max());selected=df[df[year_col]==year]
    # These are the existing executive KPI definitions over the supplied frame.
    values=(('recorded transactions',len(selected),'transactions'),
        ('recorded sales value',selected[price_col].sum(),'AED'),
        ('median recorded sale rate',selected[rate_col].median(),'AED/m²'))
    source='TruEstate '+location+' transaction analytics'
    facts=tuple(fact(page+'-'+str(i),area or location,metric,value,unit,str(year),source,reference)
        for i,(metric,value,unit) in enumerate(values) if Decimal(str(value)).is_finite())
    # Hash the full filter selection and record identities, not just the displayed
    # values, so different populations with coincidentally equal KPIs invalidate.
    import pandas as pd
    population=hashlib.sha256(pd.util.hash_pandas_object(df,index=True).values.tobytes()).hexdigest()
    selection=json.dumps(dict(filters=filters,area=area,population=population),sort_keys=True,default=str)
    return Snapshot(ctx,facts,selection,f'Analytics facts cover available {year} records within the current selection; they are not a full-year forecast.')


def dubai(df,page='dubai',area=None,filters=None):
    from regions.dubai_market.data import COL
    return transactions(df,page=page,emirate='DUBAI',location='Dubai',year_col=COL['year'],
        price_col=COL['price'],rate_col=COL['rate'],reference='Dubai cleaned residential unit sales dataset; current page selection',area=area,filters=filters)


def abu_dhabi(namespace):
    cols=namespace['COLS']
    return transactions(namespace['df'],page='abu_dhabi',emirate='ABU_DHABI',location='Abu Dhabi',
        year_col='Year',price_col=cols['price'],rate_col=cols['rate'],reference='Abu Dhabi DMT sales records; current page selection')


def report(emirate):
    if emirate=='SHARJAH':
        from regions.sharjah import sources as s
        values=[(p['period'],p['value_aed_billion'],p['status']) for p in s.SHARJAH_TRANSACTION_VALUE_POINTS if p['status'].startswith('published')]
        periods={'Q1 2026':'2026-Q1','FY 2025':'2025','April 2026':'2026-04'}
        facts=tuple(fact('sharjah-'+str(i),'Sharjah','transaction value',value,'AED billion',periods[period],
            s.SAVILLS_Q1_2026['publisher'],s.SAVILLS_Q1_2026['citation'],'SOURCE_REPORTED') for i,(period,value,_) in enumerate(values))
        return Snapshot(context('sharjah','SHARJAH'),facts,'Savills Q1 2026','Published Sharjah report values retain their own periods and source attribution.')
    from regions.rak import sources as s
    rows=s.RAK_ANNUAL_2024_2025_VALUE
    facts=tuple(fact('rak-'+str(i),'Ras Al Khaimah',r['category'],r['y2025_aed'],'AED','2025',
        r['source']['publisher'],r['source']['citation'],'SOURCE_REPORTED') for i,r in enumerate(rows[:3]))
    return Snapshot(context('rak','RAS_AL_KHAIMAH'),facts,'RAK annual 2025','Published RAK report values cover 2025; no other emirate’s values are used.')


def outlook(df=None,area=None):
    if df is not None and not df.empty:return dubai(df,page='forecast',area=area)
    return Snapshot(context('forecast','DUBAI',area),(),'No observed dashboard facts',
        'The summary uses available reported intelligence. Property valuation projections remain in the existing forecast panel.')
