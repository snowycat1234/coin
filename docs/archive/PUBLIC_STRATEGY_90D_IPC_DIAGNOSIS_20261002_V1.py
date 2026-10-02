from pathlib import Path
import hashlib,json
import polars as pl
ROOT=Path('/mnt/d/codex/coin')
r=json.loads((ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json').read_text())
p=Path(r['minute_source']['path'])
m=pl.read_parquet(p)
f=m.filter(pl.col('open_us').is_between(r['folds'][0]['start_us']-31*86_400_000_000,r['folds'][0]['end_us'],closed='left'))
def digest(df):return hashlib.sha256(df.write_ipc(None).getvalue()).hexdigest()
records={}
for name,df in [('readback',f),('readback_rechunk',f.rechunk()),('rebuild_string_columns',f.with_columns([pl.Series(n,f[n].to_list(),dtype=pl.String) for n in ('symbol','missing_reason')]).rechunk()),('rebuild_all_columns',pl.DataFrame(f.to_dict(as_series=False),schema=f.schema).rechunk())]:
 records[name]={'sha256':digest(df),'chunks':{k:v.n_chunks() for k,v in zip(df.columns,df.get_columns())},'schema':{k:str(v) for k,v in df.schema.items()},'logically_equal':df.equals(f)}
x={'original_report_sha256':hashlib.sha256((ROOT/'reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json').read_bytes()).hexdigest(),'parquet_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reported_parquet_sha256':r['minute_source']['sha256'],'expected_runtime_IPC_sha256':r['folds'][0]['minute_input_sha256'],'rows':f.height,'records':records,'ledger_arrays_read':0,'raw_sources_read':False,'statistical_or_economic_recalculation':False}
q=Path('/home/xflops/coin-state/test-simple-strategy-continuous-90d-audit-20261002-v2/IPC_PORTABILITY_DIAGNOSIS.json')
with q.open('x') as g:json.dump(x,g,indent=2);g.write(chr(10))
print(json.dumps(x))