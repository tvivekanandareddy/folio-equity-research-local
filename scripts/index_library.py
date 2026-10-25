"""Build cached vectors for saved reports using the explicitly configured provider."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import ai,store

def main():
    if ai.embedding_provider()=='none':
        print('Choose an embedding provider in .env first. Nothing indexed.')
        return 1
    print('Embedding provider:',ai.embedding_provider(),'Model:',ai.model_id(),flush=True)
    try:
        for company in store.companies():
            ticker=company['ticker'];docs=store.chunks(ticker)
            if not docs:continue
            indexed=ai.index_documents(docs)
            cached=len(store.embeddings_for([d['id'] for d in docs],ai.model_id()))
            print(f'{ticker}: {indexed} new vectors; {cached}/{len(docs)} cached.',flush=True)
    except ai.AIError as exc:
        print(str(exc));print('Completed batches are saved. Rerun to resume missing batches.')
        return 1
    except Exception:
        print('Indexing stopped. Check database connectivity. Credentials are not logged.')
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
