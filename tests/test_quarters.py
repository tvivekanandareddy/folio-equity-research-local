from fastapi.testclient import TestClient
from app.main import app
from app import store,ingest,ai

def report(year=2024,period='Q4',text=None):
    return ingest.ingest((text or f'Quarterly net income for Q4 {year} was USD 10 million. Annual net income was USD 70 million.').encode(),f'q4-{year}.txt','AAPL',fiscal_year=year,fiscal_period=period)

def test_short_q4_income_resolves_latest_available_year_and_discloses_metric():
    report(2023);report(2024)
    with TestClient(app) as client:
        r=client.post('/api/research',json={'question':'q4 income'}).json()
        assert r['year']==2024 and r['period']=='Q4'
        assert 'latest Q4 available' in r['answer'] and 'GAAP net income' in r['answer']
        assert r['sources'] and all(s['fiscal_year']==2024 for s in r['sources'])

def test_reviewed_mixed_period_reports_are_searchable_without_duplicate_chunks():
    doc=report(period='FY')
    with TestClient(app) as client:
        assert client.get('/api/documents?period=Q4').json()==[]
        store.add_document_periods(doc['id'],['FY','Q4'])
        store.add_document_periods(doc['id'],['FY','Q4'])
        assert len(client.get('/api/documents?period=Q4').json())==1
        assert len(client.get('/api/documents?period=FY').json())==1
        assert len(store.chunks('AAPL'))==1

def test_question_year_is_respected_and_unavailable_period_is_explained():
    report(2024)
    with TestClient(app) as client:
        r=client.post('/api/research',json={'question':'q4 income in 2022'}).json()
        assert r['sources']==[] and r['year']==2022
        assert 'Q4 2022' in r['answer'] and 'Q4 2024' in r['answer']
        assert 'not a substitute' in r['answer']

def test_quarter_and_year_conflicts_ask_for_correction_without_ai(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','openai')
    monkeypatch.setattr(ai,'generate',lambda *a:(_ for _ in ()).throw(AssertionError('No API call expected')))
    with TestClient(app) as client:
        for question,filters in [('q4 income',{'period':'FY'}),('q4 income in 2023',{'year':2024}),('compare Q3 and Q4 income',{})]:
            r=client.post('/api/research',json={'question':question,**filters}).json()
            assert not r['sources'] and r['mode']=='evidence'
            assert 'filter' in r['answer'] or 'one quarter' in r['answer']

def test_fourth_quarter_and_operating_income_preserved_for_model(monkeypatch):
    report()
    monkeypatch.setenv('AI_PROVIDER','openai')
    questions=[]
    def generate(question,docs):
        questions.append(question)
        return 'Operating income is reported in the quarterly column [1].'
    monkeypatch.setattr(ai,'generate',generate)
    with TestClient(app) as client:
        r=client.post('/api/research',json={'question':'fourth quarter operating income 2024'}).json()
        assert r['period']=='Q4' and r['mode']=='openai'
        assert 'GAAP net income' not in questions[0]
        assert 'quarterly column, not full-year totals' in questions[0]

def test_split_quarterly_table_keeps_date_headers_with_net_income_row(monkeypatch):
    content='Three Months Ended September 28, 2024 and September 30, 2023. Twelve Months Ended. In millions.\n'+'Sales and costs data. '*90+'\nNet income: 14,736 22,956 93,736 96,995.'
    report(text=content)
    monkeypatch.setenv('AI_PROVIDER','openai')
    def generate(question,docs):
        row=next(d for d in docs if 'Net income:' in d['text'])
        assert 'Three Months Ended' in row['text']
        assert 'September 28, 2024' in row['text']
        return 'Quarterly net income is USD 14,736 million [1].'
    monkeypatch.setattr(ai,'generate',generate)
    with TestClient(app) as client:
        r=client.post('/api/research',json={'question':'q4 income'}).json()
        assert r['mode']=='openai' and r['sources']
