"""Load the verified eight-company report manifest into the configured workspace."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import sec,store,ingest

def main():
    manifest=json.loads((ROOT/'data'/'report_manifest.json').read_text())
    success=0
    for item in manifest:
        if item.get('status')!='downloaded':continue
        ticker=item['ticker']
        try:
            company=sec.import_company(item['cik'],ticker)
        except sec.SECError:
            company={'ticker':ticker,'name':item['name'],'cik':item['cik'],'sector':'Public company','origin':'sec','metrics':{},'periods':[],'documents':[],'comparable':False,'warning':'SEC metric snapshot unavailable; verified report research is ready.','retrieved_at':None}
        store.save_company(company)
        r=ingest.ingest((ROOT/item['path']).read_bytes(),Path(item['path']).name,ticker,title=item['title'],source_url=item['url'],fiscal_year=item['fiscal_year'],fiscal_period=item['fiscal_period'],origin='investor_relations')
        success+=1;print(f'{ticker}: {r["pages"]} pages/sections, {r["chunks"]} excerpts, duplicate={r["duplicate"]}',flush=True)
    print(f'Report library ready for {success} companies.',flush=True)
    return 0 if success>=8 else 1
if __name__=='__main__':raise SystemExit(main())
