import hashlib,json
from pathlib import Path
import polars as pl
from scripts.investment.run_shared_direction import stamp
from quant.paths import ROOT,STATE
p=STATE/'d085-shared-direction-20261005-v3/shared_dataset.parquet'
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
b=pl.read_parquet(p)
out=dict(status='READ_ONLY_PAST_REGIME_COVERAGE_NOT_HMM_OR_ALPHA_EVIDENCE',input_path=str(p),input_sha256=digest,
    model_fits=0,new_accounts=0,data_role='ALREADY_SEEN_DEVELOPMENT',periods=[])
for role,start,end in [('TRAIN','2024-09-01','2025-03-01'),('VALIDATION','2025-03-01','2025-05-01'),('ECONOMICS','2025-05-01','2025-07-01')]:
    one=b.filter((pl.col('close_us')>=stamp(start))&(pl.col('close_us')<stamp(end)))
    counts=dict.fromkeys(['BULL','BEAR','SIDEWAYS','HIGH_VOL_CRASH'],0)
    for r in one.filter(pl.col('symbol')=='BTCUSDT').iter_rows(named=True):
        name=('HIGH_VOL_CRASH' if r['return_1d']<-.05 and r['vol_30d']*365**.5>.8 else
            'BULL' if r['ma200_distance']>0 and r['return_20d']>0 else
            'BEAR' if r['ma200_distance']<0 and r['return_20d']<0 else 'SIDEWAYS')
        counts[name]+=1
    matured=one.filter(pl.col('label').is_not_null() & (pl.col('label_available_us')<stamp(end)))
    out['periods'].append(dict(role=role,start=start,end_exclusive=end,counts=counts,
        complete_calendar_days=one.filter(pl.col('symbol')=='BTCUSDT').height,
        matured_labels_by_symbol_same_calendar=True,matured_class_counts={label:matured.filter(pl.col('label')==i).height
            for i,label in enumerate(['SHORT','CASH','LONG'])},
        scope='COUNTS_NOT_INDEPENDENT_SAMPLES; pooled ten coins correlated; 5d labels overlap'))
with (ROOT/'reports/SHARED_DIRECTION_REGIME_COVERAGE_20261005_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out['periods']))
