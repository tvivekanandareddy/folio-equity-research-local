-- Private application schema: only the Python backend connects to it.
-- Run once through Supabase SQL Editor, then store the Session pooler URI in .env.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;
create schema if not exists folio;
set search_path to folio, extensions, public;

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
-- Reviewed coverage: a Q4 earnings release may also cover the full fiscal year.
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

CREATE TABLE IF NOT EXISTS embeddings (
 chunk_id TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
 model TEXT NOT NULL, embedding extensions.vector NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_text_idx ON chunks USING gin(to_tsvector('english',text));
-- No direct browser/Data API access. The backend uses a server-only connection.
REVOKE ALL ON SCHEMA folio FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA folio FROM anon, authenticated;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE research ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_candidates ENABLE ROW LEVEL SECURITY;
