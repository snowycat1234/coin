"""One predeclared mature fit and two seen historical diagnostics."""
import argparse
from datetime import datetime,timezone
import inspect
import json
from pathlib import Path
import subprocess
import time
import urllib.request
import scipy
import numpy as np
from tail import DAY,SYMBOLS,Q,summarize,feature,calibrate,forecast,pinball,bootstrap,downsize
from prepare import ROOT,HERE,save,file_sha,digest


def stamp(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000000)


def run(prepared,output,source):
    git=lambda *a:subprocess.check_output(['git',*a],cwd=ROOT).decode().strip()
    assert git('rev-parse','HEAD')==source and not git('status','--porcelain')
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    save(output/'STARTED.json',dict(source_commit=source,scientific_attempt=1,planned_historical_fits=5,wallets=0,
        protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),preparation_proof_SHA256=file_sha(prepared/'RECOVERY.json')))
    bound=[]
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        expected,path=line.split(maxsplit=1)
        assert file_sha(ROOT/path)==expected
        with urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+source+'/'+path,timeout=20) as r:
            raw=r.read(1000000)
        assert digest(raw)==expected
        bound.append(dict(path=path,SHA256=expected))
    assert scipy.__version__=='1.18.1'
    from scipy.optimize import _linprog,_linprog_highs
    for module,expected in ((_linprog,'66633d0193e4482a54f38f4890f15d0437aea9eacc6c2ac3b41746b81c72513d'),
            (_linprog_highs,'32999bba42521a001d08bd9a1a02ca663b8b7eb93b6f799f37438e062484c89a')):
        assert file_sha(Path(inspect.getfile(module)))==expected
    save(output/'SOURCE_PUBLIC_READBACK.json',dict(source_commit=source,sources=bound,local_solver_sources_verified=True,historical_fits=0))
    recovery=json.loads((prepared/'RECOVERY.json').read_bytes())
    for name,sha in recovery['artifacts'].items():
        assert file_sha(prepared/name)==sha
    arrays=np.load(prepared/'SOURCE_PANELS.npz',allow_pickle=False)
    assert tuple(arrays['symbol_order'])==SYMBOLS
    profiles={};trade={};context={}
    for label in ('A2021','A2022'):
        profiles[label]=summarize(arrays[label+'_mark'],arrays[label+'_available_us'])
        trade[label]=summarize(arrays[label+'_trade'],arrays[label+'_available_us'])
        context[label]=np.load(prepared/('BASE'+label[1:]+'.npz'),allow_pickle=False)
    p=profiles['A2021'];t=p['available']
    training=np.flatnonzero((t>=stamp('2021-02-02'))&(t<=stamp('2021-08-31')))
    assert len(training)==211 and t[training[-1]+1]==stamp('2021-09-01')
    blocks=(('SEP_NOV2021','A2021','2021-09-02','2021-11-30',90),('NOV2022','A2022','2022-11-01','2022-11-30',30))
    eval_ix={}
    maximum_return_error=0.
    for block,label,start,end,count in blocks:
        ix=np.flatnonzero((profiles[label]['available']>=stamp(start))&(profiles[label]['available']<=stamp(end)))
        assert len(ix)==count and profiles[label]['available'][ix[-1]+1]==stamp(end)+DAY
        eval_ix[block]=ix
        for i in np.r_[training,ix] if label=='A2021' else ix:
            decision=int(profiles[label]['available'][i]);c=context[label]
            j=int(np.searchsorted(c['decision_us'],decision))
            assert c['decision_us'][j]==decision and c['target_available_us'][j]<=decision
            close=trade[label]['close']
            returns=np.diff(close[i-30:i+1],axis=0)/close[i-30:i]
            maximum_return_error=max(maximum_return_error,float(abs(returns-c['past_returns'][j]).max()))
            np.testing.assert_allclose(returns,c['past_returns'][j],rtol=0,atol=2e-14)
            feature(profiles[label],int(i))
    save(output/'PREFIT_INPUT_CHECKS.json',dict(training_rows=211,diagnostic_rows=120,maximum_return_error=maximum_return_error,
        saved_trend_identity=True,causal_exact_dates_and_maturity=True,fits=0,wallets=0))
    model=calibrate(p,training,stamp('2021-09-01'),lambda m:save(output/('MODEL_'+m['symbol']+'.json'),m))
    save(output/'MODEL.json',model)
    constant=np.array([m['empirical_unconditional'] for m in model['models']])
    train_scales=np.array([np.minimum(1,constant/forecast(p,int(i),model)['CONDITIONAL']) for i in training])
    static=train_scales.mean(0)
    # Future suffix does not enter earlier features or frozen predictions.
    changed={k:np.array(v,copy=True) for k,v in p.items()}
    future=changed['available']>=stamp('2021-10-01')
    for k in ('RV','RSplus','excursion','close'):
        changed[k][future]*=3
    prefix_error=0.
    for i in np.flatnonzero((t>=stamp('2021-09-02'))&(t<stamp('2021-10-01'))):
        prefix_error=max(prefix_error,float(abs(forecast(p,int(i),model)['CONDITIONAL']-forecast(changed,int(i),model)['CONDITIONAL']).max()))
    gates={'future_suffix_error_zero':prefix_error==0};results={};saved={};risk={};checks=[]
    for block,label,start,end,count in blocks:
        profile=profiles[label];ix=eval_ix[block]
        preds={a:[] for a in ('CONDITIONAL','VOL_SCALED','UNCONDITIONAL')}
        weights={a:[] for a in ('BASE','CONDITIONAL','VOL_SCALED','STATIC_TRAIN')}
        scales=[]
        for i in ix:
            decision=int(profile['available'][i]);c=context[label]
            j=int(np.searchsorted(c['decision_us'],decision));base=c['base'][j]
            f=forecast(profile,int(i),model)
            for arm in preds:
                preds[arm].append(f[arm])
            weights['BASE'].append(base)
            for arm,s in (('CONDITIONAL',np.minimum(1,constant/f['CONDITIONAL'])),('VOL_SCALED',np.minimum(1,constant/f['VOL_SCALED'])),('STATIC_TRAIN',static)):
                w,witness=downsize(base,s,c['past_returns'][j])
                weights[arm].append(w)
            scales.append(np.minimum(1,constant/f['CONDITIONAL']))
            checks.append(dict(block=block,decision_us=decision,feature_latest_available_us=decision,
                label_mature_us=int(profile['available'][i+1]),base_eligible=bool(c['eligible'][j])))
        preds={a:np.asarray(v) for a,v in preds.items()};weights={a:np.asarray(v) for a,v in weights.items()}
        actual=profile['excursion'][ix+1]
        losses={a:pinball(actual,v) for a,v in preds.items()}
        compare={}
        for arm in ('VOL_SCALED','UNCONDITIONAL'):
            compare[arm]=dict(relative_pinball_improvement=1-float(losses['CONDITIONAL'].mean()/losses[arm].mean()),
                improved_assets=int(np.sum(losses['CONDITIONAL'].mean(0)<losses[arm].mean(0))),
                baseline_mean_pinball=float(losses[arm].mean()),conditional_mean_pinball=float(losses['CONDITIONAL'].mean()))
        delta=np.column_stack([(losses['CONDITIONAL']-losses[a]).mean(1) for a in ('VOL_SCALED','UNCONDITIONAL')])
        ci=bootstrap(delta)
        coverage=float((actual<=preds['CONDITIONAL']).mean())
        gates[block+'_relative_improvement_ge002']=compare['VOL_SCALED']['relative_pinball_improvement']>=.02
        gates[block+'_at_least3_assets']=compare['VOL_SCALED']['improved_assets']>=3
        gates[block+'_coverage']=.80<=coverage<=.98
        for j,a in enumerate(('VOL_SCALED','UNCONDITIONAL')):
            gates[block+'_'+a+'_bootstrap_upper_negative']=bool(ci[j,1]<0)
        results[block]=dict(rows=count,comparisons=compare,conditional_coverage=coverage,
            coverage_per_asset=(actual<=preds['CONDITIONAL']).mean(0).tolist(),paired_bootstrap95=ci.tolist())
        saved[block+'_decision_us']=profile['available'][ix]
        saved[block+'_label_mature_us']=profile['available'][ix+1]
        saved[block+'_actual']=actual
        for a,v in preds.items():
            saved[block+'_forecast_'+a]=v
        for a,v in weights.items():
            saved[block+'_weights_'+a]=v
        future_trade=trade[label]['close'][ix+1]/trade[label]['close'][ix]-1
        markprices=arrays[label+'_mark']
        sample_return=np.vstack([np.full((1,5),np.nan),np.diff(np.log(markprices),axis=0)]).reshape(-1,288,5)[ix+1]
        risk[block]={}
        for a,w in weights.items():
            turn=float(abs(np.diff(np.vstack([np.zeros((1,5)),w,np.zeros((1,5))]),axis=0)).sum())
            variance=float(np.square(np.einsum('dka,da->dk',sample_return,w)).sum(1).mean())
            tail=(weights['BASE']<0)&(actual>constant)
            normal=(weights['BASE']<0)&(future_trade<=0)&~tail
            risk[block][a]=dict(mean_target_gross=float(abs(w).sum(1).mean()),mean_target_short=float(np.maximum(-w,0).sum(1).mean()),
                fixed_weight_mark_intraday_annual_sigma=float(np.sqrt(variance*365)),gross_closed_price_proxy_USDT=float((w*future_trade).sum()*10000),
                turnover_cost_proxy_USDT=turn*.00135*10000,short_tail_asset_days=int(tail.sum()),
                short_tail_price_proxy_USDT=float((w*future_trade)[tail].sum()*10000),normal_down_short_asset_days=int(normal.sum()),
                normal_down_short_price_proxy_USDT=float((w*future_trade)[normal].sum()*10000))
    np.savez_compressed(output/'SAVED_FORECASTS_TARGETS.npz',symbol_order=np.asarray(SYMBOLS),**saved)
    save(output/'DAILY_CHECKS.json',checks)
    save(output/'RESULT.json',dict(status='PREDICTIVE_GATE_PASS' if all(gates.values()) else 'STOP_FIXED_SHORT_UPSIDE_QUANTILE',
        gates=gates,diagnostic_blocks=results,risk_proxies=risk,static_training_short_scale=static.tolist(),
        scientific_attempts=1,historical_parameter_fits=5,training_rows_per_asset=211,forecast_rows=120,seed=811131,
        future_suffix_forecast_error=prefix_error,elapsed_seconds=time.monotonic()-started,wallets=0,
        source_commit=source,protocol_SHA256=file_sha(HERE/'PROTOCOL.json'),scipy_version=scipy.__version__,
        scope='Alreadyseen historical development, no pristineOOS. Risk/exposure/price/cost proxies are not actualwalletprofit, funding, fills, liquidation or riskmatchedalpha. Outcomes used for diagnosis only, never oracle-as-learned-return. No oldSTOPrefit or post-hocrecipechange.',
        artifacts={p.name:file_sha(p) for p in output.iterdir()}))
    assert time.monotonic()-started<120
    print((output/'RESULT.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    a=p.parse_args();run(a.prepared,a.output,a.source_commit)
