import httpx
import pytest
from app import ai,ingest,store
from app.main import app
from fastapi.testclient import TestClient

def test_cloudflare_missing_credentials_does_not_send_requests(monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID','')
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN','')
    monkeypatch.setattr(httpx,'post',lambda *a,**k:pytest.fail('Unexpected network call'))
    with pytest.raises(ai.AIError,match='privately'):
        ai._cloudflare('@cf/baai/bge-small-en-v1.5',{'text':['test']})

def test_cloudflare_errors_are_sanitized_without_fallback(monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID','a'*32)
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN','private-test-token')
    for status,body in [(429,{}),(403,{}),(200,{'success':False,'errors':['private-test-token']})]:
        monkeypatch.setattr(httpx,'post',lambda *a,**k:httpx.Response(status,json=body,request=httpx.Request('POST','https://example.com')))
        with pytest.raises(ai.AIError) as error:ai._cloudflare('test',{})
        assert 'private-test-token' not in str(error.value)

def test_cloudflare_vectors_reject_bad_dimensions_and_nonfinite_values(monkeypatch):
    monkeypatch.setenv('EMBEDDING_PROVIDER','cloudflare')
    for vectors in [[],[[1.,2.]],[[float('nan')]*384],[[0.]*384]]:
        monkeypatch.setattr(ai,'_cloudflare',lambda *a:{'data':vectors})
        with pytest.raises(ai.AIError):ai.embed(['revenue'])

def test_hosted_rag_write_retrieve_generate_and_cache(monkeypatch):
    monkeypatch.setenv('EMBEDDING_PROVIDER','cloudflare')
    monkeypatch.setenv('AI_PROVIDER','cloudflare')
    ingest.ingest(b'Apple Services revenue grew as paid subscriptions increased during fiscal 2024.','services.txt','AAPL',fiscal_year=2024,fiscal_period='FY')
    calls=[]
    def fake_cloudflare(model,payload):
        calls.append((model,payload))
        if model.endswith('bge-small-en-v1.5'):
            return {'data':[[1.]+[0.]*383 for _ in payload['text']]}
        assert 'Apple Services revenue' in payload['messages'][1]['content']
        return {'response':'Apple Services revenue grew as paid subscriptions increased [1].'}
    monkeypatch.setattr(ai,'_cloudflare',fake_cloudflare)
    with TestClient(app) as client:
        for _ in range(2):
            response=client.post('/api/research',json={'ticker':'AAPL','question':'How did subscriptions affect Services revenue?','year':2024})
            assert response.status_code==200
            result=response.json()
            assert result['mode']=='cloudflare' and result['retrieval']=='hybrid'
            assert result['sources'][0]['ticker']=='AAPL' and '[1]' in result['answer']
        health=client.get('/api/health').json()
        assert health['embeddings']==1 and health['embedding_model']=='@cf/baai/bge-small-en-v1.5'
        assert len(client.get('/api/history').json())==2
    embeddings=[p['text'] for m,p in calls if m.endswith('bge-small-en-v1.5')]
    assert len(embeddings)==3 # one saved passage embedding, two question embeddings
    assert not embeddings[0][0].startswith('Represent this sentence')
    assert all(p[0].startswith('Represent this sentence') for p in embeddings[1:])
    assert len(next(iter(store.embeddings_for([store.chunks('AAPL')[0]['id']],ai.model_id()).values())))==384
