"""Shared repository: PostgreSQL/Supabase when configured, SQLite for offline development."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3
import threading
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')
DB=Path(os.getenv('FOLIO_DB',str(Path(__file__).resolve().parents[1]/'data'/'workspace.sqlite3')))
_init_lock=threading.Lock()
_initialized=set()

BASE_SQL='''
CREATE TABLE IF NOT EXISTS companies (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, ticker TEXT NOT NULL, title TEXT NOT NULL, filename TEXT NOT NULL,
 sha256 TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '', fiscal_year INTEGER,
 fiscal_period TEXT, origin TEXT NOT NULL, local_path TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(ticker,sha256)
);
CREATE TABLE IF NOT EXISTS pages (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 page_number INTEGER NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_periods (
 document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 fiscal_period TEXT NOT NULL CHECK (fiscal_period IN ('FY','Q1','Q2','Q3','Q4')),
 PRIMARY KEY(document_id,fiscal_period)
);
CREATE TABLE IF NOT EXISTS chunks (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 ticker TEXT NOT NULL, page_number INTEGER NOT NULL, text TEXT NOT NULL, title TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_ticker_idx ON chunks(ticker);
CREATE TABLE IF NOT EXISTS research (
 id TEXT PRIMARY KEY, ticker TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL,
 payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metric_candidates (
 id TEXT PRIMARY KEY, ticker TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES chunks(id),
 payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'needs_review', created_at TEXT NOT NULL
);
'''

class Connection:
    def __init__(self,raw,pg):self.raw,self.pg=raw,pg
    def execute(self,sql,args=()):return self.raw.execute(sql.replace('?','%s') if self.pg else sql,args)
    def executemany(self,sql,rows):
        cur=self.raw.cursor();cur.executemany(sql.replace('?','%s') if self.pg else sql,rows);return cur

@contextmanager
def connection():
    url=os.getenv('DATABASE_URL','').strip()
    if url:
        import psycopg
        from psycopg.rows import dict_row
        raw=psycopg.connect(url,connect_timeout=12,sslmode='require',row_factory=dict_row)
        raw.execute('SET search_path TO folio, extensions, public')
        key=url;pg=True
    else:
        DB.parent.mkdir(parents=True,exist_ok=True)
        raw=sqlite3.connect(DB,timeout=30);raw.row_factory=sqlite3.Row
        raw.execute('PRAGMA foreign_keys=ON');key=str(DB);pg=False
    try:
        with _init_lock:
            if key not in _initialized:
                if pg:
                    # Run explicit migration before use; do not silently fall back if configuration fails.
                    raw.execute('SELECT id FROM folio.documents LIMIT 0')
                else:
                    raw.executescript(BASE_SQL)
                    raw.execute('CREATE TABLE IF NOT EXISTS embeddings (chunk_id TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE, model TEXT NOT NULL, embedding TEXT NOT NULL)')
                    raw.execute('CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED, text)')
                raw.commit();_initialized.add(key)
        yield Connection(raw,pg)
        raw.commit()
    except Exception:
        raw.rollback();raise
    finally:raw.close()

def companies():
    with connection() as c:return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM companies ORDER BY ticker').fetchall()]

def save_company(company):
    with connection() as c:c.execute('INSERT INTO companies(ticker,payload) VALUES (?,?) ON CONFLICT(ticker) DO UPDATE SET payload=excluded.payload',(company['ticker'],json.dumps(company)))

def document_list(ticker=None):
    with connection() as c:
        where=' WHERE ticker=?' if ticker else ''
        rows=c.execute('SELECT d.*, (SELECT count(*) FROM chunks c WHERE c.document_id=d.id) AS chunk_count, (SELECT count(*) FROM pages p WHERE p.document_id=d.id) AS page_count FROM documents d'+where+' ORDER BY created_at DESC',(ticker,) if ticker else ()).fetchall()
        periods={}
        for p in c.execute('SELECT document_id,fiscal_period FROM document_periods').fetchall():periods.setdefault(p['document_id'],[]).append(p['fiscal_period'])
        return [{**dict(r),'covered_periods':sorted(set(periods.get(r['id'],[])+([r['fiscal_period']] if r['fiscal_period'] else [])))} for r in rows]

def chunks(ticker,year=None,period=None):
    header=",(SELECT substr(p.text,1,500) FROM pages p WHERE p.document_id=c.document_id AND p.page_number=c.page_number LIMIT 1) AS page_header" if period and period!='FY' else ''
    sql='SELECT c.*,d.source_url,d.filename,d.fiscal_year,d.fiscal_period,d.origin'+header+' FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.ticker=?'
    args=[ticker]
    if year is not None:sql+=' AND d.fiscal_year=?';args.append(year)
    if period:
        sql+=' AND (d.fiscal_period=? OR EXISTS (SELECT 1 FROM document_periods dp WHERE dp.document_id=d.id AND dp.fiscal_period=?))'
        args.extend([period,period])
    with connection() as c:
        rows=c.execute(sql+' ORDER BY c.id',args).fetchall()
    return [{**dict(r),'sample':False,'url':r['source_url'],'file_url':f"/api/files/{r['document_id']}"+(f"#page={r['page_number']}" if r['filename'].lower().endswith('.pdf') else '')} for r in rows]

def add_document_periods(document_id,periods):
    if any(p not in ('FY','Q1','Q2','Q3','Q4') for p in periods):raise ValueError('Invalid report coverage')
    with connection() as c:
        c.executemany('INSERT INTO document_periods(document_id,fiscal_period) VALUES (?,?) ON CONFLICT DO NOTHING',[(document_id,p) for p in periods])

def reporting_periods(ticker):
    with connection() as c:
        rows=c.execute('SELECT fiscal_year,fiscal_period FROM documents WHERE ticker=? AND fiscal_period IS NOT NULL UNION SELECT d.fiscal_year,dp.fiscal_period FROM documents d JOIN document_periods dp ON dp.document_id=d.id WHERE d.ticker=? ORDER BY fiscal_year DESC,fiscal_period',(ticker,ticker)).fetchall()
    return [dict(r) for r in rows]

def embeddings_for(ids,model):
    if not ids:return {}
    result={}
    with connection() as c:
        for offset in range(0,len(ids),400):
            batch=ids[offset:offset+400]
            sql='SELECT chunk_id,embedding FROM embeddings WHERE model=? AND chunk_id IN ('+','.join('?' for _ in batch)+')'
            for r in c.execute(sql,[model]+batch).fetchall():
                result[r['chunk_id']]=json.loads(str(r['embedding']))
    return result

def save_embeddings(rows,model):
    with connection() as c:
        c.executemany('INSERT INTO embeddings(chunk_id,model,embedding) VALUES (?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET model=excluded.model,embedding=excluded.embedding',[(chunk_id,model,json.dumps(vector)) for chunk_id,vector in rows])

def vector_search(ids,model,vector,limit=20):
    # On Supabase, pgvector executes the exact cosine search in the database.
    if not ids:return []
    with connection() as c:
        if not c.pg:return []
        rows=c.execute('SELECT chunk_id, 1-(embedding OPERATOR(extensions.<=>) ?::extensions.vector) AS score FROM embeddings WHERE model=? AND chunk_id = ANY(?) ORDER BY embedding OPERATOR(extensions.<=>) ?::extensions.vector LIMIT ?', (json.dumps(vector),model,ids,json.dumps(vector),limit)).fetchall()
    return [(r['chunk_id'],float(r['score'])) for r in rows]

def keyword_search(ids,words,limit=30):
    if not ids or not words:return []
    with connection() as c:
        if c.pg:
            rows=c.execute("SELECT id, ts_rank_cd(to_tsvector('english', text), plainto_tsquery('english', ?)) AS rank FROM chunks WHERE id=ANY(?) AND to_tsvector('english',text) @@ plainto_tsquery('english',?) ORDER BY rank DESC LIMIT ?",(' '.join(words),ids,' '.join(words),limit)).fetchall()
        else:
            # FTS5 uses OR to keep natural-language questions from requiring every word.
            rows=c.execute('SELECT id,bm25(chunks_fts) AS rank FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?',(' OR '.join('"'+w+'"' for w in words),limit*10)).fetchall()
            allowed=set(ids);rows=[r for r in rows if r['id'] in allowed][:limit]
        return [r['id'] for r in rows]

def history(ticker,session=None):
    where=' AND id LIKE ?' if session else ''
    args=(ticker,'demo-'+session+'-%') if session else (ticker,)
    with connection() as c:return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM research WHERE ticker=?'+where+' ORDER BY created_at DESC LIMIT 30',args).fetchall()][::-1]
