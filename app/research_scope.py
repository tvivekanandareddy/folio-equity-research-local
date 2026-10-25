"""Resolve short fiscal-period questions without substituting annual evidence."""
import re
from app import store

def resolve(ticker,question,year=None,period=None):
    quarters={int(n) for n in re.findall(r'\bq\s*([1-4])\b',question,re.I)}
    for number,pattern in [(1,r'first|1st'),(2,r'second|2nd'),(3,r'third|3rd'),(4,r'fourth|4th')]:
        if re.search(r'\b(?:'+pattern+r')[ -]+quarter\b',question,re.I):quarters.add(number)
    years={int(n) for n in re.findall(r'\b(?:19|20)\d{2}\b',question)}
    if len(quarters)>1:
        return year,period,question,[],'Please ask about one quarter at a time, or select a report period.'
    inferred='Q'+str(next(iter(quarters))) if quarters else None
    if inferred and period and inferred!=period:
        return year,period,question,[],f'Your question asks for {inferred}, but the report filter is {period}. Change the filter to {inferred} or All periods.'
    if year is not None and years and year not in years:
        return year,period,question,[],f'The question year conflicts with the report-year filter ({year}). Change the filter or the question.'
    period=period or inferred
    if year is None and len(years)==1:year=next(iter(years))
    assumptions=[]
    available=store.reporting_periods(ticker)
    # Choose the latest *available* fiscal quarter, never a live/current year guess.
    if period and period!='FY' and year is None and not years:
        matches=[p['fiscal_year'] for p in available if p['fiscal_period']==period and p['fiscal_year'] is not None]
        if matches:
            year=max(matches)
            assumptions.append(f'Using fiscal {period} {year}, the latest {period} available in this library.')
    if re.search(r'\b(income|earnings)\b',question,re.I) and not re.search(r'\b(net|operating|comprehensive|pretax|pre.tax|per share|eps)\b',question,re.I):
        question+=' (Interpret income/earnings as GAAP net income, not revenue.)'
        assumptions.append('Interpreting “income” as GAAP net income. Ask for operating income or revenue if that is what you mean.')
    if period and period!='FY':
        question+=f' Answer only for fiscal {period}'+(f' {year}' if year else '')+'. Use the quarterly column, not full-year totals. Do not estimate a missing quarterly value.'
    return year,period,question,assumptions,None

def missing_message(ticker,year,period):
    available=store.reporting_periods(ticker)
    labels=[f"{p['fiscal_period']} {p['fiscal_year'] if p['fiscal_year'] is not None else '(year unspecified)'}" for p in available]
    requested=' '.join(str(v) for v in (period,year) if v is not None) or 'the requested scope'
    return (f'The available documents do not contain enough evidence for {ticker} {requested}. '
            +('Available report coverage: '+', '.join(labels)+'. ' if labels else 'No reports with labeled fiscal periods are available. ')
            +'Add the corresponding quarterly earnings release or financial statements, or change the report filters. Full-year income is not a substitute for quarterly income.')
