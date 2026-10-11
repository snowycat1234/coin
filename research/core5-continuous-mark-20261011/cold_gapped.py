"""Verify observed source rows and genuine missing masks; not fullcontinuity."""
import argparse
import io
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from recover_gapped import observed_month,observed_primitives
from mark_source import (HERE,ROOT,PREFIX,PHASES,SYMBOLS,SourceReader,bind_current,configure,inventories,git,digest,save)


def run(commit,state):
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists();state.mkdir();configure(state,'Q32022')
    blocked=[];start=time.monotonic()
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)) and str(Path(args[0]).absolute()).startswith('/workspace/mark-continuous-state/'):
            blocked.append(str(args[0]));raise RuntimeError('OriginalSTATEread forbidden')
    sys.addaudithook(audit)
    prefix=PREFIX+'phases/Q32022/'
    iraw=git('show',commit+':'+prefix+'SOURCE_INDEX.json');index=json.loads(iraw)
    raw=git('show',commit+':'+prefix+'RECOVERY.json');assert digest(raw)==index['proof_SHA256']
    proof=bind_current(json.loads(raw),commit)
    for line in git('show',commit+':'+PREFIX+'GAPPED_SOURCE_SHA256.txt').decode().splitlines():
        sha,p=line.split(maxsplit=1)
        assert digest(git('show',proof['source_commit']+':'+p))==digest(git('show',commit+':'+p))==digest((ROOT/p).read_bytes())==sha
    saved={}
    for name,row in index['artifacts'].items():
        b=b''.join(SourceReader.part(commit,p) for p in row['parts'])
        assert digest(b)==row['SHA256'] and len(b)==row['bytes']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:saved[name]={k:a[k].copy() for k in a.files}
    inv,_,invsha,_=inventories();assert invsha==proof['source_inventory_SHA256']
    reader=SourceReader(inv,state,local=False);days=[];fives=[];times=[];minutes=0;missing=0;boundary=0
    from modules.collector_research.pipeline.normalize import month_limits
    def bounded():
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=16106127360
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<1000000000
    for mi,(y,m) in enumerate(PHASES['Q32022']):
        bounded()
        l,r=month_limits(y,m);daily={};five=[];at=None
        for s in SYMBOLS:
            record=next(v for v in proof['sources'] if v['source']['symbol']==s and v['source']['month']==f'{y}-{m:02d}')
            frame,e=observed_month(reader,record['source'],l,r)
            for k in ('original_month_rows','observed_minutes','original_missing_minutes','identical_month_duplicates','repairs','remaining_missing_open_ms','CRC','exact_complete_grid'):
                assert e[k]==record[k],k
            past=record['past_boundary'];assert past['open_ms']==l-60000 and past['available_us']==l*1000
            if mi==0:
                py,pm=y,m-1;pl,pr=month_limits(py,pm)
                previous,_=observed_month(reader,past['source'],pl,pr)
                assert previous.timestamp_ms.iloc[-1]==past['open_ms'] and float(previous.close.iloc[-1])==past['close'];boundary+=1
            else:
                prev=next(v for v in proof['sources'] if v['source']['symbol']==s and v['end_boundary']['open_ms']==past['open_ms'])
                assert prev['end_boundary']==past
            v,t,c=observed_primitives(frame,past['close'],l,r)
            for k,a in v.items():daily.setdefault(k,[]).append(a)
            if at is None:at=t
            np.testing.assert_array_equal(t,at)
            five.append(c);minutes+=len(frame);missing+=len(e['remaining_missing_open_ms'])
            bounded()
        days.append({k:np.column_stack(v) for k,v in daily.items()});fives.append(np.column_stack(five));times.append(at)
        print('GAPPED_COLD_MONTH',y,m,'observedsource/missingmask exact',flush=True)
    reader.close()
    for name in days[0]:np.testing.assert_array_equal(np.concatenate([d[name] for d in days]),saved['DAILY.npz'][name])
    at=np.concatenate(times);np.testing.assert_array_equal(at,saved['DAILY.npz']['available_us'])
    ft=np.arange(at[0]-86400000000+300000000,at[-1]+300000000,300000000,dtype=np.int64)
    np.testing.assert_array_equal(ft,saved['FIVE_MIN.npz']['available_us'])
    np.testing.assert_array_equal(np.concatenate(fives),saved['FIVE_MIN.npz']['close'])
    assert tuple(saved['DAILY.npz']['symbol_order'])==tuple(saved['FIVE_MIN.npz']['symbol_order'])==SYMBOLS
    assert minutes==proof['actual_minutes'] and missing==proof['remaining_missing_minutes'] and not blocked
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_GAPPED_MARK_SOURCE_RESTORE',artifact_commit=commit,phase='Q32022',
        source_index_SHA256=digest(iraw),actual_minutes=minutes,remaining_missing_minutes=missing,calendar_days=92,
        valid_joint_days=proof['valid_joint_RV_days'],previous_month_raw_boundary_checks=boundary,
        all_observed_rows_daily_primitives_nan_masks_exact=True,full_minute_continuity=False,
        provider_downloads=0,original_STATE_open_attempts=0,fits=0,wallets=0,labels_created=0,elapsed_seconds=time.monotonic()-start))
    print((state/'PUBLIC_RESTORE.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--state',type=Path,required=True)
    a=p.parse_args();run(a.commit,a.state)
