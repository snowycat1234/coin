"""Restore source-only marks and frozen trend intents; no statistical fit."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile
import numpy as np
import pandas as pd
from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
from modules.collector_research.pipeline.download import parse_checksum

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SYMBOLS=("BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT")
DAY=86_400_000_000
DATA="94fe13c494c82bb6e6868e6614eb7298fb15b3c3"
digest=lambda b:hashlib.sha256(b).hexdigest()


def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):
            h.update(b)
    return h.hexdigest()


def save(p,x):
    with p.open('x') as f:
        f.write(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')


def run(archive,bear,output,source):
    git=lambda *x:subprocess.check_output(['git',*x],cwd=ROOT)
    assert git('rev-parse','HEAD').decode().strip()==source and not git('status','--porcelain')
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    index=json.loads(git('show',DATA+':research/core5-2021-economic-data/Y2021/INDEX.json'))
    assert file_sha(archive)==index['package_SHA256']=='b427bd0a17322f4c238cd7a813450fe5dee0f3c3a673ec38743a70784d387ab2'
    members={r['name']:r for r in index['members']}
    evidence=[]
    mark=[]
    with zipfile.ZipFile(archive) as z:
        def read_frame(name,left,right):
            b=z.read(name);check=z.read(name+'.CHECKSUM')
            for n,v in ((name,b),(name+'.CHECKSUM',check)):
                assert len(v)==members[n]['bytes'] and digest(v)==members[n]['SHA256']
            assert digest(b)==parse_checksum(check.decode(),Path(name).name)
            with zipfile.ZipFile(io.BytesIO(b)) as inner:
                assert inner.testzip() is None and len(inner.namelist())==1
            p=output/Path(name).name
            p.write_bytes(b)
            try:
                frame,dups=validate_price(numeric_csv(p),'markPriceKlines',left,right)
            finally:
                p.unlink()
            evidence.append(dict(member=name,SHA256=digest(b),CHECKSUM_SHA256=digest(check),observed_minutes=len(frame),identical_duplicates=dups,CRC=True))
            return frame
        for s in SYMBOLS:
            blocks=[]
            for m in range(1,12):
                l,r=month_limits(2021,m)
                name=f'raw/markPriceKlines/{s}/{s}-1m-2021-{m:02d}.zip'
                frame=read_frame(name,l,r)
                old_rows=len(frame)
                if m==7 and s in ('BTCUSDT','SOLUSDT','XRPUSDT'):
                    parts=[frame]
                    for day in (1,24,25,26,27):
                        parts.append(read_frame(f'raw/markPriceKlines/{s}/{s}-1m-2021-07-{day:02d}.zip',l+(day-1)*86400000,l+day*86400000))
                    frame,common=validate_price(pd.concat(parts,ignore_index=True),'markPriceKlines',l,r)
                    evidence.append(dict(symbol=s,month=m,union_observed_minutes=len(frame),original_month_minutes=old_rows,exact_common_duplicates=common,source_added_minutes=len(frame)-old_rows))
                assert np.array_equal(frame.timestamp_ms.to_numpy(),np.arange(l,r,60000,dtype=np.int64))
                blocks.append(frame.close.to_numpy(dtype=float)[4::5])
                assert time.monotonic()-started<600 and shutil.disk_usage(output).free>=15*1024**3
            mark.append(np.concatenate(blocks))
            print('RECOVERED2021_MARK',s,334*1440,'actual minutes',flush=True)
        context_raw=z.read('derived/CONTEXT_INPUTS.npz')
        assert digest(context_raw)=='775074cc788949e5b12953f4f22d5b724b653e358b04f44b46ecb5dbc703e7cf'
        context=np.load(io.BytesIO(context_raw),allow_pickle=False)
        assert tuple(context['symbol_order'])==SYMBOLS and list(context['original_E5_slots'])==[0,1,4]
        assert list(context['expert_names'])==['CASH','VOL_MANAGED_HOLD','CSMOM21']
        base2021=dict(decision_us=context['decision_us'],symbol_order=np.asarray(SYMBOLS),base=context['expert_targets'][:,2,:],
            target_available_us=context['target_available_us'][:,2],eligible=context['expert_eligible'][:,2]&context['fixed5_covariance_ready'],
            asset_eligible=context['asset_eligible'][:,2,:],past_returns=context['past_returns'])
        assert digest(np.asarray(base2021['base'],dtype='<f8',order='C').tobytes())=='733276fc4ddead2305f53b43dd328189e63a8ef2198c11e475ed1d01145ec7ed'
    # Reuse only measured trade source panels, no old HAR model/result members.
    bundle=HERE.parent/'har-rv-risk-20261011'
    binding=json.loads((bundle/'PUBLIC_BUNDLE.json').read_bytes())
    with zipfile.ZipFile(bundle/'RESULT_BUNDLE.zip') as z:
        name='prepared/FIVE_MIN_CLOSES.npz';b=z.read(name)
        assert digest(b)==binding['members'][name]['SHA256']
        trade2021=np.load(io.BytesIO(b),allow_pickle=False)
        assert tuple(trade2021['symbol_order'])==SYMBOLS
        trade=np.column_stack([trade2021[s][:334*288] for s in SYMBOLS])
    mark=np.column_stack(mark)
    assert mark.shape==trade.shape==(334*288,5)
    clocks2021=np.arange(1609459200000000+300000000,1638316800000000+300000000,300000000,dtype=np.int64)
    octdir=HERE.parent/'core5-october-warmup-20261011'
    novdir=HERE.parent/'core5-2022-rv-source-20261011'
    octproof=json.loads((octdir/'RECOVERY.json').read_bytes())
    novproof=json.loads((novdir/'RECOVERY.json').read_bytes())
    def panel(p,sha):
        assert file_sha(p)==sha
        return np.load(p,allow_pickle=False)
    october=panel(octdir/'prepared/FIVE_MIN_CLOSES.npz',octproof['derived']['FIVE_MIN_CLOSES.npz'])
    with zipfile.ZipFile(novdir/'DATA_BUNDLE.zip') as z:
        b=z.read('prepared/FIVE_MIN_CLOSES.npz')
        assert digest(b)==novproof['artifacts']['FIVE_MIN_CLOSES.npz']
        november=np.load(io.BytesIO(b),allow_pickle=False)
    clocks2022=np.r_[october['available_us'],november['available_us']]
    assert np.all(np.diff(clocks2022)==300000000) and len(clocks2022)==61*288
    trade2022=np.column_stack([np.r_[october['klines_'+s],november['klines_'+s]] for s in SYMBOLS])
    mark2022=np.column_stack([np.r_[october['markPriceKlines_'+s],november['markPriceKlines_'+s]] for s in SYMBOLS])
    assert file_sha(bear)=='98e38bc3f0e6a16fd51a63be880371882d4e2b52df1d8ec5a39963721d2d2bb8'
    with zipfile.ZipFile(bear) as z:
        b=z.read('bear_recovery_data/inputs/BEAR2022NOV_INPUTS.npz')
        assert digest(b)=='c00557727efe5213621958f5bd59cb62268c5f98f9117ea1f4a35f18a9d0ae45'
        c=np.load(io.BytesIO(b),allow_pickle=False)
        assert tuple(c['symbol_order'])==SYMBOLS and list(c['expert_order'])==['CASH','VOL_MANAGED_HOLD','PUBLIC_SMA50_200_SIGNED','DONCHIAN_EXIT10','CSMOM21']
        base2022=dict(decision_us=c['decision_us'],symbol_order=np.asarray(SYMBOLS),base=c['expert_targets'][:,4,:],
            target_available_us=c['target_available_us'][:,4],eligible=c['expert_eligible'][:,4],
            asset_eligible=c['expert_asset_eligible'][:,4,:],past_returns=c['past_returns30'])
    for name,a in (('BASE2021',base2021),('BASE2022',base2022)):
        assert tuple(a['symbol_order'])==SYMBOLS and np.all(a['target_available_us']<=a['decision_us'])
        assert np.isfinite(a['base']).all() and np.max(abs(a['base']))<=.3+1e-12 and np.max(abs(a['base']).sum(1))<=.6+1e-12
        assert not np.any(a['base'][~a['asset_eligible']]) and not np.any(a['base'][~a['eligible']])
        np.savez_compressed(output/(name+'.npz'),**a)
    np.savez_compressed(output/'SOURCE_PANELS.npz',symbol_order=np.asarray(SYMBOLS),
        A2021_available_us=clocks2021,A2021_mark=mark,A2021_trade=trade,
        A2022_available_us=clocks2022,A2022_mark=mark2022,A2022_trade=trade2022)
    save(output/'RECOVERY.json',dict(status='PASS_REAL_MARK_AND_FROZEN_TREND_INPUT_RECOVERY',source_commit=source,
        mark2021_actual_minutes=334*1440*5,source_members=evidence,mark2021_originals=index['package_SHA256'],
        source_context2021_SHA256=digest(context_raw),source_context2022_SHA256='c00557727efe5213621958f5bd59cb62268c5f98f9117ea1f4a35f18a9d0ae45',
        source_clocks='End5minute conservativeavailability; absentJan1/Oct1priorreturns remainunknown, no future completeness predictor',
        artifacts={p.name:file_sha(p) for p in output.iterdir()},fits=0,wallets=0,provider_downloads=0,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--bear',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    a=p.parse_args()
    run(a.archive,a.bear,a.output,a.source_commit)
