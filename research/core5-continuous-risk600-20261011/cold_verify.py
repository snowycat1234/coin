"""Recover public bindings into fresh STATE and recompute actual raw minute features."""
import argparse
import io
import json
from pathlib import Path
import sys
import time
import signal
import shutil
import urllib.request
import numpy as np
from prepare import HERE,ROOT,SYMBOLS,PHASES,SourceReader,bind_current,configure,decoded_month,digest,git,old_five,save
from primitives import measure

PREFIX='research/core5-continuous-risk600-20261011/'


def run(commit,phase,state):
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists()
    state.mkdir();configure(state,phase)
    blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(Path(args[0]).absolute())
            if any(path.startswith('/workspace/'+s+'/') for s in ('continuous600-state','btc-beta-residual-state','core5-2022-rv-state',
                        'october2022-state','october2022-complete-state','october2022-union-state','har-rv-state','tail-risk-state')):
                blocked.append(path);raise RuntimeError('Original STATE read forbidden')
    sys.addaudithook(audit);start=time.monotonic()
    signal.alarm(600)
    def bounded():
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=15*1024**3
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<=1000000000
    def public(path):
        bounded()
        with urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+path,timeout=20) as r:
            b=r.read(8000001)
        assert len(b)<8000001
        bounded()
        return b
    indexraw=public(PREFIX+'phases/'+phase+'/SOURCE_INDEX.json');index=json.loads(indexraw)
    invraw=public(PREFIX+'SOURCE_COVERAGE.json');assert digest(invraw)==index['source_inventory_SHA256']
    inv=json.loads(invraw)
    proofraw=public(PREFIX+'phases/'+phase+'/RECOVERY.json');assert digest(proofraw)==index['proof_SHA256']
    proof=bind_current(json.loads(proofraw),commit)
    assert proof['phase']==phase and proof['fits']==proof['wallets']==proof['labels_created']==0
    assert digest(public(PREFIX+'PROTOCOL.json'))==proof['protocol_SHA256']
    assert digest(public(PREFIX+'cold_verify.py'))==digest(Path(__file__).read_bytes())
    for name,sha in proof['code_SHA256'].items():
        assert digest(public(PREFIX+name))==sha==digest((HERE/name).read_bytes())
    # Shared parsers/date guards are numerical dependencies, not merely imports.
    dependency_sha={}
    for name in ('normalize.py','download.py','common.py'):
        path='modules/collector_research/pipeline/'+name
        b=git('show',proof['source_commit']+':'+path)
        assert digest(b)==digest((ROOT/path).read_bytes())==digest(public(path))
        dependency_sha[path]=digest(b)
    saved={}
    for name,row in index['artifacts'].items():
        b=b''.join(SourceReader.part(commit,p) for p in row['parts'])
        assert len(b)==row['bytes'] and digest(b)==row['SHA256']
        (state/name).write_bytes(b);saved[name]=np.load(io.BytesIO(b),allow_pickle=False)
    reader=SourceReader(inv,state,local=False)
    from modules.collector_research.pipeline.normalize import month_limits
    days=[];fives=[];times=[];actual=0;boundary_checks=0
    for y,m in PHASES[phase]:
        l,r=month_limits(y,m);daily={};five=[];t=None
        for symbol in SYMBOLS:
            record=next(x for x in proof['sources'] if x['source']['symbol']==symbol and x['source']['month']==f'{y}-{m:02d}')
            frame,evidence=decoded_month(reader,record['source'],l,r)
            for k in ('original_month_rows','observed_minutes','identical_month_duplicates','repairs','CRC','exact_complete_grid'):
                assert evidence[k]==record[k]
            past=record['past_boundary']
            if past is not None:
                assert past['open_ms']==l-60000 and past['available_us']==l*1000
                if m==PHASES[phase][0][1]:
                    py,pm=(y-1,12) if m==1 else (y,m-1);pl,pr=month_limits(py,pm)
                    previous,_=decoded_month(reader,past['source'],pl,pr)
                    assert previous.timestamp_ms.iloc[-1]==past['open_ms'] and float(previous.close.iloc[-1])==past['close']
                    boundary_checks+=1
                else:
                    prior=next(x for x in proof['sources'] if x['source']['symbol']==symbol and x['end_boundary']['open_ms']==past['open_ms'])
                    assert prior['end_boundary']==past
            measured,at,c=measure(frame,None if past is None else past['close'])
            for k,v in measured.items():daily.setdefault(k,[]).append(v)
            if t is None:t=at
            np.testing.assert_array_equal(t,at)
            assert float(frame.close.iloc[-1])==record['end_boundary']['close'] and frame.timestamp_ms.iloc[-1]==record['end_boundary']['open_ms']
            five.append(c);actual+=len(frame)
        days.append({k:np.column_stack(v) for k,v in daily.items()});fives.append(np.column_stack(five));times.append(t)
        print('COLD_MONTH',phase,y,m,'actual minute features and boundaries exact',flush=True)
        bounded()
    reader.close();available=np.concatenate(times);five=np.concatenate(fives)
    np.testing.assert_array_equal(available,saved['DAILY.npz']['available_us'])
    assert tuple(saved['DAILY.npz']['symbol_order'])==SYMBOLS
    for k in days[0]:
        np.testing.assert_array_equal(np.concatenate([d[k] for d in days]),saved['DAILY.npz'][k])
    ft=np.arange(available[0]-86400000000+300000000,available[-1]+300000000,300000000,dtype=np.int64)
    if phase=='Y2021':
        t,c,sha=old_five();np.testing.assert_array_equal(t,ft);np.testing.assert_array_equal(c,five)
        assert sha==proof['reused_public_five_min']['member_SHA256']
    else:
        assert tuple(saved['FIVE_MIN.npz']['symbol_order'])==SYMBOLS
        np.testing.assert_array_equal(saved['FIVE_MIN.npz']['available_us'],ft)
        np.testing.assert_array_equal(saved['FIVE_MIN.npz']['close'],five)
    assert actual==proof['actual_minutes'] and not blocked
    bounded()
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_GIT_OBJECT_RAW_MINUTE_COLD_RESTORE',artifact_commit=commit,phase=phase,
        source_index_SHA256=digest(indexraw),actual_minutes=actual,calendar_days=proof['calendar_days'],
        valid_joint_RV_days=proof['valid_joint_RV_days'],boundary_previous_month_raw_checks=boundary_checks,
        exact_all_daily_primitives_and_five_min=True,original_STATE_open_attempts=len(blocked),
        public_index_and_code_HTTP_reads=True,large_originals_reused_from_public_pinned_local_Git_objects=True,
        verifier_self_SHA256=digest(Path(__file__).read_bytes()),shared_dependency_SHA256=dependency_sha,
        provider_downloads=0,fits=0,wallets=0,labels_created=0,elapsed_seconds=time.monotonic()-start))
    print((state/'PUBLIC_RESTORE.json').read_text())
    signal.alarm(0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--phase',choices=PHASES,required=True)
    p.add_argument('--state',type=Path,required=True);a=p.parse_args();run(a.commit,a.phase,a.state)
