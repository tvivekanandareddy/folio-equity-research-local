"""Add verified Apple/NVIDIA Q4 statements and reviewed mixed-period coverage."""
import json
from pathlib import Path
import sys
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import store,ingest,ai

URL='https://www.apple.com/newsroom/pdfs/fy2024-q4/FY24_Q4_Consolidated_Financial_Statements.pdf'

def main():
    path=ROOT/'data/reports/AAPL_Q4_2024.pdf'
    if not path.exists():
        response=httpx.get(URL,timeout=60,follow_redirects=True)
        response.raise_for_status()
        if not response.content.startswith(b'%PDF'):raise ValueError('Expected original Apple PDF')
        path.write_bytes(response.content)
    pages=ingest.read_pages(path.read_bytes(),path.name)
    text='\n'.join(t for _,t in pages)
    if not all(s in text for s in ['Apple Inc.','2024','2023','Net income','Three Months Ended']):
        raise ValueError('Apple quarterly statement identity/period checks failed')
    result=ingest.ingest(path.read_bytes(),path.name,'AAPL',title='Apple Inc. Q4 and FY2024 Consolidated Financial Statements',source_url=URL,fiscal_year=2024,fiscal_period='Q4',origin='investor_relations')
    store.add_document_periods(result['id'],['Q4','FY'])
    # Only these reviewed source documents explicitly include both periods.
    for ticker in ['TSLA','META']:
        for doc in store.document_list(ticker):
            if doc['fiscal_year']==2024 and 'Q4 and FY2024' in doc['title']:
                store.add_document_periods(doc['id'],['Q4','FY'])
    indexed=ai.index_documents(store.chunks('AAPL',2024,'Q4'))
    print(f"Apple Q4 statement ready: {result['pages']} pages, {result['chunks']} excerpts; {indexed} new vectors.",flush=True)
    url='https://investor.nvidia.com/files/doc_financials/2024/Q4FY24/Q4FY24-CFO-Commentary.pdf'
    path=ROOT/'data/reports/NVDA_Q4_2024.pdf'
    if not path.exists():
        response=httpx.get(url,timeout=60,follow_redirects=True);response.raise_for_status()
        if not response.content.startswith(b'%PDF'):raise ValueError('Expected original NVIDIA PDF')
        path.write_bytes(response.content)
    text='\n'.join(t for _,t in ingest.read_pages(path.read_bytes(),path.name))
    if not all(s.lower() in text.lower() for s in ['NVIDIA','2024','Q4','12,285']):raise ValueError('NVIDIA quarterly identity/period check failed')
    result=ingest.ingest(path.read_bytes(),path.name,'NVDA',title='NVIDIA Q4 and FY2024 CFO Commentary and Financial Statements',source_url=url,fiscal_year=2024,fiscal_period='Q4',origin='investor_relations')
    store.add_document_periods(result['id'],['Q4','FY'])
    indexed=ai.index_documents(store.chunks('NVDA',2024,'Q4'))
    print(f"NVIDIA Q4 statement ready: {result['pages']} pages, {result['chunks']} excerpts; {indexed} new vectors.",flush=True)
    for ticker in ['AAPL','NVDA','TSLA','META']:print(ticker,store.reporting_periods(ticker),flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('Quarterly report setup failed:',type(exc).__name__)
        raise SystemExit(1)
