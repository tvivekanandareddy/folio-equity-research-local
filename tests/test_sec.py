from fastapi.testclient import TestClient
from app.main import app
from app import sec,store


def fact(value, start, end, filed='2025-02-01', form='10-K'):
    return {'val':value,'start':start,'end':end,'filed':filed,'form':form,'fy':2024,'accn':'0000000000-25-000001'}


def test_annual_periods_not_filing_year_and_restatements():
    rows=[fact(100e9,'2023-01-01','2023-12-31'),fact(110e9,'2023-01-01','2023-12-31','2026-02-01'),fact(150e9,'2024-01-01','2024-12-31'),fact(999e9,'2024-10-01','2024-12-31')]
    data={'facts':{'us-gaap':{'Revenues':{'units':{'USD':rows,'EUR':[fact(999e9,'2024-01-01','2024-12-31')]}}}}}
    metrics, periods, docs, comparable=sec.annual_metrics(data,123,'TEST')
    assert metrics['Revenue']==[110,150]
    assert metrics['Net income']==[None,None]
    assert periods==['2023-12-31','2024-12-31']
    assert comparable
    assert len(docs)==2 and docs[0]['url'].startswith('https://www.sec.gov/Archives/')


def test_nonconsecutive_periods_not_comparable():
    data={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[fact(100,'2021-01-01','2021-12-31'),fact(200,'2024-01-01','2024-12-31')]}}}}}
    assert sec.annual_metrics(data,1,'X')[3] is False


def test_search_fallback_and_cik(monkeypatch):
    monkeypatch.setattr(sec,'_directory',None)
    def fetch(url,*args):
        if 'company_tickers' in url: raise sec.SECError('blocked')
        return {'name':'Amazon','tickers':['AMZN']}
    monkeypatch.setattr(sec,'fetch_json',fetch)
    assert sec.search('amazon')['results'][0]['ticker']=='AMZN'
    assert sec.search('amazon')['fallback']
    assert sec.search('1018724')['results'][0]['cik']==1018724
    assert not sec.search('not-a-real-company')['results']


def test_add_persistence_documents_and_duplicate(monkeypatch,tmp_path):
    monkeypatch.setattr(store,'DB',tmp_path/'workspace.sqlite3')
    company={'ticker':'AMZN','name':'Amazon','metrics':{},'origin':'sec','documents':[{'id':'sec-1','text':'Annual revenue USD 100 billion','ticker':'AMZN','sample':False}]}
    monkeypatch.setattr(sec,'import_company',lambda *args:company)
    with TestClient(app) as client:
        assert client.post('/api/companies',json={'cik':1018724,'ticker':'AMZN'}).status_code==200
        assert client.post('/api/companies',json={'cik':1018724,'ticker':'AMZN'}).status_code==200
        assert len([c for c in client.get('/api/companies').json() if c['ticker']=='AMZN'])==1
        assert client.get('/api/documents?ticker=AMZN').json()[0]['id']=='sec-1'
        assert client.post('/api/companies',json={'cik':-1}).status_code==422
    assert sec.saved()[0]['ticker']=='AMZN'


def test_sec_error_does_not_save(monkeypatch,tmp_path):
    monkeypatch.setattr(store,'DB',tmp_path/'workspace.sqlite3')
    def fail(*args): raise sec.SECError('Unavailable')
    monkeypatch.setattr(sec,'import_company',fail)
    with TestClient(app) as client:
        assert client.post('/api/companies',json={'cik':1}).status_code==502
        assert sec.saved()==[]
