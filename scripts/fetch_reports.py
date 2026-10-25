"""Download reproducible historical 2024 annual report corpus; no API keys needed."""
import hashlib
import json
import sys
import time
from pathlib import Path
import httpx
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
CATALOG=[('AAPL','Apple Inc.',320193,'2024-09-28'),('MSFT','Microsoft Corporation',789019,'2024-06-30'),('NVDA','NVIDIA Corporation',1045810,'2024-01-28'),('AMZN','Amazon.com, Inc.',1018724,'2024-12-31'),('TSLA','Tesla, Inc.',1318605,'2024-12-31'),('GOOGL','Alphabet Inc.',1652044,'2024-12-31'),('META','Meta Platforms, Inc.',1326801,'2024-12-31'),('NFLX','Netflix, Inc.',1065280,'2024-12-31')]

SOURCES={
'AAPL':('https://s2.q4cdn.com/470004039/files/doc_financials/2024/q4/c87043b9-5d89-4717-9f49-c4f9663d0061.pdf','FY2024 Annual Report'),
'MSFT':('https://www.microsoft.com/investor/reports/ar24/index.html','FY2024 Annual Report (HTML text)'),
'NVDA':('https://s201.q4cdn.com/141608511/files/doc_financials/2024/ar/NVIDIA-2024-Annual-Report.pdf','FY2024 Annual Report'),
'AMZN':('https://s2.q4cdn.com/299287126/files/doc_financials/2025/ar/Amazon-2024-Annual-Report.pdf','FY2024 Annual Report'),
'TSLA':('https://digitalassets.tesla.com/tesla-contents/image/upload/IR/TSLA-Q4-2024-Update.pdf','Q4 and FY2024 Financial Update'),
'GOOGL':('https://s206.q4cdn.com/479360582/files/doc_financials/2025/q4/2024-annual-report.pdf','FY2024 Annual Report'),
'META':('https://investor.atmeta.com/files/doc_financials/2024/q4/Meta-12-31-2024-Exhibit-99-1-FINAL.pdf','Q4 and FY2024 Earnings Release'),
'NFLX':('https://s22.q4cdn.com/959853165/files/doc_financials/2024/ar/Netflix-10-K-01272025.pdf','FY2024 Annual Report')}

def main():
    from bs4 import BeautifulSoup
    destination=ROOT/'data'/'reports';destination.mkdir(parents=True,exist_ok=True)
    manifest=[]
    with httpx.Client(timeout=90,follow_redirects=True,headers={'User-Agent':'Folio Equity Research personal educational project'}) as client:
        for ticker,name,cik,period in CATALOG:
            url,label=SOURCES[ticker]
            extension='.txt' if ticker=='MSFT' else '.pdf'
            path=destination/f'{ticker}_2024{extension}'
            try:
                if not path.exists():
                    r=client.get(url);r.raise_for_status()
                    if len(r.content)>40*1024*1024:raise ValueError('File too large')
                    if extension=='.pdf':
                        if not r.content.startswith(b'%PDF'):raise ValueError('Not a PDF')
                        content=r.content
                    else:
                        soup=BeautifulSoup(r.text,'html.parser')
                        for node in soup(['script','style','nav','header','footer']):node.decompose()
                        content=soup.get_text(' ',strip=True).encode()
                        (destination/f'{ticker}_2024.html').write_bytes(r.content)
                    temp=path.with_suffix('.partial');temp.write_bytes(content);temp.replace(path)
                if extension=='.pdf':
                    reader=PdfReader(path);sample=' '.join((p.extract_text() or '') for p in reader.pages[:12]).lower();pages=len(reader.pages)
                else:sample=path.read_text().lower();pages=1
                expected={'AAPL':'apple','MSFT':'microsoft','NVDA':'nvidia','AMZN':'amazon','TSLA':'tesla','GOOGL':'alphabet','META':'meta','NFLX':'netflix'}[ticker]
                if expected not in sample or '2024' not in sample:raise ValueError('Identity/year check failed')
                item={'ticker':ticker,'name':name,'cik':cik,'fiscal_year':2024,'fiscal_period':'FY','period_end':period,'title':f'{name} {label}','url':url,'publisher':'Company investor relations','path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':pages,'status':'downloaded'}
                manifest.append(item);print(f'{ticker}: verified {pages} pages/sections',flush=True)
            except Exception as exc:
                manifest.append({'ticker':ticker,'status':'failed','error':type(exc).__name__});print(f'{ticker}: failed {type(exc).__name__}',flush=True)
            time.sleep(.4)
    (ROOT/'data'/'report_manifest.json').write_text(json.dumps(manifest,indent=2))
    return 0 if sum(i['status']=='downloaded' for i in manifest)>=8 else 1
if __name__=='__main__':raise SystemExit(main())
