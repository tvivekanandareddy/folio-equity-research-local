"""Folio personal research workspace: private database access stays on the server."""
import io
import json
import math
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import sec, store, ingest, ai, research_scope
from app.sample import COMPANIES
app=FastAPI(title='Folio Equity Research',version='0.2.0')
STATIC=Path(__file__).parent/'static'
app.mount('/static',StaticFiles(directory=STATIC),name='static')

@app.get('/')
def home():return FileResponse(STATIC/'index.html')

@app.get('/api/health')
def health():
    try:
        with store.connection() as c:
            totals=c.execute('SELECT (SELECT count(*) FROM documents) AS documents, (SELECT count(*) FROM embeddings) AS embeddings, (SELECT count(*) FROM chunks) AS chunks, (SELECT count(*) FROM pages) AS pages').fetchone()
        return {'status':'ok','mode':ai.provider(),'storage':'supabase' if os.getenv('DATABASE_URL') else 'sqlite','embedding_provider':ai.embedding_provider(),'embedding_model':ai.model_id() if ai.embedding_provider()!='none' else None,'embedding_dimensions':1536 if ai.embedding_provider()=='openai' and ai.model_id()=='text-embedding-3-small' else 3072 if ai.embedding_provider()=='openai' and ai.model_id()=='text-embedding-3-large' else 384 if ai.embedding_provider() in ('local','cloudflare') else None,**dict(totals),'model':'@cf/meta/llama-3.2-3b-instruct' if ai.provider()=='cloudflare' else os.getenv('OLLAMA_MODEL','qwen3:4b') if ai.provider()=='ollama' else os.getenv('OPENAI_CHAT_MODEL','gpt-5-mini') if ai.provider()=='openai' else None}
    except Exception:raise HTTPException(503,'Database unavailable. Check .env and run scripts/setup_database.py. Credentials are never returned to the browser.')

@app.get('/api/companies')
def companies():
    merged={c['ticker']:{**c,'origin':'sample'} for c in COMPANIES}
    merged.update({c['ticker']:c for c in store.companies()})
    return [{k:v for k,v in c.items() if k not in ('notes','documents')} for c in merged.values()]

@app.get('/api/companies/search')
def search_companies(q:str=''):
    if not 1<=len(q.strip())<=100:raise HTTPException(400,'Enter a company name, ticker, or numeric SEC CIK.')
    try:return sec.search(q)
    except sec.SECError as exc:raise HTTPException(502,str(exc))

class AddCompany(BaseModel):
    cik:int=Field(ge=1,le=9999999999)
    ticker:str=Field(default='',max_length=20,pattern=r'^[A-Z0-9.\-]*$')

@app.post('/api/companies')
def add_company(body:AddCompany):
    try:
        company=sec.import_company(body.cik,body.ticker);store.save_company(company)
        return {k:v for k,v in company.items() if k!='documents'}
    except sec.SECError as exc:raise HTTPException(502,str(exc))

def get_company(ticker):
    c=next((c for c in store.companies()+COMPANIES if c['ticker']==ticker),None)
    if c is None:raise HTTPException(404,'Unknown company')
    return c

def documents(ticker,year=None,period=None):
    company=get_company(ticker)
    persisted=store.chunks(ticker,year,period)
    # Explicit filters must never silently fall back to other periods or fixtures.
    if persisted or year is not None or period:return persisted
    if store.document_list(ticker):return []
    if company.get('origin')=='sec':return company.get('documents',[])
    return [{'id':f'{ticker}-{i}','title':f'{ticker} FY2024 · illustrative summary','text':t,'sample':True,'ticker':ticker,'origin':'sample'} for i,t in enumerate(company.get('notes',[]))]

@app.get('/api/documents')
def document_chunks(ticker:str='AAPL',year:int|None=None,period:str|None=None):return documents(ticker,year,period)

@app.get('/api/library')
def library(ticker:str|None=None):
    if ticker:get_company(ticker)
    return [{k:v for k,v in r.items() if k not in ('local_path','sha256')} for r in store.document_list(ticker)]

@app.get('/api/files/{document_id}')
def original_file(document_id:str):
    with store.connection() as c:r=c.execute('SELECT local_path,filename,source_url FROM documents WHERE id=?',(document_id,)).fetchone()
    if not r:raise HTTPException(404,'Document not found')
    path=(ingest.ROOT/r['local_path']).resolve()
    if not path.is_relative_to((ingest.ROOT/'data').resolve()) or not path.is_file():
        raise HTTPException(404,'Original file is not on this computer. Use the original publisher link.')
    return FileResponse(path,filename=r['filename'],content_disposition_type='inline')

class Question(BaseModel):
    question:str=Field(min_length=3,max_length=2000)
    ticker:str='AAPL'
    year:int|None=Field(default=None,ge=1990,le=2100)
    period:str|None=Field(default=None,pattern=r'^(FY|Q1|Q2|Q3|Q4)$')
    answer_mode:str=Field(default='ai',pattern=r'^(ai|evidence)$')

def cosine(a,b):return sum(x*y for x,y in zip(a,b))/max(math.sqrt(sum(x*x for x in a)*sum(y*y for y in b)),1e-12)

