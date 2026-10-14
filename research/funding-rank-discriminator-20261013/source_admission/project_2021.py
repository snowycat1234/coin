"""Bounded original event projection and coverage admission; no baskets/PnL."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
DAY=86400000000;HOUR=3600000000;JITTER=60000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
START=1609459200000000;END=1640995200000000
LOWER=START-23*DAY
SOURCE_SHA='bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'


def project():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    raw=(HERE/'TEMPORAL_FEATURE_SOURCE.zip').read_bytes()
    assert len(raw)==2246454 and hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    out={};summary={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        members=json.loads(z.read('MEMBERS.json'))['files']
        for s in SYMBOLS:
            name=f'source_tables_not_model_inputs/economics/{s}_funding_events.parquet'
            b=z.read(name);pin=members[name]
            assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['SHA256']
            # Avoid Dataset/background thread shutdown and whitelist ONLY the
            # three original settled-input columns. Charge marks/owned rewards
            # are never read. Date cut precedes array/canonical record export.
            pf=pq.ParquetFile(io.BytesIO(b))
            table=pf.read(columns=['calc_time_ms','last_funding_rate','funding_interval_hours'],use_threads=False)
            rows=[r for r in table.to_pylist() if LOWER//1000<=r['calc_time_ms']<END//1000]
            t=np.array([r['calc_time_ms']*1000 for r in rows],np.int64)
            rates=np.array([r['last_funding_rate'] for r in rows],float)
            h=np.array([r['funding_interval_hours'] for r in rows],float)
            assert np.all(np.diff(t)>0) and np.isfinite(rates).all() and np.isfinite(h).all() and (h>0).all()
            assert np.all(np.abs(np.diff(t)-h[1:]*HOUR)<=JITTER)
            complete={}
            for day in range(LOWER,END,DAY):
                keep=(t>=day)&(t<day+DAY);a=t[keep];v=h[keep]
                # These exact2020Dec/2021 records have only8h source-field
                # intervals, so daily edges can be certified without the
                # asymmetric final-interval extrapolation used in old code.
                # No general8h assumption is exported into the new core.
                assert np.all(v==8.) and len(a)==3
                assert np.all(np.abs(a-(day+np.array([0,8,16])*HOUR))<=JITTER)
                complete[str(day)]=a.tolist()
            year=(t>=START)&(t<END)
            assert int(year.sum())==1095
            out[s]={'times':t.tolist(),'rates':rates.tolist(),'hours':h.tolist(),
                    'interval_hours_provenance':'EXACT_ORIGINAL_TRANSFER_PARQUET_FIELD; ORIGINAL_RAW_CSV_NOT_NEWLY_RECHECKED',
                    'complete_day_event_ids':complete}
            summary[s]={'projected_events':len(t),'full2021_events':int(year.sum()),
                        'first_event_us':int(t[0]),'last_event_us':int(t[-1]),
                        'original_transfer_field_interval_hours':sorted(set(h.tolist())),
                        'source_member':name,'source_member_SHA256':pin['SHA256'],
                        'coverage':'EXACT_ORIGINAL_SEALED_IDS_PLUS_OBSERVED_FULL8H_CADENCE_FOR_THIS_SPECIFIC_SOURCE'}
    return out,summary


if __name__=='__main__':
    events,summary=project()
    p=HERE/'Y2021_RAW_EVENTS_PROJECTED.json';assert not p.exists()
    b=(json.dumps(events,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();p.write_bytes(b)
    receipt={'status':'PASS_EXACT_SEALED2021_INPUT_PROJECTION_NO_BASKET_EVALUATION',
             'source_commit':'e0d3400b23842f11f167a63e7d80856d76501de8',
             'source_archive_SHA256':SOURCE_SHA,'source_archive_bytes':2246454,
             'projected_file':p.name,'projected_bytes':len(b),'projected_SHA256':hashlib.sha256(b).hexdigest(),
             'projection_calendar_us':[LOWER,END], 'full_year_events':5475,'symbols':summary,
             'raw_rate_units':'CONDITIONAL_RAW_AS_FRACTION1_UNCERTIFIED',
             'publication_clock':'CONDITIONAL24H_DAY_PROXY_NOT_REAL_PIT',
             'fresh_provider_requests':0,'fits':0,'wallets':0,'historical_basket_evaluations':0,
             'pyarrow_version':pa.__version__,'numpy_version':np.__version__,
             'source_values_not_roundtrip_certified_against_original_raw_CSV':True}
    (HERE/'Y2021_PROJECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
