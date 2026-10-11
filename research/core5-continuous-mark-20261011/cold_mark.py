"""FreshSTATE reparse of public mark raw sources and actual past boundary."""
import argparse
import io
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from mark_source import (HERE,ROOT,PREFIX,PHASES,SYMBOLS,SourceReader,bind_current,configure,
    inventories,complete_month,identity,measure,digest,git,save)


def run(commit,phase,state):
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists()
    state.mkdir();configure(state,phase);start=time.monotonic();blocked=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(Path(args[0]).absolute())
            if path.startswith('/workspace/mark-continuous-state/'):
                blocked.append(path);raise RuntimeError('Original preparationSTATE forbidden')
    sys.addaudithook(audit)
    raw=git('show',commit+':'+PREFIX+'phases/'+phase+'/SOURCE_INDEX.json');index=json.loads(raw)
    proofraw=git('show',commit+':'+PREFIX+'phases/'+phase+'/RECOVERY.json');assert digest(proofraw)==index['proof_SHA256']
    proof=bind_current(json.loads(proofraw),commit)
    for line in git('show',commit+':'+PREFIX+'SOURCE_SHA256.txt').decode().splitlines():
        sha,p=line.split(maxsplit=1)
        assert digest(git('show',proof['source_commit']+':'+p))==digest(git('show',commit+':'+p))==digest((ROOT/p).read_bytes())==sha,p
    saved={}
    for name,row in index['artifacts'].items():
        b=b''.join(SourceReader.part(commit,p) for p in row['parts'])
        assert len(b)==row['bytes'] and digest(b)==row['SHA256']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:saved[name]={k:a[k].copy() for k in a.files}
    inv,_,invsha,_=inventories();assert invsha==proof['source_inventory_SHA256']
    reader=SourceReader(inv,state,local=False);days=[];fives=[];times=[];minutes=0;boundary_checks=0
    from modules.collector_research.pipeline.normalize import month_limits
    for mi,(y,m) in enumerate(PHASES[phase]):
        l,r=month_limits(y,m);daily={};five=[];clock=None
        for symbol in SYMBOLS:
            record=next(v for v in proof['sources'] if v['source']['symbol']==symbol and v['source']['month']==f'{y}-{m:02d}')
            frame,e=complete_month(reader,record['source'],l,r)
            for name in ('original_month_rows','observed_minutes','original_missing_minutes','identical_month_duplicates','repairs','CRC','exact_complete_grid'):
                assert e[name]==record[name],name
            past=record['past_boundary']
            if past is not None:
                identity(past['source']);assert past['open_ms']==l-60000 and past['available_us']==l*1000
                if mi==0:
                    py,pm=(y-1,12) if m==1 else (y,m-1);pl,pr=month_limits(py,pm)
                    previous,_=complete_month(reader,past['source'],pl,pr)
                    assert previous.timestamp_ms.iloc[-1]==past['open_ms'] and float(previous.close.iloc[-1])==past['close']
                    boundary_checks+=1
                else:
                    prev=next(v for v in proof['sources'] if v['source']['symbol']==symbol and v['end_boundary']['open_ms']==past['open_ms'])
                    assert prev['end_boundary']==past
            result,t,c=measure(frame,None if past is None else past['close'])
            for name,v in result.items():
                if name in saved['DAILY.npz']:daily.setdefault(name,[]).append(v)
            if clock is None:clock=t
            np.testing.assert_array_equal(clock,t)
            assert float(frame.close.iloc[-1])==record['end_boundary']['close'] and frame.timestamp_ms.iloc[-1]==record['end_boundary']['open_ms']
            five.append(c);minutes+=len(frame)
        days.append({k:np.column_stack(v) for k,v in daily.items()});fives.append(np.column_stack(five));times.append(clock)
        print('MARK_COLD_MONTH',phase,y,m,'allactualminute/primitives/boundaryverified',flush=True)
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=16106127360
    reader.close();at=np.concatenate(times);five=np.concatenate(fives)
    assert tuple(saved['DAILY.npz']['symbol_order'])==tuple(saved['FIVE_MIN.npz']['symbol_order'])==SYMBOLS
    np.testing.assert_array_equal(at,saved['DAILY.npz']['available_us'])
    for name in days[0]:np.testing.assert_array_equal(np.concatenate([d[name] for d in days]),saved['DAILY.npz'][name])
    ft=np.arange(at[0]-86400000000+300000000,at[-1]+300000000,300000000,dtype=np.int64)
    np.testing.assert_array_equal(ft,saved['FIVE_MIN.npz']['available_us']);np.testing.assert_array_equal(five,saved['FIVE_MIN.npz']['close'])
    assert minutes==proof['actual_minutes'] and not blocked
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_RAW_MARK_MINUTE_COLD_RESTORE',artifact_commit=commit,phase=phase,
        source_index_SHA256=digest(raw),actual_minutes=minutes,calendar_days=proof['calendar_days'],
        valid_joint_days=proof['valid_joint_RV_days'],previous_month_raw_boundary_checks=boundary_checks,
        all_daily_primitives_five_min_clocks_exact=True,original_STATE_open_attempts=0,provider_downloads=0,
        fits=0,wallets=0,labels_created=0,elapsed_seconds=time.monotonic()-start,
        domain='IndependentofficialmarkPriceKlines, no trade or exactcharge-mark substitution'))
    print((state/'PUBLIC_RESTORE.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--phase',choices=PHASES,required=True)
    p.add_argument('--state',type=Path,required=True);a=p.parse_args();run(a.commit,a.phase,a.state)
