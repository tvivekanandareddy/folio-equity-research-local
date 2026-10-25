"""SEC company discovery and conservative annual USD fact selection."""
from contextlib import contextmanager
import json
import os
import sqlite3
import threading
import time
from datetime import date
from pathlib import Path
import httpx
from app import store

DB = Path(os.getenv('FOLIO_DB', str(Path(__file__).parent.parent / 'data' / 'workspace.sqlite3')))
_gate = threading.Lock()
_cache = {}
_last = 0.0
# Discovery fallback only. Names and tickers are verified against SEC submissions on add.
FALLBACK = [
    ('AAPL','Apple Inc.',320193), ('MSFT','Microsoft Corporation',789019),
    ('NVDA','NVIDIA Corporation',1045810), ('AMZN','Amazon.com, Inc.',1018724),
    ('TSLA','Tesla, Inc.',1318605), ('GOOGL','Alphabet Inc.',1652044),
    ('META','Meta Platforms, Inc.',1326801), ('NFLX','Netflix, Inc.',1065280),
    ('AMD','Advanced Micro Devices, Inc.',2488), ('INTC','Intel Corporation',50863),
    ('JPM','JPMorgan Chase & Co.',19617), ('V','Visa Inc.',1403161),
    ('WMT','Walmart Inc.',104169), ('COST','Costco Wholesale Corporation',909832),
    ('DIS','The Walt Disney Company',1744489), ('KO','The Coca-Cola Company',21344),
    ('CRM','Salesforce, Inc.',1108524), ('ORCL','Oracle Corporation',1341439),
    ('ADBE','Adobe Inc.',796343), ('UBER','Uber Technologies, Inc.',1543151),
]

class SECError(Exception):
    pass

def fetch_json(url, ttl=3600):
    global _last
    # Serialize upstream requests, including retries; <= 4 requests per second.
    with _gate:
        cached = _cache.get(url)
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1]
        time.sleep(max(0, .26 - (time.monotonic() - _last)))
        _last = time.monotonic()
        try:
            response = httpx.get(url, headers={'User-Agent': os.getenv('SEC_USER_AGENT', 'Folio Equity Research application'), 'Accept-Encoding':'gzip, deflate'}, timeout=25)
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SECError('SEC data is unavailable. Try again later; configure SEC_USER_AGENT with your application name and contact email if access is blocked.') from exc
        _cache[url] = (time.monotonic(), result)
        if len(_cache) > 250:
            _cache.pop(next(iter(_cache)))
        return result

_directory = None
_directory_attempt = 0.0

def search(query):
    global _directory, _directory_attempt
    if _directory is None or time.monotonic() - _directory_attempt > 86400:
        _directory_attempt = time.monotonic()
        try:
            raw = fetch_json('https://www.sec.gov/files/company_tickers.json', 86400)
            _directory = [{'ticker':r['ticker'], 'name':r['title'], 'cik':r['cik_str']} for r in raw.values()]
        except SECError:
            _directory = []
    fallback = not bool(_directory)
    records = _directory or [{'ticker':t,'name':n,'cik':c} for t,n,c in FALLBACK]
    q = query.strip().upper()
    if q.isdigit() and 1 <= len(q) <= 10:
        raw = fetch_json(f'https://data.sec.gov/submissions/CIK{int(q):010d}.json')
        return {'results':[{'ticker':(raw.get('tickers') or [q])[0], 'name':raw['name'], 'cik':int(q)}], 'fallback':False}
    found = [r for r in records if q in r['ticker'].upper() or q in r['name'].upper()]
    found.sort(key=lambda r:(r['ticker'].upper()!=q, not r['ticker'].upper().startswith(q), r['ticker']))
    return {'results':found[:30], 'fallback':fallback}

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute('CREATE TABLE IF NOT EXISTS companies (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    try:
        with con:
            yield con
    finally:
        con.close()

def saved():return store.companies()

def save(company):return store.save_company(company)

TAGS = {'Revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'], 'Net income':['NetIncomeLoss'], 'Operating income':['OperatingIncomeLoss']}

def annual_metrics(facts, cik, ticker):
    selected = {}
    gaap = facts.get('facts',{}).get('us-gaap',{})
    for label, tags in TAGS.items():
        rows = []
        for priority, tag in enumerate(tags):
            for r in gaap.get(tag,{}).get('units',{}).get('USD',[]):
                try:
                    days = (date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days
                    if r.get('form') not in ('10-K','10-K/A') or not 330 <= days <= 380:
                        continue
                    rows.append({**r, 'tag':tag, 'priority':priority})
                except (KeyError, ValueError):
                    continue
        # End date is the period identity; fy on a comparative fact is the filing's year.
        for r in sorted(rows, key=lambda r:(r['end'], r.get('filed',''), -r['priority'])):
            selected[(label,r['end'])] = r
    ends = sorted({end for _,end in selected})[-2:]
    metrics, docs = {}, []
    for label in TAGS:
        rows = [selected.get((label,end)) for end in ends]
        metrics[label] = [r['val']/1e9 if r else None for r in rows] if len(ends)==2 else [None, rows[0]['val']/1e9 if rows and rows[0] else None]
        for r in rows:
            if not r: continue
            accession = r.get('accn','')
            url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.html'
            text = f"{ticker} annual {label.lower()} for the period {r['start']} to {r['end']} was USD {r['val']:,.0f}. SEC US-GAAP tag: {r['tag']}. Reported in {r['form']} filed {r.get('filed','unknown')}, accession {accession}. This is structured XBRL financial data, not narrative filing text."
            docs.append({'id':f"{ticker}-{label}-{r['end']}", 'title':f"{ticker} · {label} · year ended {r['end']}", 'text':text, 'ticker':ticker, 'sample':False, 'origin':'sec', 'url':url})
    comparable = len(ends)==2 and 330 <= (date.fromisoformat(ends[1])-date.fromisoformat(ends[0])).days <= 380
    return metrics, ends, docs, comparable

def import_company(cik, requested_ticker=''):
    raw = fetch_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')
    tickers = raw.get('tickers') or []
    if requested_ticker and requested_ticker not in tickers:
        raise SECError('The selected ticker no longer matches this SEC company. Search by CIK to see its current listing.')
    ticker = requested_ticker or (tickers[0] if tickers else f'CIK{cik}')
    warning = None
    try:
        facts = fetch_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json')
        metrics, periods, docs, comparable = annual_metrics(facts, cik, ticker)
    except SECError as exc:
        metrics, periods, docs, comparable = {}, [], [], False
        warning = str(exc)
    if not periods and not warning:
        warning = 'No supported annual US-GAAP USD metrics found. Upload reports to research this company.'
    return {'ticker':ticker,'name':raw['name'],'cik':cik,'sector':raw.get('sicDescription') or 'SEC registrant', 'metrics':metrics,'periods':periods,'comparable':comparable,'documents':docs,'origin':'sec','warning':warning,'retrieved_at':date.today().isoformat()}
