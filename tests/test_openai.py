import httpx
import pytest
from app import ai

def test_openai_embeddings_reordered_and_validated(monkeypatch):
    monkeypatch.setenv('EMBEDDING_PROVIDER','openai')
    monkeypatch.setattr(ai,'_openai',lambda *a:{'data':[{'index':1,'embedding':[0.,1.]},{'index':0,'embedding':[1.,0.]}]})
    assert ai.embed(['first','second'])==[[1.,0.],[0.,1.]]
    monkeypatch.setattr(ai,'_openai',lambda *a:{'data':[{'index':0,'embedding':[1.,0.]},{'index':0,'embedding':[0.,1.]}]})
    with pytest.raises(ai.AIError):ai.embed(['first','second'])

def test_transient_limit_retried_but_quota_failure_stops(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-secret')
    sleeps=[];monkeypatch.setattr(ai.time,'sleep',sleeps.append)
    statuses=iter([429,200])
    def post(*a,**k):
        status=next(statuses)
        return httpx.Response(status,json={'data':[]},request=httpx.Request('POST','https://example.com'))
    monkeypatch.setattr(httpx,'post',post)
    assert ai._openai('embeddings',{})=={'data':[]}
    assert sleeps==[2]
    monkeypatch.setattr(httpx,'post',lambda *a,**k:httpx.Response(429,json={'error':{'code':'insufficient_quota','message':'test-secret'}},request=httpx.Request('POST','https://example.com')))
    with pytest.raises(ai.AIError,match='insufficient') as error:ai._openai('embeddings',{})
    assert sleeps==[2] and 'test-secret' not in str(error.value)

def test_answer_request_disables_storage_and_includes_only_selected_sources(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','openai')
    monkeypatch.setenv('OPENAI_CHAT_MODEL','gpt-5-mini')
    calls=[]
    def fake(path,payload):
        calls.append(payload)
        return {'output':[{'content':[{'type':'output_text','text':'Revenue increased [1].'}]}]}
    monkeypatch.setattr(ai,'_openai',fake)
    result=ai.generate('Revenue change?',[{'id':'source-1','title':'Annual report','text':'Revenue increased.'}])
    assert '[1]' in result
    assert calls[0]['store'] is False and calls[0]['max_output_tokens']==2500
    assert '[1] Source ID: source-1' in calls[0]['input'][1]['content']
