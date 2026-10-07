"""Finite market/feedback information ablation; reference utilities, not wallets.

Reuses mature public intent/risk and the daily quantity kernel. No new trading
engine, neural network, hyperparameter search or API/LLM calls in this runner.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import polars as pl
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import sklearn

from modules.collector_research.pipeline.economics import interval_arrays, proxy_step
from scripts.investment.public_sma_perpetual import signed_risk_weights
from scripts.research.calibrate_expert_following import label_available_at
from scripts.research.public_cross_section_momentum import DAY_US, WEEK_US, public_targets
from scripts.research.run_public_momentum import ROOT, save, sha

EXPERTS = ('SMA200_SIGNED', 'CSMOM21_CORE5', 'HOLD', 'CASH')
FEATURES = ('mom20', 'mom60', 'mom200', 'dist50', 'dist200', 'vol30', 'range', 'vol_z')
INPUTS = ('FEEDBACK', 'MARKET_INTENT', 'COMBINED')


def reference_available_at(decision_us):
    # Endpoint open comes from a completed1m source bar. Conservatively wait
    # for that bar's close as well as the execution-boundary event.
    source_bar_close = int(decision_us) + 7*DAY_US + 120_000_000
    return max(label_available_at(int(decision_us), 7), source_bar_close+1)


def feedback_panel(decisions, label_available, utilities, anchor_us, windows=(1, 4, 12)):
    """Consume complete fixed weekly slots only after their outcomes mature.

    Missing slots remain missing; never compress a gapped history to '12 weeks'.
    Utilities are realised reference performance, not fitted residual memory.
    """
    d = np.asarray(decisions, dtype=np.int64)
    av = np.asarray(label_available, dtype=np.int64)
    u = np.asarray(utilities, dtype=float)
    if av.shape != d.shape or u.shape != (len(d), len(EXPERTS)) or np.any(np.diff(d) != DAY_US) or np.any(np.diff(av) <= 0):
        raise ValueError('Common daily clock and ordered expert utility matrix required')
    slots = np.flatnonzero((d - anchor_us) % WEEK_US == 0)
    output = np.full((len(d), len(EXPERTS)*len(windows)), np.nan)
    last_source = np.full(len(d), -1, dtype=np.int64)
    for i, decision in enumerate(d):
        count = int(np.searchsorted(av[slots], decision, side='right'))
        if count < max(windows):
            continue
        selected = slots[count-max(windows):count]
        if np.any(np.diff(d[selected]) != WEEK_US) or not np.isfinite(u[selected]).all():
            continue
        output[i] = np.concatenate([u[slots[count-w:count]].mean(axis=0) for w in windows])
        last_source[i] = av[slots[count-1]]
    return output, last_source


def train_mask(decisions, label_available, complete, validation_start, embargo_days):
    # Full label purge PLUS the registered embargo, not a row-count shift.
    cutoff = int(validation_start)-embargo_days*DAY_US
    return np.asarray(complete, bool) & (np.asarray(decisions) < validation_start) & (np.asarray(label_available) < cutoff)


def signed_intents(close, sma, available, core_columns):
    """Frozen SMA200/HOLD direction, existing 10% past covariance sizing."""
    n, assets = close.shape
    out = np.zeros((n, len(EXPERTS), assets), dtype=np.float64)
    csmom, _ = public_targets(close, available, available, list(core_columns), list(core_columns))
    out[:, 1] = csmom
    for i in range(199, n):
        history = close[i-199:i+1]
        good = np.all(np.isfinite(history) & (history > 0), axis=0) & np.isfinite(sma[i])
        columns = np.flatnonzero(good)
        if not len(columns):
            continue
        last = close[i-30:i+1, columns]
        r = np.diff(last, axis=0)/last[:-1]
        base = .6/len(columns)
        for e, direction in ((0, sma[i, columns]), (2, np.ones(len(columns)))):
            out[i, e, columns], _ = signed_risk_weights(base*direction, r, annual_vol_target=.10)
    return out


def reference_labels(weights, arrays, side_cost, capital, horizon_days=7, on_rows=None):
    """Zero-entry, daily-follow, execution-price boundary value; no forced exit.

    No claim of observed-mark, current-position or native margin equivalence.
    Unknown held data invalidates the label instead of filling funding/returns.
    """
    p0, p1, fund, valid = arrays
    n, experts, assets = weights.shape
    labels = np.full((n, experts), np.nan)
    labels[:, 3] = 0.
    reasons = {}
    for i in range(len(p0)-horizon_days+1):
        for e in range(experts-1):
            nav, q = float(capital), np.zeros(assets)
            try:
                for j in range(i, i+horizon_days):
                    nav, q, *_ = proxy_step(nav, q, weights[j, e], p0[j], p1[j], fund[j], valid[j], side_cost)
                labels[i, e] = nav/capital-1
            except ValueError as exc:
                reasons[str(exc)] = reasons.get(str(exc), 0)+1
        if on_rows is not None and (i % 100 == 0 or i == len(p0)-horizon_days):
            on_rows(i+1, len(p0)-horizon_days+1)
    return labels, reasons


def same_switch_random(choices, seed):
    """Diagnostic random expert with the model's exact switch boundaries.

    The boundaries come from the evaluated prediction sequence; this is a
    matched negative control, not a separately feasible trading strategy.
    """
    rng = np.random.default_rng(seed)
    result = np.empty(len(choices), dtype=int)
    result[0] = rng.integers(len(EXPERTS))
    for i in range(1, len(choices)):
        if choices[i] != choices[i-1]:
            result[i] = rng.choice([e for e in range(len(EXPERTS)) if e != result[i-1]])
        else:
            result[i] = result[i-1]
    return result


def prediction_metrics(actual, predicted):
    choice = np.argmax(predicted, axis=1)
    realised = actual[np.arange(len(actual)), choice]
    ceiling = actual.max(axis=1)
    centered_actual = actual-actual.mean(axis=1, keepdims=True)
    centered_pred = predicted-predicted.mean(axis=1, keepdims=True)
    return dict(samples=len(actual), mean_chosen_reference_utility=float(realised.mean()),
        mean_top_choice_regret=float((ceiling-realised).mean()), winner_accuracy=float(np.mean(choice==actual.argmax(axis=1))),
        centered_RMSE=float(np.sqrt(np.mean((centered_actual-centered_pred)**2))),
        raw_RMSE=float(np.sqrt(np.mean((actual-predicted)**2))),
        switches=int(np.count_nonzero(np.diff(choice))), choices=choice.tolist())


def research_decision(gates, joint_increment):
    if gates['COMBINED'] and joint_increment:
        return 'REGISTER_NATIVE_CANDIDATE_NEXT'
    if any(gates[k] for k in INPUTS[:-1]):
        return 'RETAIN_SIMPLER_INFORMATION_CANDIDATE'
    return 'PAUSE_EXACT_RIDGE_INFORMATION_RECIPE'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    assert p['budget']['main_fits']==12 and p['budget']['placebo_fits']==12 and p['budget']['new_wallets']==0
    assert p['horizon_days']==7 and p['ridge_alpha']==10 and p['features']==list(FEATURES) and p['experts']==list(EXPERTS)
    assert p['inputs']==list(INPUTS) and p['funding_scales']==[1,.01]
    for path in [Path(__file__),a.protocol,ROOT/'scripts/research/calibrate_expert_following.py',ROOT/'scripts/research/public_cross_section_momentum.py',ROOT/'modules/collector_research/pipeline/economics.py']:
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+str(path.resolve().relative_to(ROOT))])).hexdigest()==sha(path)
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8_000_000_000 and (group/'memory.swap.max').read_text().strip()=='0'
    state.mkdir(exist_ok=True);assert not (state/'RESULTS.json').exists(),'Use completed results, do not refit a completed experiment'
    assert not (state/'STARTED.json').exists(),'Inspect partial run before authorising a new attempt; no silent duplicate fits'
    assert shutil.disk_usage(state).free>=p['budget']['reserve_bytes']
    save(state/'STARTED.json',dict(protocol_sha256=sha(a.protocol),source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(),started_at=time.time()))
    completed=0;total=29
    def progress(stage,detail,**extra):
        save(state/'progress.json',dict(status='running',stage=stage,phase=stage,completed=completed,total=total,unit='任务',detail=detail,
            elapsed_seconds=time.monotonic()-began,updated_at=time.time(),pid=os.getpid(),**extra))
        print(f'[{stage}] {completed}/{total} {detail}',flush=True)
    progress('DATA','verify bound explicit past columns; no u/y or locked data')
    parent_path=ROOT/p['parent_protocol'];assert sha(parent_path)==p['parent_protocol_sha256'];parent=json.loads(parent_path.read_text())
    work=Path(parent['work']);manifest=work/'reports/DATASET_MANIFEST.json';lm=work/'data/labels/raw_fraction/LABEL_MANIFEST.json'
    assert sha(manifest)==parent['data_manifest_sha256']==p['data_manifest_sha256'] and sha(lm)==parent['label_manifest_sha256']
    files=json.loads(lm.read_text())['files'];registered={x['symbol']:x for x in files}
    assert [x['symbol'] for x in files]==parent['symbols']
    admitted={str((Path(x['path']) if 'path' in x else work/x['relative_path']).absolute()):x['sha256'] for x in json.loads(manifest.read_text())['artifacts']}
    frames=[];daily={};input_refs=[];available=None;cutoff=max(w['end'] for w in p['windows'])
    columns=['dt','symbol','close','decision_available_at','sma_signal',*FEATURES]
    for s in p['core_symbols']:
        path=Path(registered[s]['path']).resolve();assert path.parent==lm.parent.resolve() and sha(path)==registered[s]['sha256']
        # Read only declared past columns, then the registered prelocked extent.
        f=pl.read_parquet(path,columns=columns).sort('dt')
        full_dt=f['dt'].dt.epoch('us').to_numpy();assert full_dt.max()<parent['locked_start_us']
        f=f.filter(pl.col('decision_available_at').dt.epoch('us')<=cutoff)
        av=f['decision_available_at'].dt.epoch('us').to_numpy();dt=f['dt'].dt.epoch('us').to_numpy()
        assert np.all(av==dt+DAY_US) and np.all(np.diff(av)==DAY_US) and f['symbol'].eq(s).all()
        if available is None:available=av
        else:assert np.array_equal(available,av)
        frames.append(f)
        norm=work/'data/normalized'/(s+'_daily.parquet');assert sha(norm)==admitted[str(norm)]
        g=pl.read_parquet(norm,columns=['dt','exec_price','mark_funding_per_unit','funding_interval_complete','complete_kline']).sort('dt')
        assert g['dt'].dt.epoch('us').max()<parent['locked_start_us']
        g=g.filter(pl.col('dt').dt.epoch('us')<=int(dt[-1]))
        assert np.array_equal(g['dt'].dt.epoch('us').to_numpy(),dt)
        daily[s]=g.to_pandas();input_refs.append(dict(symbol=s,past_path=str(path),past_sha256=sha(path),daily_path=str(norm),daily_sha256=sha(norm)))
    completed+=1;progress('FEATURES','same CORE5 dates and symbol order, past-only risk intent')
    close=np.column_stack([f['close'].to_numpy() for f in frames]);sma=np.column_stack([f['sma_signal'].to_numpy() for f in frames])
    weights=signed_intents(close,sma,available,p['core_symbols'])
    assert np.isfinite(weights).all() and np.max(np.abs(weights))<=.3+1e-9 and np.max(np.abs(weights).sum(axis=2))<=.6+1e-9
    # Golden check the existing CORE5 frozen intent, not the different6coin pool.
    legacy=ROOT/p['core5_result'];assert sha(legacy)==p['core5_result_sha256']
    old=json.loads(legacy.read_text())['cases'][0];case=json.loads(Path(old['result_path']).read_text());assert sha(old['result_path'])==old['result_sha256']
    assert sha(case['task']['target_path'])==case['task']['target_sha256']
    with np.load(case['task']['target_path'],allow_pickle=False) as f:
        assert f['symbol_order'].tolist()==parent['symbols']
        ids=np.searchsorted(available,f['decision_us']);cols=[parent['symbols'].index(s) for s in p['core_symbols']]
        assert np.array_equal(available[ids],f['decision_us']) and np.array_equal(weights[ids,1],f['weights'][:,cols])
    feature_cube=np.stack([f.select(list(FEATURES)).to_numpy() for f in frames],axis=1)
    valid_market=np.isfinite(feature_cube).all(axis=(1,2))
    btc=p['core_symbols'].index('BTCUSDT')
    market=np.column_stack([feature_cube[:,btc],feature_cube.mean(axis=1),
        np.mean(feature_cube[:,:,0]>0,axis=1),np.mean(feature_cube[:,:,2]>0,axis=1),
        np.abs(weights).sum(axis=2),weights.sum(axis=2),np.abs(np.minimum(weights,0)).sum(axis=2)])
    market[~valid_market]=np.nan
    maturity=np.array([reference_available_at(d) for d in available],dtype=np.int64)
    np.savez_compressed(state/'PAST_INTENTS.npz',decision_us=available,weights=weights,symbol_order=np.array(p['core_symbols']),experts=np.array(EXPERTS),market=market)
    completed+=1
    rows=[];predictions=[];actual_fits=0
    for scale in p['funding_scales']:
        arrays_by_asset=[interval_arrays(f,np.arange(len(f)-2),scale) for f in daily.values()]
        arrays=tuple(np.stack([x[k] for x in arrays_by_asset],axis=1) for k in range(4))
        labels,reasons=reference_labels(weights,arrays,p['side_cost'],p['capital'],7,
            lambda done,count:progress('LABELS',f'funding={scale} reference blocks {done}/{count}',label_rows=done,total_label_rows=count))
        feedback,last_source=feedback_panel(available,maturity,labels,p['anchor_us'])
        common=np.isfinite(market).all(1)&np.isfinite(feedback).all(1)
        assert np.all(last_source[common]<=available[common])
        complete=common&np.isfinite(labels).all(1)
        features=dict(FEEDBACK=feedback,MARKET_INTENT=market,COMBINED=np.column_stack([market,feedback]))
        np.savez_compressed(state/f'REFERENCE_PANEL_{scale}.npz',decision_us=available,label_available_us=maturity,labels=labels,feedback=feedback,feedback_last_available_us=last_source,common=common)
        completed+=1
        for window in p['windows']:
            eligible=(available>=window['start'])&(maturity<window['end'])&((available-p['anchor_us'])%WEEK_US==0)
            val=np.flatnonzero(eligible)
            assert len(val)>=20 and np.all(complete[val]),'Registered weekly validation cannot delete missing dates'
            train=np.flatnonzero(train_mask(available,maturity,complete,window['start'],p['embargo_days']))
            assert len(train)>=p['minimum_train_daily_rows'] and np.all(maturity[train]<window['start']-p['embargo_days']*DAY_US)
            ytrain=labels[train];actual=labels[val]
            train_constant=np.broadcast_to(ytrain.mean(0),actual.shape).copy();train_constant[:,3]=0.
            static=prediction_metrics(actual,train_constant)
            best_single=float(np.max(actual.mean(0)));oracle=float(actual.max(1).mean());gap=oracle-best_single
            past_choices=[]
            slots=np.flatnonzero((available-p['anchor_us'])%WEEK_US==0)
            for v in val:
                past=slots[(maturity[slots]<=available[v])&np.isfinite(labels[slots]).all(1)]
                assert len(past)>0
                past_choices.append(int(np.argmax(labels[past].mean(0))))
            past_value=float(actual[np.arange(len(val)),past_choices].mean())
            baseline=dict(train_mean=static,best_validation_single_reference=best_single,best_validation_expert=EXPERTS[int(np.argmax(actual.mean(0)))],
                single_means=dict(zip(EXPERTS,actual.mean(0).tolist())),oracle_reference=oracle,oracle_gap=gap,expanding_past_winner_reference=past_value,
                training_daily_rows=len(train),training_span_us=[int(available[train[0]]),int(available[train[-1]])],validation_week_blocks=len(val),
                validation_decision_us=available[val].tolist(),max_train_label_available_us=int(maturity[train].max()),
                max_validation_label_available_us=int(maturity[val].max()),invalid_label_reasons=reasons)
            for kind in INPUTS:
                x=features[kind];pipeline=make_pipeline(StandardScaler(),Ridge(alpha=p['ridge_alpha']))
                pipeline.fit(x[train],ytrain);actual_fits+=1
                pred=pipeline.predict(x[val]);pred[:,3]=0.
                train_pred=pipeline.predict(x[train]);train_pred[:,3]=0.
                met=prediction_metrics(actual,pred);choices=np.array(met['choices'])
                random=same_switch_random(choices,p['random_seed']);assert np.count_nonzero(np.diff(random))==met['switches']
                random_value=float(actual[np.arange(len(val)),random].mean())
                completed+=1;progress('MODEL',f'{actual_fits}/24 fits: {window["id"]} funding={scale} {kind}')
                shifted=make_pipeline(StandardScaler(),Ridge(alpha=p['ridge_alpha']))
                shift=max(1,len(train)//2);shifted.fit(x[train],np.roll(ytrain,shift,axis=0));actual_fits+=1
                placebo=shifted.predict(x[val]);placebo[:,3]=0.
                pm=prediction_metrics(actual,placebo)
                value=met['mean_chosen_reference_utility']
                row=dict(window=window['id'],funding_scale=scale,input=kind,baseline=baseline,metrics=met,
                    train_metrics=prediction_metrics(ytrain,train_pred),shifted_label_placebo=pm,placebo_train_shift_rows=shift,
                    same_switch_random_reference=random_value,capture_vs_best_single=(value-best_single)/gap if gap>0 else None,
                    gap_vs_best_single=value-best_single,gap_vs_train_mean=value-static['mean_chosen_reference_utility'],gap_vs_past_winner=value-past_value,
                    gap_vs_shifted_placebo=value-pm['mean_chosen_reference_utility'],gap_vs_same_switch_random=value-random_value,
                    scaler_train_only=True,feature_count=x.shape[1],scaled_coefficients=pipeline[-1].coef_.tolist(),
                    max_abs_validation_train_z=float(np.max(np.abs(pipeline[0].transform(x[val])))))
                rows.append(row)
                predictions.append(dict(window=window['id'],funding_scale=scale,input=kind,decision_us=available[val].tolist(),
                    label_available_us=maturity[val].tolist(),feedback_source_available_us=last_source[val].tolist(),
                    predicted_reference_utility=pred.tolist(),actual_reference_utility=actual.tolist(),shifted_predictions=placebo.tolist(),
                    same_switch_random_choices=random.tolist()))
                completed+=1;progress('PLACEBO',f'{actual_fits}/24 fits: fixed train-vector half-cycle shift')
    assert actual_fits==24 and completed==28
    def eligible(row):
        return (row['gap_vs_best_single']>=p['minimum_reference_gap'] and row['capture_vs_best_single'] is not None and row['capture_vs_best_single']>=p['minimum_capture']
            and row['gap_vs_train_mean']>0 and row['gap_vs_past_winner']>0 and row['gap_vs_shifted_placebo']>0 and row['gap_vs_same_switch_random']>0)
    family_gates={kind:all(eligible(r) for r in rows if r['input']==kind) for kind in INPUTS}
    joint_increment=all(next(r for r in rows if r['window']==w['id'] and r['funding_scale']==s and r['input']=='COMBINED')['metrics']['mean_chosen_reference_utility']>
                        max(r['metrics']['mean_chosen_reference_utility'] for r in rows if r['window']==w['id'] and r['funding_scale']==s and r['input']!='COMBINED')
                        for w in p['windows'] for s in p['funding_scales'])
    decision=research_decision(family_gates,joint_increment)
    owned=sum(f.stat().st_size for f in state.rglob('*') if f.is_file())
    assert owned<=p['budget']['new_owned_bytes'] and time.monotonic()-began<=p['budget']['wall_seconds']
    result=dict(status='COMPLETE_REFERENCE_INFORMATION_SCREEN',source_commit=json.loads((state/'STARTED.json').read_text())['source_commit'],
        protocol=p,protocol_sha256=sha(a.protocol),input_refs=input_refs,cases=rows,family_gates=family_gates,joint_increment_all4=joint_increment,
        decision=decision,actual_main_fits=12,actual_placebo_fits=12,new_wallets=0,qualification='NONE_CASH',locked_consumed=False,
        sklearn_version=sklearn.__version__,elapsed_seconds=time.monotonic()-began,owned_bytes=owned,
        RAM_limit=(group/'memory.max').read_text().strip(),swap_limit=(group/'memory.swap.max').read_text().strip(),GPU=0,
        RAM_group_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,
        limitations=p['limitations'])
    save(state/'PREDICTIONS.json',predictions);save(state/'RESULTS.json',result)
    report=['# 联合市场与成熟反馈：固定Ridge信息筛选','',f'决定：{decision}；投资NONE/CASH。12主fit＋12负对照fit，零新钱包。',
        '', '|已见窗口|资金解释|输入|选择参考效用bp/周|比最佳单expert差bp|比过去赢家差bp|Oracle gap capture|错位负对照bp|',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for r in rows:
        capture=f'{r["capture_vs_best_single"]:.2%}' if r['capture_vs_best_single'] is not None else 'N/E'
        report.append(f'|{r["window"]}|{r["funding_scale"]}|{r["input"]}|{r["metrics"]["mean_chosen_reference_utility"]*1e4:.3f}|{r["gap_vs_best_single"]*1e4:.3f}|{r["gap_vs_past_winner"]*1e4:.3f}|{capture}|{r["shifted_label_placebo"]["mean_chosen_reference_utility"]*1e4:.3f}|')
    report+=['','这是零入场7日follow、执行价格端点估值、扣entry/internal turnover/funding但不强制退出的reference utility，不是共享钱包净PnL/APR。',
        '所有资金解释都是同一市场路径的条件情景，不增加独立样本。验证周块不重叠；train日标签重叠，不把每日行数当独立样本。',
        '一次错位/匹配频率random仅负对照，不支持placebo95%或显著性。CASH reference0不等于实际已有仓位能免费清仓。',
        '',*p['limitations'],'','复现：python -B scripts/research/joint_expert_information.py --protocol protocols/JOINT_EXPERT_INFORMATION_20261008.json --state /home/ubuntu/coin/execution-state/joint-information-NEW，须8GB/swap0/GPU0受限scope；完成/部分启动state不会自动重拟合。']
    (state/'REPORT.md').write_text('\n'.join(report)+'\n');completed+=1
    save(state/'progress.json',dict(status='completed',stage='REPORT',phase='信息筛选完成',completed=completed,total=total,unit='任务',
        elapsed_seconds=result['elapsed_seconds'],updated_at=time.time(),detail=decision))
    print(json.dumps(dict(status=result['status'],family_gates=family_gates,joint_increment_all4=joint_increment,decision=decision)),flush=True)


if __name__=='__main__':main()
