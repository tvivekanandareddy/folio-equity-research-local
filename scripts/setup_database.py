"""Verify private Supabase credentials and apply the idempotent app schema."""
from pathlib import Path
import sys
from dotenv import load_dotenv
import os
import psycopg
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
def main():
    url=os.getenv('DATABASE_URL','').strip()
    if not url:
        print('DATABASE_URL is missing.');return 1
    try:
        with psycopg.connect(url,connect_timeout=15,sslmode='require') as con:
            print('Supabase PostgreSQL connection succeeded.',flush=True)
            con.execute((ROOT/'supabase'/'schema.sql').read_text(),prepare=False)
            count=con.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='folio'").fetchone()[0]
            print(f'Application schema ready: {count} tables. Credentials were not displayed.',flush=True)
        return 0
    except psycopg.Error as exc:
        print(f'Database setup failed: {type(exc).__name__}; SQLSTATE={exc.sqlstate or "connection error"}. Credentials were not displayed.')
        return 1
    except Exception as exc:
        print(f'Database setup failed: {type(exc).__name__}. Check the connection string formatting.');return 1
if __name__=='__main__':raise SystemExit(main())
