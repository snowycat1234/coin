"""Read saved targets and fills to separate veto, covariance and reopening effects.

Descriptive mechanism evidence only: no counterfactual PnL, fit or new wallet.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np

from scripts.research.run_public_momentum import load_past_inputs, sha, save
from scripts.research.public_cross_section_momentum import DAY_US, WEEK_US, ANCHOR_US

ROOT=Path(__file__).resolve().parents[2]
EXPECTED='8da91688f51ae084958b763e485e0dea4880afd3402252a0dc321d7e60540fd9'


def utc(t):return datetime.fromtimestamp(t/1e6,timezone.utc).isoformat()


def read_case(row, sources):
    assert sha(row['result_path'])==row['result_sha256']
    case=json.loads(Path(row['result_path']).read_text());sources[row['result_path']]=row['result_sha256']
    task=case['task'];assert sha(task['target_path'])==task['target_sha256']
    sources[task['target_path']]=task['target_sha256']
    with np.load(task['target_path'],allow_pickle=False) as f:
        dates=f['decision_us'].copy();weights=f['weights'].copy();symbols=f['symbol_order'].tolist()
    assert dates.tolist()==list(range(task['window']['start'],task['window']['end'],DAY_US))
    assert symbols==case['summary']['symbols'] and case['terminal_cash_realized']
    def artifact(name):
        r=case['artifacts'][name];assert sha(r['path'])==r['sha256'];sources[r['path']]=r['sha256']
        raw=gzip.decompress(Path(r['path']).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==r['uncompressed_sha256']
        return json.loads(raw)
    return case,dates,weights,symbols,{n:artifact(n+'.json') for n in ('trades','funding','breaches')}


def target_diagnosis(w0,w1,dates,close,available,core):
    records=[];blocked=[];direct=[];lambdas=[];examples=[]
    for i,t in enumerate(dates):
        j=int(np.searchsorted(available,t));assert available[j]==t and j>=30
        history=close[j-30:j+1];assert np.isfinite(history).all() and (history>0).all()
        r=np.diff(history,axis=0)/history[:-1];cov=np.atleast_2d(np.cov(r,rowvar=False,ddof=1))*365
        momentum=history[-1]/history[-22]-1
        b=(w0[i]<0)&(momentum>=0);v=w0[i].copy();v[b]=0
        sigma=lambda w:float(np.sqrt(max(0.,w@cov@w)))
        old_sigma,mask_sigma,new_sigma=map(sigma,(w0[i],v,w1[i]))
        scale=min(1.,.10/mask_sigma) if mask_sigma else 1.
        error=float(np.abs(w1[i]-v*scale).max());assert error<=1e-12 and new_sigma<=.10+1e-12
        assert np.all(np.abs(w1[i])<=np.abs(w0[i])+1e-12)
        records.append(dict(available_us=int(t),terminal_day=i==len(dates)-1,old_sigma=old_sigma,masked_sigma=mask_sigma,new_sigma=new_sigma,scale=scale,error=error,
            original_long=float(np.maximum(w0[i],0).sum()),confirmed_long=float(np.maximum(w1[i],0).sum()),
            removed_short=float(np.abs(w0[i][b]).sum()),kept_short_extra_reduction=float(np.abs(v[v<0]).sum()-np.abs(w1[i][w1[i]<0]).sum())))
        blocked.append(b);direct.append(v);lambdas.append(scale)
        if b.any() and scale<.999:
            examples.append(dict(utc=utc(t),extra_scale=scale,old_sigma=old_sigma,masked_sigma=mask_sigma,new_sigma=new_sigma,
                original=w0[i].tolist(),direct_veto=v.tolist(),final=w1[i].tolist(),momentum21=momentum.tolist()))
    # End-of-window paid flattening is an execution override, not a gate toggle.
    effective=records[:-1];blocked=np.array(blocked);toggles=[]
    for k,s in enumerate(core):
        changes=[]
        for i in range(1,len(dates)-1):
            rank=lambda t:ANCHOR_US+(int(t)-ANCHOR_US)//WEEK_US*WEEK_US
            if rank(dates[i])==rank(dates[i-1]) and w0[i,k]<0 and w0[i-1,k]<0 and blocked[i,k]!=blocked[i-1,k]:
                changes.append(dict(available_us=int(dates[i]),to='CASH' if blocked[i,k] else 'SHORT'))
        toggles.append(dict(symbol=s,same_rank_sign_toggles=len(changes),to_SHORT=sum(x['to']=='SHORT' for x in changes),to_CASH=sum(x['to']=='CASH' for x in changes),events=changes))
    return dict(days_including_terminal=len(dates),measured_nonterminal_days=len(effective),
        extra_covariance_downscale_days=sum(x['scale']<1-1e-12 for x in effective),minimum_extra_scale=min(x['scale'] for x in effective),
        original_LONG_weight_days=sum(x['original_long'] for x in effective),confirmed_LONG_weight_days=sum(x['confirmed_long'] for x in effective),
        removed_SHORT_weight_days=sum(x['removed_short'] for x in effective),kept_SHORT_extra_downscale_weight_days=sum(x['kept_short_extra_reduction'] for x in effective),
        mean_old_sigma=float(np.mean([x['old_sigma'] for x in effective])),mean_direct_veto_sigma=float(np.mean([x['masked_sigma'] for x in effective])),
        mean_final_sigma=float(np.mean([x['new_sigma'] for x in effective])),max_direct_veto_sigma=max(x['masked_sigma'] for x in effective),
        max_target_reconstruction_error=max(x['error'] for x in records),same_rank_toggles=toggles,
        largest_downscales=sorted(examples,key=lambda x:x['extra_scale'])[:4])


def fill_diagnosis(case,dates,w0,w1,symbols,journals,confirmed):
    index={int(t):i for i,t in enumerate(dates)};columns={s:i for i,s in enumerate(symbols)}
    risks={x['signal_us'] for x in journals['breaches']};groups={};fund=defaultdict(float)
    for f in journals['funding']:
        q=f.get('quantity',0)
        if q:fund['LONG' if q>0 else 'SHORT']+=f['signed_funding_USDT']
    for f in journals['trades']:
        q=f['quantity_before'] or f['quantity_after'];assert q!=0
        side='LONG' if q>0 else 'SHORT';external=bool(f.get('liquidation_takeover'))
        order=f['fill_id'] if external else f['fill_id'].rsplit(':',2)[0]
        key=(f['symbol'],f['signal_us'],order,side,f['leg'])
        if key not in groups:groups[key]=dict(symbol=f['symbol'],signal_us=f['signal_us'],order=order,direction=side,leg=f['leg'],
            start_us=f['event_us'],end_us=f['event_us'],before=f['quantity_before'],after=f['quantity_after'],fills=0,
            turnover_mid=0.,fees=0.,execution=0.,realized=0.,external=external)
        g=groups[key];g['end_us']=f['event_us'];g['after']=f['quantity_after'];g['fills']+=1
        g['turnover_mid']+=f['quantity']*f['execution_mid_price'];g['fees']+=f['fee_amount'];g['execution']+=f['execution_cost'];g['realized']+=f['realized_PnL']
    aggregates={};last_short_close={};reopens=[];direction=defaultdict(lambda:dict(realized=0.,fees=0.,execution=0.,funding=0.,gross=0.,net=0.))
    for g in sorted(groups.values(),key=lambda x:x['start_us']):
        s=g['symbol'];t=g['signal_us'];i=index.get(t);k=columns[s];is_short=g['direction']=='SHORT'
        daily=i is not None;terminal=daily and i==len(dates)-1
        gate_exit=confirmed and daily and not terminal and t not in risks and w0[i,k]<0 and w1[i,k]==0 and is_short and g['leg']=='CLOSE' and g['after']==0
        rank=ANCHOR_US+(int(t)-ANCHOR_US)//WEEK_US*WEEK_US
        prev=last_short_close.get(s)
        if g['external']:category='LIQUIDATION_TAKEOVER_NOT_MARKET_FILL'
        elif terminal:category='TERMINAL_PAID_FLAT'
        elif t in risks:category='RISK_OR_DAILY_AMBIGUOUS' if daily else 'HARD_RISK_REDUCTION'
        elif not daily:category='UNKNOWN_SIGNAL_CLOCK'
        elif gate_exit:category='DAILY_ZERO_TARGET_GATE_FULL_CLOSE'
        elif is_short and g['leg']=='OPEN' and g['before']==0:
            category='SAME_RANK_GATE_REOPEN' if prev and prev['gate_exit'] and prev['rank']==rank else 'SHORT_ENTRY_OTHER'
            if category=='SAME_RANK_GATE_REOPEN':reopens.append(dict(symbol=s,close_signal_us=prev['signal_us'],reopen_signal_us=t,
                close_utc=utc(prev['signal_us']),reopen_utc=utc(t),fees=g['fees'],execution=g['execution'],fill_fragments=g['fills']))
        elif g['leg']=='OPEN':category='LONG_ENTRY_OTHER' if g['before']==0 else 'DAILY_ADD'
        elif g['after']==0:category='DAILY_FULL_CLOSE_OTHER'
        else:category='DAILY_PARTIAL_REDUCTION'
        if is_short and g['leg']=='CLOSE' and g['after']==0:last_short_close[s]=dict(rank=rank,gate_exit=gate_exit,signal_us=t)
        label=g['direction']+'/'+category
        if label not in aggregates:aggregates[label]=dict(logical_order_legs=0,fill_fragments=0,turnover_mid=0.,fees=0.,execution=0.)
        a=aggregates[label];a['logical_order_legs']+=1;a['fill_fragments']+=g['fills']
        for name in ('turnover_mid','fees','execution'):a[name]+=g[name]
        d=direction[g['direction']]
        for name in ('realized','fees','execution'):d[name]+=g[name]
    for side in ('LONG','SHORT'):
        d=direction[side];d['funding']=fund[side];d['gross']=d['realized']+d['execution'];d['net']=d['realized']-d['fees']+d['funding']
        saved=case['summary']['long_short_marked_contribution'][side]
        for name,key in (('fees','fees'),('execution','execution_cost'),('funding','funding'),('gross','gross'),('net','net_contribution')):
            assert abs(d[name]-saved[key])<=1e-7,(side,name,d[name],saved[key])
    return dict(direction_from_actual_fills=dict(direction),order_categories=aggregates,same_rank_gate_reopens=reopens,
        scope='Logical order legs and actual fill costs; descriptive association, not cost-only causal counterfactual. Liquidation not an exchange market fill.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args();began=time.monotonic()
    result=ROOT/'reports/CSMOM_ABSOLUTE_SHORT_20261008.json';assert sha(result)==EXPECTED
    assert os.uname().sysname=='Linux' and a.state.resolve().parent==Path('/home/ubuntu/coin/execution-state')
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000
    assert (group/'memory.swap.max').read_text().strip()=='0'
    a.state.mkdir(exist_ok=False);r=json.loads(result.read_text());p=r['protocol'];sources={str(result):sha(result)}
    parent=json.loads((ROOT/p['parent_protocol']).read_text());assert sha(ROOT/p['parent_protocol'])==p['parent_protocol_sha256']
    close,available,refs=load_past_inputs(parent);core=p['core_symbols'];ix=[p['symbols'].index(s) for s in core];close=close[:,ix]
    targets=[];cases=[]
    for wi,w in enumerate(p['windows'],1):
        target_check=None
        for scale in p['funding_scales']:
            old=next(x for x in r['reused_controls'] if x['window']==w['id'] and x['funding_scale']==scale)
            new=next(x for x in r['cases'] if x['window']==w['id'] and x['funding_scale']==scale)
            c0,dates,w0,symbols,j0=read_case(old,sources);c1,d1,w1,s1,j1=read_case(new,sources)
            assert np.array_equal(dates,d1) and symbols==s1==p['symbols']
            if target_check is None:
                target_check=target_diagnosis(w0[:,ix],w1[:,ix],dates,close,available,core)
                target_check['window']=w['id'];targets.append(target_check)
            else:
                assert target_check==dict(target_diagnosis(w0[:,ix],w1[:,ix],dates,close,available,core),window=w['id'])
            f0=fill_diagnosis(c0,dates,w0,w1,symbols,j0,False);f1=fill_diagnosis(c1,dates,w0,w1,symbols,j1,True)
            delta=dict(gross=new['gross_PnL']-old['gross_PnL'],funding=new['funding']-old['funding'],cost=new['fees']+new['execution_cost']-old['fees']-old['execution_cost'],net=new['net_PnL']-old['net_PnL'])
            assert abs(delta['gross']+delta['funding']-delta['cost']-delta['net'])<=1e-7
            cases.append(dict(window=w['id'],funding_scale=scale,old=f0,new=f1,economic_delta=delta))
        print(f'[DIAG {wi}/5] {w["id"]} target/covariance and two actual cost ledgers',flush=True)
    out=dict(status='COMPLETE_READ_ONLY_CONFIRMATION_MECHANISM',source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),
        inspector_sha256=sha(__file__),parent_result_sha256=sha(result),target_decomposition=targets,cases=cases,source_hashes=sources,daily_input_refs=refs,
        new_wallets=0,new_fits=0,new_configs=0,qualification='NONE_CASH',locked_consumed=False,elapsed_seconds=time.monotonic()-began,
        limitations=['Seen development forensic, no independent validation or new counterfactual performance.',
            'Target decomposition is algebraically exact; target weight-days are not profit, collateral safety or risk-matched alpha.',
            'Trade cost labels reconstruct available order/signal fields. Missing/ambiguous reason remains UNKNOWN/AMBIGUOUS, not fabricated.',
            'Same-week gate reopen counts logical order legs; fragmented fills are separately counted. Associated costs are not all incremental cost.',
            'Both funding unit interpretations remain conditional; account/kernel/quantity-capacity and native rules limitations unchanged.'])
    save(a.state/'RESULTS.json',out);print(json.dumps(dict(status=out['status'],seconds=out['elapsed_seconds'],wallets=0,fits=0)),flush=True)


if __name__=='__main__':main()
