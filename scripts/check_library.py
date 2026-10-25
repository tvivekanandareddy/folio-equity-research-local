"""Read-only checks of the actual configured database and report corpus."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import store,ai
TICKERS=['AAPL','MSFT','NVDA','AMZN','TSLA','GOOGL','META','NFLX']
def main():
    total=0
    for ticker in TICKERS:
        reports=store.document_list(ticker);chunks=store.chunks(ticker)
        assert reports and chunks,f'{ticker}: missing report'
        assert all(c['ticker']==ticker and c['document_id'] for c in chunks)
        ranked,mode=ai.retrieve('revenue profitability business risks',chunks)
        assert ranked,f'{ticker}: retrieval empty'
        assert all(c['source_url'] and c['page_number']>=1 for c in ranked)
        total+=len(chunks)
        print(f'{ticker}: {len(reports)} report(s), {len(chunks)} excerpts, source-linked {mode} search OK',flush=True)
    with store.connection() as c:
        if c.pg:
            grants=c.execute("SELECT count(*) AS n FROM information_schema.role_table_grants WHERE table_schema='folio' AND grantee IN ('anon','authenticated')").fetchone()['n']
            assert grants==0,'Browser roles must not have table grants'
        print(f'Verified 8 companies and {total} excerpts. No AI API calls made.',flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
