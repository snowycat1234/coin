from pathlib import Path
import json, polars as pl
p=Path('/mnt/d/codex/coin/reports/fast_research/PUBLIC_LONG_547D_SOURCE_REUSE_20261003_V1.json')
d=json.loads(p.read_text())
r=[x for x in d['sources'] if '2024-01'<=x['month']<='2025-06']
print(json.dumps({'source_status':d['status'],'selected_count':len(r),'rows':sum(x['rows'] for x in r),'all_oldQA_complete':all(x['old_quality']['missing_rows']==0 and x['old_quality']['gaps']==0 for x in r),'first':r[0],'last':r[-1],'schemas':{str(s):[(x['symbol'],x['month']) for x in r if str(pl.read_parquet_schema(x['normalized_path']))==s] for s in {str(pl.read_parquet_schema(x['normalized_path'])) for x in r}}},ensure_ascii=False,indent=2))