"""Recover already-public synchronized source features; zero provider access."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE='306b58c4a52035ac9f374de7c25d40dff22fb658'
SOURCE_PREFIX='research/core5-continuous-risk600-20261011/'
sys.path.insert(0,str(ROOT/SOURCE_PREFIX))
from prepare import SYMBOLS,PHASES,SourceReader,digest,git,old_five,save
from join import assemble


def recover():
    full,coverage=assemble(SOURCE)
    t,old,oldsha=old_five()
    panels=[old];clocks=[t];sources=[dict(commit='b4756ec8fb59457cfd8db74a79ca6a859f07f331',member_SHA256=oldsha)]
    for phase in list(PHASES)[1:]:
        raw=git('show',SOURCE+':'+SOURCE_PREFIX+'phases/'+phase+'/SOURCE_INDEX.json')
        row=json.loads(raw)['artifacts']['FIVE_MIN.npz']
        b=b''.join(SourceReader.part(SOURCE,p) for p in row['parts'])
        assert digest(b)==row['SHA256'] and len(b)==row['bytes']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            panels.append(a['close'].copy());clocks.append(a['available_us'].copy())
        sources.append(dict(phase=phase,index_SHA256=digest(raw),panel_SHA256=digest(b)))
    panel=np.concatenate(panels);clock=np.concatenate(clocks)
    assert panel.shape==(699*288,5) and np.all(np.diff(clock)==300000000)
    np.testing.assert_array_equal(clock[287::288],full['available_us'])
    np.testing.assert_array_equal(panel[287::288],full['close'])
    r=np.diff(np.log(np.vstack([np.full((1,5),np.nan),panel])),axis=0).reshape(699,288,5)
    cov=np.einsum('dti,dtj->dij',r,r)
    assert np.isnan(cov[0]).all() and np.isfinite(cov[1:]).all()
    np.testing.assert_allclose(np.diagonal(cov,axis1=1,axis2=2),full['RV_5m'],rtol=2e-14,atol=1e-18,equal_nan=True)
    # Reuse637-day source-information arithmetic; this is not future-label scoring.
    raw=git('show',SOURCE+':'+SOURCE_PREFIX+'information/TRAINING_SOURCE_COVARIANCE.npz')
    with np.load(io.BytesIO(raw),allow_pickle=False) as a:
        ix=np.searchsorted(full['available_us'],a['available_us'])
        np.testing.assert_array_equal(cov[ix],a['covariance'])
    data=dict(symbol_order=np.asarray(SYMBOLS),available_us=full['available_us'],close=full['close'],realized_covariance=cov)
    return data,r,dict(source_commit=SOURCE,source_panels=sources,coverage=coverage,
        intraday_returns_SHA256=digest(r.tobytes()),intraday_returns_shape=list(r.shape),
        source_information637_exact=True,original_STATE_open_attempts=0,provider_downloads=0,
        minute_CSV_scan='REUSED_FIVE_PUBLIC_COLD_SOURCE_CERTIFICATES',fits=0,wallets=0,
        labels_created=0,scope='Actual five-minute source features only; first unknown covariance remains NaN.')


def run(output,expected=None):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    assert shutil.disk_usage('/workspace').free>=16106127360
    output.mkdir();start=time.monotonic()
    data,r,proof=recover()
    np.savez_compressed(output/'SOURCE_INPUTS.npz',**data)
    if expected is not None:
        with np.load(expected,allow_pickle=False) as a:
            for k,v in data.items():np.testing.assert_array_equal(v,a[k])
        assert (output/'SOURCE_INPUTS.npz').read_bytes()==expected.read_bytes()
        proof['cold_feature_bytes_and_vectors_exact']=True
    proof.update(status='PASS_PUBLIC_SOURCE_FEATURE_RECOVERY',artifact_SHA256=digest((output/'SOURCE_INPUTS.npz').read_bytes()),
        code_SHA256=digest(Path(__file__).read_bytes()),protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),
        source_HEAD=git('rev-parse','HEAD').decode().strip(),elapsed_seconds=time.monotonic()-start)
    assert proof['elapsed_seconds']<120 and sum(p.stat().st_size for p in output.iterdir())<100000000
    save(output/'SOURCE_INPUTS.json',proof)
    print(json.dumps(dict(status=proof['status'],rows=len(data['available_us']),valid_joint_covariance_rows=698,
        elapsed_seconds=proof['elapsed_seconds'],artifact_SHA256=proof['artifact_SHA256'],fits=0,wallets=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--expected',type=Path)
    a=p.parse_args();run(a.output,a.expected)
