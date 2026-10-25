import json
from fastapi.testclient import TestClient
from app.main import app,cosine
from app import store,ai


def test_sample_is_explicit_and_cloud_env_does_not_enable_paid_calls(monkeypatch):
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','old-project')
    monkeypatch.setattr(ai,'_openai',lambda *args: (_ for _ in ()).throw(AssertionError('Unexpected paid request')))
    with TestClient(app) as client:
        result=client.post('/api/research',json={'question':'How did revenue change?','ticker':'AAPL'}).json()
        assert result['mode']=='evidence' and result['illustrative']
        assert '[1]' in result['answer']
        assert client.get('/api/health').json()['storage']=='sqlite'


def test_upload_deduplication_and_persistence_across_clients():
    text=b'Unique research: annual revenue increased significantly due to recurring cloud subscriptions.'
    with TestClient(app) as client:
        a=client.post('/api/upload?ticker=AAPL&year=2024&period=FY',files={'file':('report.txt',text)})
        b=client.post('/api/upload?ticker=AAPL&year=2024&period=FY',files={'file':('renamed.txt',text)})
        assert a.status_code==b.status_code==200
        assert not a.json()['duplicate'] and b.json()['duplicate']
        assert len(client.get('/api/library?ticker=AAPL').json())==1
    with TestClient(app) as second:
        docs=second.get('/api/documents?ticker=AAPL').json()
        assert len(docs)==1 and not docs[0]['sample']
        assert second.get('/api/files/'+docs[0]['document_id']).content==text
        result=second.post('/api/research',json={'question':'Explain revenue','ticker':'AAPL'}).json()
        assert 'Unique research' in result['answer']
        assert second.get('/api/history?ticker=AAPL').json()[0]['question']=='Explain revenue'
        assert second.get('/api/documents?ticker=MSFT').json()[0]['sample']


def test_period_filters_never_fall_back_to_other_periods():
    with TestClient(app) as client:
        text=b'Annual revenue grew due to recurring subscriptions and cloud infrastructure adoption.'
        client.post('/api/upload?ticker=AAPL&year=2024&period=FY',files={'file':('report.txt',text)})
        for question in [{'question':'Q1 revenue?','ticker':'AAPL'},{'question':'Revenue growth','ticker':'AAPL','year':2023},{'question':'Revenue growth','ticker':'AAPL','period':'Q2'}]:
            result=client.post('/api/research',json=question).json()
            assert result['sources']==[] and 'not contain enough evidence' in result['answer']


def test_validation_and_missing_files():
    with TestClient(app) as client:
        assert client.post('/api/research',json={'question':'a'}).status_code==422
        assert client.get('/api/documents?ticker=INVALID').status_code==404
        assert client.post('/api/upload',files={'file':('bad.exe',b'bad')}).status_code==400
        assert client.post('/api/upload',files={'file':('empty.txt',b'')}).status_code==400
        assert client.get('/api/files/missing').status_code==404
        assert client.post('/api/research',json={'question':'Revenue?','period':'Q9'}).status_code==422


def test_metric_extraction_requires_explicit_ai_configuration():
    with TestClient(app) as client:
        client.post('/api/upload',files={'file':('report.txt',b'Revenue for fiscal 2024 was USD 100 billion, according to this report.')})
        assert client.get('/api/metrics/extract').status_code==409
        assert client.post('/api/index').status_code==409


def test_metric_quotes_checked_candidates_persisted(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    with TestClient(app) as client:
        content='Annual revenue was USD 100 million in fiscal 2023 and USD 120 million in fiscal 2024.'
        client.post('/api/upload',files={'file':('annual.txt',content.encode())})
        sid=client.get('/api/documents').json()[0]['id']
        observations=[{'metric':'Revenue','fiscal_year':year,'value':value,'unit':'USD millions','source_id':sid,'evidence':content} for year,value in [(2023,100),(2024,120)]]
        observations.append({**observations[0],'evidence':'Invented quote','value':999})
        monkeypatch.setattr(ai,'generate',lambda *args:json.dumps({'observations':observations}))
        result=client.get('/api/metrics/extract')
        assert result.status_code==200
        assert len(result.json()['observations'])==2
        assert result.json()['comparisons'][0]['yoy_percent']==20
        with store.connection() as con:
            rows=con.execute('SELECT status FROM metric_candidates').fetchall()
            assert len(rows)==2 and all(r['status']=='needs_review' for r in rows)


def test_bad_model_citations_return_evidence(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    monkeypatch.setattr(ai,'generate',lambda *args:'An unsupported answer [99]')
    with TestClient(app) as client:
        result=client.post('/api/research',json={'question':'Revenue growth?'}).json()
        assert result['mode']=='evidence' and result['warning']
        assert '[99]' not in result['answer']


def test_cosine():
    assert cosine([1,0],[1,0])==1
    assert cosine([1,0],[0,1])==0
    assert cosine([0,0],[0,0])==0


def test_subject_terms_outrank_report_boilerplate():
    with TestClient(app) as client:
        relevant=b'Services net sales increased due to growth in paid subscriptions and advertising.'
        boilerplate=b'This report and report certification are provided by the company. The report describes revenue.'
        client.post('/api/upload?ticker=AAPL',files={'file':('services.txt',relevant)})
        client.post('/api/upload?ticker=AAPL',files={'file':('boilerplate.txt',boilerplate)})
        result=client.post('/api/research',json={'question':'What does Apple report about Services revenue?'}).json()
        assert result['sources'][0]['text'].startswith('Services net sales')

def test_library_all_companies_has_reviewed_periods_without_private_paths():
    from app import ingest
    first=ingest.ingest(b'Quarterly and annual results include net income and revenue observations.','results.txt','AAPL',fiscal_year=2024,fiscal_period='FY')
    store.add_document_periods(first['id'],['FY','Q4'])
    ingest.ingest(b'Microsoft annual report discusses cloud revenue and operating income growth.','annual.txt','MSFT',fiscal_year=2024,fiscal_period='FY')
    with TestClient(app) as client:
        library=client.get('/api/library').json()
        assert {d['ticker'] for d in library}=={'AAPL','MSFT'}
        assert all('local_path' not in d and 'sha256' not in d for d in library)
        apple=next(d for d in library if d['ticker']=='AAPL')
        assert apple['covered_periods']==['FY','Q4'] and apple['page_count']==1
        assert len(client.get('/api/library?ticker=MSFT').json())==1
        health=client.get('/api/health').json()
        assert health['documents']==2 and health['chunks']==2 and health['pages']==2

def test_excerpts_mode_skips_generation_when_ai_provider_enabled(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','openai')
    monkeypatch.setattr(ai,'generate',lambda *a:(_ for _ in ()).throw(AssertionError('Generation must not run')))
    with TestClient(app) as client:
        response=client.post('/api/research',json={'question':'Revenue growth?','answer_mode':'evidence'})
        assert response.status_code==200
        assert response.json()['mode']=='evidence' and response.json()['sources']
        assert client.post('/api/research',json={'question':'Revenue growth?','answer_mode':'invalid'}).status_code==422
