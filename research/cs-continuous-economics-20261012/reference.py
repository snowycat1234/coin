"""Actual whole-calendar fixed-route reference, never a native certification."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from core import match,quantity_reference,DAY,SYMBOLS,ARMS

def save(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(state,source):
    import subprocess
    git=lambda *args:subprocess.check_output(['git',*args],cwd=ROOT)
    assert not state.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==source
    for line in (HERE/'REFERENCE_SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
    state.mkdir();started=time.monotonic();p=json.loads((HERE/'PROTOCOL.json').read_text());path=ROOT/p['source']['daily_cube'];assert sha(path)==p['source']['daily_cube_SHA256']
    with np.load(path,allow_pickle=False) as z:
        d=z['decision_us'];t=z['close_available_us'];price=z['close'];vol=z['benchmark_targets'];assets=z['asset_eligible'];p0=z['p0'];p1=z['p1'];fp=z['funding_per_unit'];good=z['owned_interval_valid'];label=z['label_complete']
    w,proof,states,diag=match(t,price,d,vol,assets)
    old=ROOT/'research/minute-conditional-selector-20261011/input/SOURCE_PREPARED.npz'
    with np.load(old,allow_pickle=False) as z:
        assert tuple(z['symbol_order'])==SYMBOLS;ids=np.searchsorted(d,z['decision_us']);np.testing.assert_array_equal(d[ids],z['decision_us'])
        np.testing.assert_array_equal(w['CS_ORIGINAL'][ids],z['targets'][:,2]);np.testing.assert_array_equal(np.array(diag['current_eligible'])[ids],z['asset_eligible'][:,2])
    changed=price.copy();cut=int(pd.Timestamp('2022-01-01',tz='UTC').value//1000);changed[t>cut]*=np.linspace(1.01,2.,int((t>cut).sum()))[:,None]
    audit,_,_,_=match(t,changed,d,vol,assets)
    for a in ARMS:np.testing.assert_array_equal(w[a][d<=cut],audit[a][d<=cut])
    complete=label&good.all(1)&np.isfinite(p0).all(1)&np.isfinite(p1).all(1)&np.isfinite(fp).all(1)&(p0>0).all(1)&(p1>0).all(1)&(vol>0).all(1)
    # Independent raw source has known Jul12/13 holes. Keep all target dates;
    # conservative current/next completed-mark scoring proof excludes Jul11-13.
    gaps=(d>=int(pd.Timestamp('2022-07-11',tz='UTC').value//1000))&(d<=int(pd.Timestamp('2022-07-13',tz='UTC').value//1000));complete[gaps]=False
    one=[];quarter=[];quarter_rows=[]
    for i,at in enumerate(d):
        for a in ARMS:
            if a!='CASH' and not complete[i]:one.append(dict(decision_us=int(at),arm=a,status='NOT_EVALUABLE_COMMON_ECONOMIC_SOURCE',net_USDT=None));continue
            report,rows=quantity_reference(d[i:i+1],w[a][i:i+1],p0[i:i+1],p1[i:i+1],fp[i:i+1],good[i:i+1],complete[i:i+1])
            one.append(dict(decision_us=int(at),arm=a,status=report['status'],net_USDT=report['net_USDT'],cost_USDT=rows[0]['cost'] if rows else None,funding_cash_USDT=rows[0]['funding_cash'] if rows else None,state=str(states[i])))
    for year in (2021,2022,2023):
        for month in (1,4,7,10):
            start=pd.Timestamp(year=year,month=month,day=1,tz='UTC');end=start+pd.DateOffset(months=3);sel=(d>=start.value//1000)&(d<end.value//1000)
            for a in ARMS:
                report,rows=quantity_reference(d[sel],w[a][sel],p0[sel],p1[sel],fp[sel],good[sel],complete[sel]);quarter.append(dict(quarter=f'{year}Q{(month-1)//3+1}',arm=a,**report))
                quarter_rows += [dict(quarter=f'{year}Q{(month-1)//3+1}',arm=a,**r) for r in rows]
    frame=pd.DataFrame(one);summary=[]
    for year in (2021,2022,2023):
        for a in ARMS:
            sel=(frame.arm==a)&(frame.decision_us>=pd.Timestamp(f'{year}-01-01',tz='UTC').value//1000)&(frame.decision_us<pd.Timestamp(f'{year+1}-01-01',tz='UTC').value//1000);x=frame[sel]
            summary.append(dict(year=year,arm=a,planned_days=len(x),evaluable_paid_day_references=int(x.net_USDT.notna().sum()),mean_paid_day_reference_net_USDT=float(x.net_USDT.mean()),scope='SEPARATE_FRESH_ONE_DAY_PAID_REFERENCES_NOT_PORTFOLIO_INCOME'))
    frame.to_csv(state/'PAID_DAY_REFERENCES.csv',index=False);pd.DataFrame(quarter_rows).to_csv(state/'QUARTER_TRACES.csv',index=False);save(state/'QUARTER_RESULTS.json',quarter)
    np.savez_compressed(state/'TARGETS.npz',decision_us=d,symbol_order=np.array(SYMBOLS),state=states,common_outcome_complete=complete,**w)
    save(state/'CAUSAL_RISK_PROOF.json',proof)
    report=dict(status='COMPLETE_FIXED_FULL_CALENDAR_REFERENCE_WITH_EXPLICIT_GAPS',science_source_commit=source,natural_calendar_days=len(d),source_cube_SHA256=sha(path),original_CS_target_parity='EXACT_ALL_REUSED_PREFIX_ROWS',real_suffix_invariance=True,summary=summary,reference_quarters=60,completed_quarter_references=sum(r['paid_terminal'] for r in quarter),stopped_quarter_references=sum(not r['paid_terminal'] for r in quarter),unresolved_positions_preserved=True,new_models=0,new_native_wallets=0,provider_downloads=0,scope=p['reference_role'],seconds=time.monotonic()-started)
    save(state/'RESULT.json',report);assert report['seconds']<120;print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
