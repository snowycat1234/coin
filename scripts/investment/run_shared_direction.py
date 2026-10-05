"""One fixed shared fit and matched real N-asset perpetual account comparison."""
from __future__ import annotations
import argparse, gc, hashlib, json, os, resource, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import polars as pl
import xgboost
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix
from quant import disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import shared_direction_model as model
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import donchian_daily_pool_target as donchian
from scripts.investment import audit_shared_direction as independent
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.investment.bybit_cost_inputs import snapshot_cost
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')

def stamp(s): return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1_000_000

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for k in ('protocol', 'run-dir', 'output'): parser.add_argument('--'+k, type=Path, required=True)
    parser.add_argument('--resume-input', type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    spec = json.loads(args.protocol.read_bytes())
    run = args.run_dir
    engine.need(os.environ.get('COIN_TASK_ID') and sys.prefix == str(STATE/'v8-clean-env-20261002-v2') and
        pl.thread_pool_size() <= 2 and run.parent == STATE and not run.exists() and not args.output.exists(),
        'Exclusive bounded clean CPU2 run')
    engine.need(sha(ROOT/'state/dataset_lock.json') ==
        '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d', 'Lock SHA only')
    symbols = tuple(spec['symbols'])
    regime_spec=spec.get('regime')
    is_anchor=bool(regime_spec and regime_spec.get('kind')=='FIXED_PAST_TREND')
    reuse_spec=spec.get('direction_model_reuse')
    train_start=stamp(spec['split']['train_decisions_start'])
    train_end=stamp(spec['split']['training_label_maturity_before'])
    val_end=stamp(spec['split']['validation_label_maturity_before'])
    score_start=stamp(spec['split']['economics_start'])
    score_end=stamp(spec['split']['economics_end_exclusive'])
    score_days=(score_end-score_start)//model.DAY
    source_paths = ['scripts/investment/run_shared_direction.py','scripts/investment/shared_direction_model.py',
        'scripts/investment/audit_shared_direction.py','scripts/investment/multi_asset_data.py',
        'scripts/investment/perpetual_directional.py','scripts/investment/perpetual_closing_exempt_account.py',
        'scripts/investment/bybit_cost_inputs.py','src/quant/perpetual_account.py',
        'scripts/investment/public_sma_perpetual.py','scripts/investment/vol_managed_perpetual_target.py',
        'scripts/investment/donchian_daily_pool_target.py']
    if regime_spec: source_paths+=['scripts/investment/market_regime.py']
    binding = dict(task_id=os.environ['COIN_TASK_ID'], protocol_sha256=sha(args.protocol),
        source_hashes={p:sha(ROOT/p) for p in source_paths}, command=[sys.executable, *sys.argv],
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        input_manifest_sha256=sha(spec['data_manifest']['path']), xgboost_version=xgboost.__version__)
    engine.need(binding['input_manifest_sha256'] == spec['data_manifest']['sha256'], 'Accepted input identity')
    run.mkdir(); write(run/'RUN_BINDING.json', binding)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=spec['experiment_id'], event_type='OPERATIONAL_RESEARCH_START',
        event_id=spec['experiment_id']+':'+run.name+':START', git_commit=binding['git_commit'],
        data_manifest_hash=binding['input_manifest_sha256'], protocol_hash=binding['protocol_sha256'],
        feature_set='PAST_DAILY_PRICE_VOLUME_BTC_ETH_BREADTH_ONEHOT_SHARED', labels=spec['labels'],
        model_family='REUSED_XGB_FIXED_PAST_TREND' if is_anchor else 'XGB_FIXED_PLUS_TRAIN_ONLY_GMM' if regime_spec else 'XGBOOST_SHARED_THREE_CLASS',
        hyperparameters=dict(direction=model.MODEL,regime=regime_spec), seed=20261005,
        thresholds='ARGMAX_FIXED_37BP_LABEL_BAND', cost_assumptions='BYBIT_SNAPSHOT_TWO_COSTS_TWO_UNKNOWN_FUNDING_UNITS',
        all_folds=spec['split'], success_failure='START_BEFORE_FIT_OR_ACCOUNT_RESULTS',
        reason_for_next_experiment=spec['question'], result_influenced_later_choice=False,
        direction_fits=0 if args.resume_input or reuse_spec else 1,regime_fits=1 if regime_spec and not is_anchor else 0,
        normalizer_fits=1 if regime_spec and not is_anchor else 0)
    append_event(ROOT/'reports/experiment_registry.jsonl', event)
    progress = Progress(); progress.value['detail'] = '共享三分类方向与真实成本账户对照；已见历史开发筛选'
    began = time.monotonic(); shared_peak = 0
    result = dict(status='FAILED', binding=binding, run_dir=str(run), cases=[], models_fit=0,
        candidate='NONE', investment='CASH', long_term_APR='NOT_EVALUABLE', data_role=spec['data_role'],
        funding_unit_certified=False, orders_sent=0, locked_consumed=False, GPU_hours=0., protocol=spec)
    def guard():
        nonlocal shared_peak
        r = resources.status(); shared_peak = max(shared_peak, r['ram_current_bytes'])
        engine.need(time.monotonic()-began < spec['budget']['wall_seconds'] and
            sum(p.stat().st_size for p in run.rglob('*') if p.is_file()) < spec['budget']['owned_bytes'], 'Finite wall/disk budget')
        engine.need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < spec['budget']['RSS_bytes'], 'Finite RSS budget')
    try:
        progress.update('新磁盘扫描；总量未知', None, None, '扫描')
        result['disk_before'] = dict(disk.check(spec['budget']['owned_bytes']), measured_utc=datetime.now(UTC).isoformat())
        engine.need(result['disk_before']['total_bytes']+spec['budget']['owned_bytes'] < 32_000_000_000, 'Disk warning reserve')
        guard(); progress.update('复用370份已验收来源，核身份并生成日线', None, None, '文件')
        whole = load_portfolio_window(spec['data_manifest']['path'], symbols,
            stamp('2024-09-01'), stamp('2025-07-01'))
        bars = whole['daily']
        features, columns = model.feature_table(bars, symbols)
        labeled = model.label_table(features, bars).filter(pl.all_horizontal([pl.col(f).is_not_null() for f in columns]))
        labeled.write_parquet(run/'shared_dataset.parquet', compression='zstd')
        train = labeled.filter((pl.col('close_us') >= train_start) & (pl.col('label_available_us') < train_end) & pl.col('label').is_not_null())
        validation = labeled.filter((pl.col('close_us') >= train_end) & (pl.col('label_available_us') < val_end) & pl.col('label').is_not_null())
        score = labeled.filter((pl.col('close_us') >= score_start) & (pl.col('close_us') < score_end))
        engine.need(train.height > 1000 and validation.height > 400 and score.height == score_days*len(symbols) and
            set(train['label']) == {0,1,2}, 'Shared matured train/diagnostic/economics split, all classes')
        fit_start = time.monotonic(); progress.update('复用固定方向模型' if reuse_spec or args.resume_input else '共享XGBoost训练，一个配置',0,1,'模型')
        clf = xgboost.XGBClassifier(**model.MODEL)
        if reuse_spec:
            proof=Path(reuse_spec['report_path']); model_path=Path(reuse_spec['path'])
            engine.need(proof.resolve().is_relative_to(ROOT/'reports') and model_path.resolve().is_relative_to(STATE) and
                sha(proof)==reuse_spec['report_sha256'] and sha(model_path)==reuse_spec['sha256'], 'Exact immutable existing direction fit')
            old=json.loads(proof.read_bytes())
            engine.need(old['splits']['fitted_data_cutoff_us']==train_end and old['splits']['maximum_training_label_available_us']<score_start and
                old['splits']['no_validation_early_stopping'] and old['feature_columns']==columns and
                old['binding']['input_manifest_sha256']==binding['input_manifest_sha256'], 'Same matured training, feature order and data; no future fit')
            clf.load_model(model_path)
            result['direction_model_reused']=reuse_spec
        elif args.resume_input:
            previous = args.resume_input.resolve()
            engine.need(previous.parent == STATE and previous != run, 'One exact closed predecessor')
            old = json.loads((ROOT/'reports/fast_research/SHARED_DIRECTION_20261005_V1.json').read_bytes())
            engine.need(old['models_fit'] == 1 and old['run_dir'] == str(previous) and old['binding']['protocol_sha256'] == binding['protocol_sha256'],
                'Resume identical predeclared experiment, preserve previous failure')
            for source in ('shared_direction_model.py','run_shared_direction.py','audit_shared_direction.py'):
                engine.need(sha(previous/'SOURCE_SNAPSHOT'/source) == old['binding']['source_hashes']['scripts/investment/'+source],
                    'Preserved original source bytes')
            for source,digest in old['binding']['source_hashes'].items():
                if source not in ('scripts/investment/shared_direction_model.py','scripts/investment/run_shared_direction.py','scripts/investment/audit_shared_direction.py'):
                    engine.need(sha(ROOT/source) == digest, 'Unchanged prior execution and dataset')
            clf.load_model(previous/'xgb_shared.json')
            result['fit_reused'] = dict(prior_run=str(previous), model_sha256=sha(previous/'xgb_shared.json'),
                actual_models_fit_total=1, original_failure_report='reports/fast_research/SHARED_DIRECTION_20261005_V1.json',
                original_failure_sha256=sha(ROOT/'reports/fast_research/SHARED_DIRECTION_20261005_V1.json'))
        else:
            clf.fit(train.select(columns).to_numpy(), train['label'].to_numpy())
            result['models_fit'] = 1
        result['fit_seconds'] = time.monotonic()-fit_start
        clf.save_model(run/'xgb_shared.json')
        result['feature_columns'] = columns
        result['splits'] = dict(train_rows=train.height, validation_rows=validation.height, score_rows=score.height,
            maximum_training_label_available_us=int(train['label_available_us'].max()),
            fitted_data_cutoff_us=train_end, model_usable_before_economics_us=score_start,
            no_validation_early_stopping=True, no_score_selection=True, normalization='NONE_TREE_MODEL')
        result['classification'] = {}
        for name, frame in [('VALIDATION',validation),('ECONOMICS',score)]:
            prob = clf.predict_proba(frame.select(columns).to_numpy())
            pred = prob.argmax(axis=1)
            pred_frame = frame.select('symbol','close_us','available_us','label','future_price_return').with_columns(
                pl.Series('prediction', pred), *[pl.Series('P_'+label, prob[:,i]) for i,label in enumerate(model.CLASSES)])
            pred_frame.write_parquet(run/(name+'_predictions.parquet'), compression='zstd')
            known = frame['label'].is_not_null().to_numpy(); y = frame.filter(pl.col('label').is_not_null())['label'].to_numpy()
            result['classification'][name] = dict(accuracy=float(accuracy_score(y,pred[known])),
                log_loss=float(log_loss(y,prob[known], labels=[0,1,2])),
                confusion_SHORT_CASH_LONG=confusion_matrix(y,pred[known],labels=[0,1,2]).tolist(),
                predictions={label:int((pred==i).sum()) for i,label in enumerate(model.CLASSES)},
                missing_future_labels=int((~known).sum()), role='DIAGNOSTIC_NOT_ADOPTION_METRIC')
            if name == 'ECONOMICS': predictions = pred_frame
        if args.resume_input:
            old_predictions = pl.read_parquet(previous/'ECONOMICS_predictions.parquet')
            engine.need(predictions.equals(old_predictions), 'Same immutable predictions; no new fit or changed selection')
        if reuse_spec:
            previous_predictions=pl.read_parquet(reuse_spec['golden_predictions_path'])
            engine.need(sha(reuse_spec['golden_predictions_path'])==reuse_spec['golden_predictions_sha256'], 'Original default prediction bytes')
            overlap=predictions.filter((pl.col('close_us')>=previous_predictions['close_us'].min()) &
                (pl.col('close_us')<=previous_predictions['close_us'].max()))
            engine.need(overlap.equals(previous_predictions), 'Golden common-period probabilities/identity/labels unchanged')
            result['default_prediction_golden']='PASS_EXACT_D085_MAY_JUNE_PROBABILITIES_AND_LABELS'
            result['default_target_golden']=[]
            for old_target in reuse_spec.get('golden_targets',[]):
                engine.need(sha(old_target['path'])==old_target['sha256'], 'Original default target bytes')
                original=pl.read_parquet(old_target['path'])
                original_decisions=np.asarray(sorted(original['available_us'].unique()),dtype=np.int64)
                reproduced,_=model.targets(overlap,bars,original_decisions,old_target['mode'],symbols)
                engine.need(reproduced.equals(original), 'Default ordered raw/risk targets unchanged')
                result['default_target_golden'].append(dict(mode=old_target['mode'],rows=original.height,
                    status='PASS_EXACT_ORIGINAL_TARGETS_NO_OLD_ACCOUNT_REPLAY'))
        regime_map=None
        if regime_spec:
            from scripts.investment import market_regime
            if is_anchor:
                engine.need(regime_spec['rule']=='BTC_SMA200_AND_RETURN20_ZERO_BOUNDARY_WITH_PAST_CRASH_OVERRIDE', 'One fixed prior descriptive rule')
                progress.update('固定过去趋势状态；无拟合',0,1,'规则')
                regime_frame=market_regime.rule_states(features,score_start,score_end)
                receipt=dict(kind='FIXED_PAST_TREND',regime_fits=0,normalizer_fits=0,direction_fits=0,
                    future_labels_or_account_results_used=False,rule=regime_spec['rule'],
                    semantics='CURRENT_COMPLETED_PRICE_TREND_NOT_FUTURE_RETURN_TRUTH')
            else:
                engine.need(regime_spec['parameters']==market_regime.PARAMETERS and regime_spec['features']==list(market_regime.FEATURES), 'One declared GMM config')
                progress.update('训练期市场分群，一个固定配置',0,1,'分群')
                regime_frame,receipt,scaler,gmm=market_regime.fit_predict(features,train_start,train_end,score_start,score_end)
                import joblib
                joblib.dump(dict(scaler=scaler,gmm=gmm,receipt=receipt),run/'regime_model.joblib')
            regime_frame.write_parquet(run/'market_regimes.parquet',compression='zstd')
            write(run/'regime_fit.json',receipt); result['regime_fit']=receipt
            regime_map=dict(zip(regime_frame['available_us'],regime_frame['regime'],strict=True))
            result['regime_counts']={label:regime_frame.filter(pl.col('regime')==label).height for label in ('BULL','BEAR','SIDEWAYS','HIGH_VOL_CRASH')}
        window = dict(whole, start=score_start, end=score_end,
            events=[r for r in whole['events'] if score_start <= r['event_us'] < score_end],
            minute_blocks=lambda:whole['minute_blocks'](score_start, score_end))
        decisions = np.arange(window['start'], window['end'], model.DAY, dtype=np.int64)
        # Past-only descriptive strata; this is not the planned learned HMM.
        btc = features.filter(pl.col('symbol')=='BTCUSDT')
        regimes = {r['close_us']:('HIGH_VOL_CRASH' if r['return_1d'] < -.05 and r['vol_30d']*365**.5 > .8 else
            'BULL' if r['ma200_distance'] > 0 and r['return_20d'] > 0 else
            'BEAR' if r['ma200_distance'] < 0 and r['return_20d'] < 0 else 'SIDEWAYS')
            for r in btc.filter(pl.col('close_us')>=score_start).iter_rows(named=True)}
        result['regime_definition'] = 'PAST_BTC_SMA200_AND20D_RETURN_CRASH_1D_LT_MINUS5PCT_VOL30_GT80PCT_DESCRIPTIVE_NOT_HMM'
        if is_anchor:
            control=spec['control_reuse'];path=Path(control['path'])
            engine.need(path.resolve().is_relative_to(ROOT/'reports') and sha(path)==control['sha256'], 'Immutable accepted control report')
            old=json.loads(path.read_bytes())
            engine.need(old['status']=='COMPLETE_FIXED_DIRECTION_REGIME_PAIRED_ECONOMICS_CONDITIONAL_PROXY' and len(old['cases'])==16, '16 completed prior controls')
            for key in ('split','symbols','risk','labels','cost','data_manifest','signal_execution'):
                engine.need(old['protocol'][key]==spec[key], 'Matched control field '+key)
            for source,digest in old['binding']['source_hashes'].items():
                if source not in ('scripts/investment/run_shared_direction.py','scripts/investment/market_regime.py'):
                    engine.need(sha(ROOT/source)==digest,'Unchanged control finance/data/targets '+source)
            old_prediction=Path(old['run_dir'])/'ECONOMICS_predictions.parquet'
            engine.need(sha(old_prediction)==control['prediction_sha256'] and predictions.equals(pl.read_parquet(old_prediction)), 'Exact all122 day probabilities and labels')
            engine.need(regime_map=={k:v for k,v in regimes.items() if k<score_end},'Fixed decision states equal previous descriptive state definition')
            result['control_reuse']=dict(**control,status='REUSED_D086_BY_IMMUTABLE_REPORT_AND_IDENTICAL_INPUTS',
                reused_accounts=16,probability_golden='PASS_EXACT_1220_ROWS',new_accounts=4)
        strategies = [('XGB_LONG_SHORT','LONG_SHORT'),('XGB_LONG_ONLY','LONG_ONLY'),
            ('XGB_SHORT_ONLY','SHORT_ONLY'),('HOLD','LONG_ONLY'),('DONCHIAN_EXIT10','LONG_ONLY')]
        if regime_spec:
            strategies=[('XGB_LONG_SHORT','LONG_SHORT'),('XGB_REGIME_GATED','LONG_SHORT'),('HOLD','LONG_ONLY'),('DONCHIAN_EXIT10','LONG_ONLY')]
        if is_anchor: strategies=[('XGB_TREND_GATED','LONG_SHORT')]
        result['required_accounts'] = len(strategies)*4
        for name, mode in strategies:
            if name == 'HOLD': factory=lambda b,d,m:hold.fixed_targets(b,d,m,symbols=symbols)
            elif name == 'DONCHIAN_EXIT10': factory=lambda b,d,m:donchian.fixed_targets(b,d,m,symbols=symbols,exit_period=10)
            else: factory=lambda b,d,m:model.targets(predictions,b,d,m,symbols,
                regimes=regime_map if name in ('XGB_REGIME_GATED','XGB_TREND_GATED') else None)
            for cost_legacy in engine.COSTS:
                cost = snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json', symbols=symbols,
                    fee_zone_by_symbol={s:'DERIVATIVES_CRYPTO_STANDARD' for s in symbols}, scenario_id=cost_legacy['id'],
                    half_spread_bps=cost_legacy['half_spread_bps'], slippage_bps=cost_legacy['slippage_bps'],
                    execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY', execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
                for unit in engine.UNITS:
                    guard(); case_id=name+'_'+cost['id']+'_'+unit['id']; started=time.monotonic()
                    progress.update('真实共享10币账户对照',len(result['cases']),result['required_accounts'],'账户',strategy=name)
                    case_dir=run/case_id
                    actual=None
                    if args.resume_input and not result['cases']:
                        case_dir=previous/case_id
                        saved=dict(summary=json.loads((case_dir/'summary.json').read_bytes()),
                            artifacts={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
                                for p in case_dir.iterdir() if p.is_file()})
                    else:
                        actual=engine.simulate(window,mode,cost,unit,progress,guard,target_factory=factory,
                            account_factory=USDTLinearPerpetualAccount)
                        saved=engine.save_case(actual,case_dir)
                        write(case_dir/'summary.json', saved['summary'])
                    engine.need(saved['summary']['completed_minutes']==score_days*1440, 'Complete marked calendar; residual never deleted')
                    checked=independent.verify(case_dir,symbols,unit['scale'])
                    if name.startswith('XGB'):
                        checked['target_reference']=independent.verify_direction_targets(
                            pl.read_parquet(case_dir/'targets.parquet'),predictions,bars,symbols,mode,
                            regimes=regime_map if name in ('XGB_REGIME_GATED','XGB_TREND_GATED') else None)
                    by_regime={}
                    for day in checked['daily_direction_contributions']:
                        regime=regimes[day['day_end_us']-model.DAY]
                        r=by_regime.setdefault(regime,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        r['days']+=1
                        for k in ('LONG','SHORT','CASH'): r[k]+=day[k]
                        r['net']+=day['LONG']+day['SHORT']
                    checked['by_past_regime']=by_regime
                    if regime_map:
                        grouped={}
                        for day in checked['daily_direction_contributions']:
                            label=regime_map[day['day_end_us']-model.DAY]
                            v=grouped.setdefault(label,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                            v['days']+=1
                            for k in ('LONG','SHORT','CASH'): v[k]+=day[k]
                            v['net']+=day['LONG']+day['SHORT']
                        checked['by_learned_regime']=grouped
                    write(run/(case_id+'_independent.json'),checked)
                    result['cases'].append(dict(id=case_id,strategy=name,cost_id=cost['id'],unit_id=unit['id'],
                        elapsed_seconds=time.monotonic()-started,**saved, independent=checked,
                        account_reused_from_closed_predecessor=case_dir.parent!=run))
                    write(run/'CHECKPOINT.json',result); del actual; gc.collect(); guard()
        result['cash_benchmark'] = dict(initial_capital_USDT=10000, net_PnL=0, costs=0, volatility=0, drawdown=0,
            role='ANALYTIC_FLAT_ACCOUNT_NOT_A_FAKE_REPLAY')
        result['status']=('COMPLETE_FIXED_PAST_TREND_GATE_NEW4_REUSED16_CONDITIONAL_PROXY' if is_anchor else 'COMPLETE_FIXED_DIRECTION_REGIME_PAIRED_ECONOMICS_CONDITIONAL_PROXY' if regime_spec else
            'COMPLETE_ONE_SHARED_FIT_MATCHED_DIRECTION_AND_RULE_ECONOMICS_CONDITIONAL_PROXY')
    except Exception as e:
        result.update(error_type=type(e).__name__,reason=str(e)); raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-began, shared_RAM_sampled_peak_bytes=shared_peak,
            resources_after=resources.status(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(args.output,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_type='OPERATIONAL_RESEARCH_RESULT',
            event_id=spec['experiment_id']+':'+run.name+':RESULT',success_failure=result['status'],
            artifact_path=str(args.output.relative_to(ROOT)),artifact_sha256=sha(args.output)))
        progress.stop.set(); progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],accounts=len(result['cases']),models_fit=result['models_fit'],output=str(args.output))))

if __name__ == '__main__': main()
