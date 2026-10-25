"""Page-preserving ingestion with deterministic IDs and transactional deduplication."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import io
import re
from pypdf import PdfReader
from app import store
ROOT=Path(__file__).resolve().parents[1]

def split_text(text,size=1100,overlap=150):
    text=text.replace('\x00','').strip()
    start=0
    while start<len(text):
        end=min(start+size,len(text))
        if end<len(text):
            boundary=text.rfind(' ',start+size//2,end)
            if boundary>start:end=boundary
        piece=text[start:end].strip()
        if len(piece)>=30:yield piece
        if end==len(text):break
        start=max(start+1,end-overlap)

def read_pages(data,filename):
    if len(data)>40*1024*1024:raise ValueError('Maximum file size is 40 MB.')
    if filename.lower().endswith('.pdf'):
        reader=PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(''):raise ValueError('Password-protected PDFs must be unlocked first.')
        if len(reader.pages)>500:raise ValueError('Maximum report length is 500 pages.')
        pages=[(i+1,(p.extract_text() or '').replace('\x00','')) for i,p in enumerate(reader.pages)]
    elif filename.lower().endswith('.txt'):
        pages=[(1,data.decode('utf-8').replace('\x00',''))]
    else:raise ValueError('Choose a text-based PDF or UTF-8 TXT file.')
    if sum(len(t.strip()) for _,t in pages)<40:raise ValueError('No usable text found. Scanned reports need OCR; chart interpretation is not enabled.')
    if sum(len(t) for _,t in pages)>3000000:raise ValueError('Maximum extracted text length is 3 million characters.')
    return pages

def ingest(data,filename,ticker,title=None,source_url='',fiscal_year=None,fiscal_period=None,origin='upload'):
    digest=hashlib.sha256(data).hexdigest()
    doc_id=hashlib.sha256((ticker+digest).encode()).hexdigest()[:32]
    # Parse before a database transaction; duplicate reads are safe and idempotent.
    pages=read_pages(data,filename)
    filename=Path(filename).name
    ext='.pdf' if filename.lower().endswith('.pdf') else '.txt'
    path=ROOT/'data'/'documents'/(doc_id+ext);path.parent.mkdir(parents=True,exist_ok=True)
    chunks=[]
    for page,text in pages:
        for i,piece in enumerate(split_text(text)):
            chunks.append((f'{doc_id}-{page}-{i}',doc_id,ticker,page,piece,f'{title or filename} · PDF page {page}' if ext=='.pdf' else f'{title or filename} · text excerpt {i+1}'))
    if not chunks:raise ValueError('No searchable passages found.')
    # Files use content-derived names. Store originals atomically; DB commit publishes metadata.
    if not path.exists():
        temporary=path.with_suffix('.partial');temporary.write_bytes(data);temporary.replace(path)
    with store.connection() as c:
        existing=c.execute('SELECT id FROM documents WHERE id=?',(doc_id,)).fetchone()
        if existing:
            return {'id':doc_id,'name':filename,'chunks':len(chunks),'pages':len(pages),'duplicate':True}
        c.execute('INSERT INTO documents(id,ticker,title,filename,sha256,source_url,fiscal_year,fiscal_period,origin,local_path,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(doc_id,ticker,title or filename,filename,digest,source_url,fiscal_year,fiscal_period,origin,str(path.relative_to(ROOT)),datetime.now(timezone.utc).isoformat()))
        c.executemany('INSERT INTO pages(id,document_id,page_number,text) VALUES (?,?,?,?)',[(f'{doc_id}-{page}',doc_id,page,text) for page,text in pages])
        c.executemany('INSERT INTO chunks(id,document_id,ticker,page_number,text,title) VALUES (?,?,?,?,?,?)',chunks)
        if not c.pg:c.executemany('INSERT INTO chunks_fts(id,text) VALUES (?,?)',[(r[0],r[4]) for r in chunks])
    return {'id':doc_id,'name':filename,'chunks':len(chunks),'pages':len(pages),'duplicate':False}
