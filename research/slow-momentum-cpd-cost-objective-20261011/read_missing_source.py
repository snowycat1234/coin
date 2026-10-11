import io,json,zipfile,hashlib
from pathlib import Path
import polars as pl
archive=Path('/workspace/slow-momentum-state/source/features.zip')
out=[]
with zipfile.ZipFile(archive) as z:
    members=json.loads(z.read('MEMBERS.json'))['files']
    for symbol in ('SOLUSDT','XRPUSDT'):
        name=f'source_tables_not_model_inputs/daily_features/{symbol}.parquet'
        raw=z.read(name);identity=hashlib.sha256(raw).hexdigest();assert identity==members[name]['SHA256']
        frame=pl.read_parquet(io.BytesIO(raw),columns=['dt','symbol','close','complete_kline'])
        frame=frame.filter(pl.col('dt').cast(pl.String).str.slice(0,10).is_between(pl.lit('2022-02-24'),pl.lit('2022-03-02')))
        records=[]
        for r in frame.to_dicts():r['dt']=str(r['dt']);records.append(r)
        out.append(dict(symbol=symbol,member=name,member_sha256=identity,records=records))
result=dict(scope='Original hashed archive raw columns only; no funding/lock/provider/alternative data read',sources=out)
with Path('/workspace/slow-momentum-cost-training-state/RAW_SOURCE_GAP.json').open('x') as h:json.dump(result,h,indent=2);h.write('\n')
print(json.dumps(result))
