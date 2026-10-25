import io
import pytest
from pypdf import PdfWriter
from app import ingest,store,ai


def test_pdf_page_references(monkeypatch):
    from pypdf import PdfReader
    # Mock extraction for two real blank PDF pages to test page-boundary preservation.
    writer=PdfWriter();writer.add_blank_page(width=500,height=700);writer.add_blank_page(width=500,height=700)
    data=io.BytesIO();writer.write(data)
    from pypdf._page import PageObject
    monkeypatch.setattr(PageObject,'extract_text',lambda self:'Evidence on a document page about revenue and operating results.')
    result=ingest.ingest(data.getvalue(),'test.pdf','AAPL')
    chunks=store.chunks('AAPL')
    assert result['pages']==2
    assert {c['page_number'] for c in chunks}=={1,2}
    assert all('#page=' in c['file_url'] for c in chunks)


def test_failed_parse_does_not_publish_document():
    with pytest.raises(Exception):ingest.ingest(b'bad PDF','bad.pdf','AAPL')
    assert store.document_list('AAPL')==[]


def test_overlapping_chunk_boundaries():
    text=' '.join(f'word{i}' for i in range(500))
    chunks=list(ingest.split_text(text))
    assert len(chunks)>1
    assert set(chunks[0].split()) & set(chunks[1].split())
    assert chunks[-1].endswith('word499')


def test_embeddings_are_cached_and_model_scoped(monkeypatch):
    ingest.ingest(b'Services subscriptions expanded as demand for cloud infrastructure increased.','cloud.txt','AAPL')
    docs=store.chunks('AAPL')
    monkeypatch.setenv('EMBEDDING_PROVIDER','local')
    calls=[]
    def embedding(texts):calls.append(texts);return [[1.,0.] for _ in texts]
    monkeypatch.setattr(ai,'embed',embedding)
    assert ai.index_documents(docs)==1
    assert ai.index_documents(docs)==0
    assert len(calls)==1
    ranked,mode=ai.retrieve('subscription growth',docs)
    assert ranked[0]['id']==docs[0]['id'] and mode=='hybrid'
    assert store.embeddings_for([docs[0]['id']],'different-model')=={}
