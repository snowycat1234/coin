"""Thin frozen-target adapter; one account, no expert wallet combination."""
import json,math
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
from scripts.investment.oracle_expert_opportunity import CORE

FAMILIES=('ORACLE60D','EQUAL_EXPERTS','STATIC_DIRECTION3')
DAY=86_400_000_000

def load(spec):
    ref=spec['expert_mixture'];path=ROOT/ref['path'];assert path.is_relative_to(ROOT/'reports') and sha(path)==ref['sha256']
    report=json.loads(path.read_bytes())
    assert report['status']=='COMPLETE_FROZEN_EXPERT_OPPORTUNITY_DIAGNOSTIC_NOT_EXECUTABLE_OR_INVESTMENT'
    task=json.loads((STATE/'task-progress'/('task-'+report['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
    proof=ROOT/ref['independent_path'];assert sha(proof)==ref['independent_sha256']
    independent=json.loads(proof.read_bytes());assert independent['maximum_scalar_error_USDT']<1e-7
    assert independent['input']['sha256']==ref['sha256'] and report['real_accounts_new']==report['models_fit']==0
    assert report['protocol']['decision_horizons_days']==[60] and report['investment_status']=='NONE_CASH'
    names=report['protocol']['experts'];assert len(names)==len(set(names))==8
    cases={};source_bindings=[]
    keys=('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','resources','input_adapter','source_acceptance','cycle_regression')
    for entry in report['producers']:
        p=ROOT/entry['path'];assert sha(p)==entry['sha256'];r=json.loads(p.read_bytes())
        task=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
        assert task['status']=='completed' and task['exit_code']==0
        for key in keys:assert r['protocol'][key]==spec[key],'Mixture input/capital/cost mismatch: '+key
        for key in CORE:assert r['binding']['source_hashes'][key]==sha(ROOT/key),'Mixture financial core changed: '+key
        for c in r['cases']:
            mode='CASH' if c['strategy']=='CASH' else 'LONG_ONLY' if c['strategy']=='HOLD' else 'LONG_SHORT'
            if c['strategy'] not in names or c['mode']!=mode:continue
            assert (c['strategy'],c['unit']) not in cases
            s=c['summary'];assert s['completed_minutes']==s['required_minutes']==1051200 and s['terminal_cash_realized']
            assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
            assert c['independent']['target_reference']['maximum_error']<1e-10
            fee=s['contract']['cost_provenance'];assert sha(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json')==fee['fee_source_sha256']
            cases[c['strategy'],c['unit']]=c
        source_bindings.append(entry)
    assert len(cases)==16
    frames={};artifacts=[]
    for entry in report['library']:
        pair=(entry['expert'],entry['unit']);c=cases[pair];assert entry['original_case_id']==c['id']
        v=c['artifacts']['targets.parquet'];assert v==entry['artifacts']['targets.parquet']
        p=Path(v['path']);assert p.is_relative_to(STATE) and sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
        frames[pair]=pl.read_parquet(p);artifacts.append(dict(expert=pair[0],unit=pair[1],**v))
    return dict(names=names,frames=frames,oracle_by_unit={r['unit']:r['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']['segments'] for r in report['results']},
        binding=dict(**ref,experts=names,producer_bindings=source_bindings,targets=artifacts))

def weights(names,days,family,segments=None):
    assert family in FAMILIES and len(names)==len(set(names))
    out=np.zeros((days,len(names)))
    if family=='EQUAL_EXPERTS':out[:]=1/len(names)
    elif family=='STATIC_DIRECTION3':
        for name,value in (('SMA200_SIGNED',.5),('HOLD',.25),('CASH',.25)):out[:,names.index(name)]=value
    else:
        cursor=0
        for k,v in enumerate(segments):
            b,e=v['begin_day'],v['end_day'];assert b==cursor==k*60 and e==min(days,b+60)
            out[b:e,names.index(v['expert'])]=1;cursor=e
        assert cursor==days
    assert np.isfinite(out).all() and (out>=0).all() and np.allclose(out.sum(axis=1),1,rtol=0,atol=1e-15)
    return out

def combine(frames,names,decisions,symbols,blend):
    assert len(decisions)>0 and np.all(np.diff(decisions)==DAY) and len(symbols)==len(set(symbols))
    assert blend.shape==(len(decisions),len(names)) and (blend>=0).all() and np.allclose(blend.sum(axis=1),1,atol=1e-15,rtol=0)
    target=[];raw=[]
    for name in names:
        f=frames[name];lookup={(r['available_us'],r['symbol']):r for r in f.iter_rows(named=True)}
        assert len(lookup)==f.height==len(decisions)*len(symbols)
        assert set(lookup)=={(int(t),s) for t in decisions for s in symbols}
        assert all(r['eligibility_reason']=='ELIGIBLE' for r in lookup.values()),'Only complete common frozen experts in this screen'
        target.append([[lookup[int(t),s]['target_weight'] for s in symbols] for t in decisions])
        raw.append([[lookup[int(t),s]['raw_signed_target'] for s in symbols] for t in decisions])
    result=np.einsum('te,etn->tn',blend,np.asarray(target));unscaled=np.einsum('te,etn->tn',blend,np.asarray(raw))
    assert np.isfinite(result).all() and np.max(np.abs(result))<=.3+1e-12 and np.max(np.abs(result).sum(axis=1))<=.6+1e-12
    return pl.DataFrame([dict(available_us=int(t),symbol=s,target_weight=float(result[i,j]),raw_signed_target=float(unscaled[i,j]),
        mode='LONG_SHORT',eligibility_reason='ELIGIBLE') for i,t in enumerate(decisions) for j,s in enumerate(symbols)])

def verify(frame,frames,names,decisions,symbols,blend,bars):
    # Independent scalar ordered combination and covariance; no einsum.
    sources={n:{(r['available_us'],r['symbol']):r for r in frames[n].iter_rows(named=True)} for n in names}
    actual={(r['available_us'],r['symbol']):r for r in frame.iter_rows(named=True)};error=peak_vol=0.
    assert len(actual)==frame.height==len(decisions)*len(symbols)
    for i,t in enumerate(decisions):
        signed=[];returns=[]
        for s in symbols:
            w=sum(float(blend[i,k])*sources[n][int(t),s]['target_weight'] for k,n in enumerate(names))
            raw=sum(float(blend[i,k])*sources[n][int(t),s]['raw_signed_target'] for k,n in enumerate(names))
            error=max(error,abs(actual[int(t),s]['target_weight']-w),abs(actual[int(t),s]['raw_signed_target']-raw));signed.append(w)
            p=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=t)&(pl.col('available_us')<=t)).sort('close_us').tail(31)
            assert p.height==31 and np.all(np.diff(p['close_us'])==DAY)
            prices=p['close'].to_list();returns.append([prices[k+1]/prices[k]-1 for k in range(30)])
        means=[sum(v)/30 for v in returns]
        variance=sum(signed[a]*signed[b]*sum((x-means[a])*(y-means[b]) for x,y in zip(returns[a],returns[b]))/29*365
            for a in range(len(symbols)) for b in range(len(symbols)))
        sigma=math.sqrt(max(0,variance));peak_vol=max(peak_vol,sigma)
        assert sigma<=.10+1e-10 and sum(abs(w) for w in signed)<=.6+1e-12 and max(abs(w) for w in signed)<=.3+1e-12
    assert error<1e-10
    return dict(status='PASS_SCALAR_ORDERED_FROZEN_EXPERT_COMBINATION_CAPS_AND_PAST_SIGNED_COV',maximum_error=error,rows=frame.height,
        maximum_past_covariance_annual_vol=peak_vol,scope='Targets only; actual one-wallet fills/NAV independently audited')

def targets(library,bars,decisions,symbols,family,unit):
    names=library['names'];frames={n:library['frames'][n,unit] for n in names}
    w=weights(names,len(decisions),family,library['oracle_by_unit'][unit] if family=='ORACLE60D' else None)
    target=combine(frames,names,decisions,symbols,w);proof=verify(target,frames,names,decisions,symbols,w,bars)
    meta=dict(family=family,unit=unit,symbols=list(symbols),experts=names,weights=w.tolist(),
        future_winner_used=family=='ORACLE60D',causal_strategy=family!='ORACLE60D',
        role='NONCAUSAL_ORACLE_REPLAY_NOT_INVESTMENT' if family=='ORACLE60D' else 'FIXED_STATIC_DEVELOPMENT_REFERENCE',
        one_shared_full_capital_account=True,expert_intents_not_separate_funded_wallets=True,
        original_expert_parameters_changed=False,static_weights_optimized=False,
        shadow_cost_surcharge_not_applied_actual_fills_costed_once=True,source=library['binding'],candidate_status='NONE_CASH')
    return target,meta,proof