@app.post('/api/research')
def research(body:Question):
    get_company(body.ticker)
    year,period,question,assumptions,clarification=research_scope.resolve(body.ticker,body.question,body.year,body.period)
    docs=[] if clarification else documents(body.ticker,year,period)
    try:
        retrieval_question=body.question+(' net income' if any(a.startswith('Interpreting') for a in assumptions) else '')
        if period:retrieval_question+=' fiscal '+period
        if year:retrieval_question+=' '+str(year)
        ranked,retrieval=ai.retrieve(retrieval_question,docs)
        # Keep quarter/year column headers next to table rows split into later chunks.
        ranked=[{**d,'text':'[Page header]\n'+d['page_header']+'\n\n[Retrieved excerpt]\n'+d['text']} if d.get('page_header') and not d['text'].startswith(d['page_header']) else d for d in ranked]
        mode='evidence';warning=None
        if not ranked:answer=clarification or research_scope.missing_message(body.ticker,year,period)
        elif ai.provider()=='evidence' or body.answer_mode=='evidence':answer='\n\n'.join(f'{d["text"]} [{i+1}]' for i,d in enumerate(ranked))
        else:
            answer=ai.generate(question,ranked);mode=ai.provider()
            citations=[int(n) for n in re.findall(r'\[(\d+)\]',answer)]
            if not citations or any(n<1 or n>len(ranked) for n in citations):
                warning='The model returned missing or invalid source references. Showing retrieved evidence instead.'
                answer='\n\n'.join(f'{d["text"]} [{i+1}]' for i,d in enumerate(ranked));mode='evidence'
    except ai.AIError as exc:raise HTTPException(502,str(exc))
    if ranked and assumptions:answer='\n\n'.join(assumptions)+'\n\n'+answer
    result={'answer':answer,'sources':ranked,'mode':mode,'retrieval':retrieval,'illustrative':any(d.get('sample') for d in ranked),'warning':warning,'question':body.question,'ticker':body.ticker,'year':year,'period':period,'assumptions':assumptions,'created_at':datetime.now(timezone.utc).isoformat()}
    with store.connection() as c:c.execute('INSERT INTO research(id,ticker,question,answer,payload,created_at) VALUES (?,?,?,?,?,?)',(secrets.token_hex(16),body.ticker,body.question,answer,json.dumps(result),result['created_at']))
    return result

@app.get('/api/history')
def history(ticker:str='AAPL'):
    get_company(ticker);return store.history(ticker)

@app.post('/api/upload')
def upload(ticker:str='AAPL',year:int|None=None,period:str|None=None,file:UploadFile=File(...)):
    get_company(ticker)
    if year is not None and not 1990<=year<=2100:raise HTTPException(400,'Invalid fiscal year')
    if period and period not in ('FY','Q1','Q2','Q3','Q4'):raise HTTPException(400,'Invalid fiscal period')
    data=file.file.read(40*1024*1024+1)
    try:result=ingest.ingest(data,file.filename or 'report.txt',ticker,fiscal_year=year,fiscal_period=period)
    except ValueError as exc:raise HTTPException(400,str(exc))
    except Exception:raise HTTPException(400,'Could not read this report. Use a text-based PDF or UTF-8 TXT file.')
    return result

@app.post('/api/index')
def index_documents(ticker:str='AAPL'):
    get_company(ticker)
    if ai.embedding_provider()=='none':raise HTTPException(409,'Embeddings are disabled. Choose a provider explicitly before indexing.')
    try:return {'indexed':ai.index_documents(store.chunks(ticker)),'provider':ai.embedding_provider()}
    except ai.AIError as exc:raise HTTPException(409,str(exc))

class MetricObservation(BaseModel):
    metric:str
    fiscal_year:int
    value:float
    unit:str
    source_id:str
    evidence:str
class MetricExtraction(BaseModel):observations:list[MetricObservation]

@app.get('/api/metrics/extract')
def extract_metrics(ticker:str='AAPL'):
    docs=store.chunks(ticker);get_company(ticker)
    if not docs:raise HTTPException(409,'Upload a financial report before extracting metrics.')
    if ai.provider()=='evidence':raise HTTPException(409,'AI metric extraction needs Cloudflare, OpenAI or Ollama. Research and source viewing work in evidence-only mode.')
    try:
        context=sorted(docs,key=lambda d:sum(d['text'].lower().count(k) for k in ['net income','operating income','revenue','net sales','millions']),reverse=True)[:16]
        output=ai.generate('Extract annual financial metrics and their exact supporting quotes.',context,MetricExtraction.model_json_schema())
        extracted=MetricExtraction.model_validate_json(output);source_map={d['id']:d for d in context}
        valid=[]
        for o in extracted.observations:
            if o.source_id not in source_map or not o.evidence.strip() or o.evidence not in source_map[o.source_id]['text'] or not math.isfinite(o.value):continue
            # These are review candidates, never silently accepted accounting records.
            valid.append(o.model_dump())
        with store.connection() as c:
            for o in valid:c.execute('INSERT INTO metric_candidates(id,ticker,source_id,payload,status,created_at) VALUES (?,?,?,?,?,?)',(secrets.token_hex(16),ticker,o['source_id'],json.dumps(o),'needs_review',datetime.now(timezone.utc).isoformat()))
        groups={}
        for o in valid:groups.setdefault((o['metric'],o['unit'],o['fiscal_year']),set()).add(o['value'])
        comparisons=[]
        for (metric,unit,year),values in groups.items():
            previous=groups.get((metric,unit,year-1),set())
            if len(values)==len(previous)==1 and next(iter(previous))!=0:
                current,prior=next(iter(values)),next(iter(previous))
                comparisons.append({'metric':metric,'unit':unit,'year':year,'current':current,'previous':prior,'yoy_percent':(current-prior)/abs(prior)*100})
        return {'observations':valid,'comparisons':comparisons,'note':'AI-extracted candidates saved for review. Exact quote presence is checked; values, units, and fiscal periods still require human verification. These do not overwrite the dashboard.'}
    except ai.AIError as exc:raise HTTPException(502,str(exc))
    except Exception:raise HTTPException(502,'Metric extraction returned an invalid response. Please retry.')
