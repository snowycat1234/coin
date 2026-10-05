"""One shared meta fit; fixed public intent, fresh common economic accounts."""
import argparse,gc,hashlib,json,os,resource,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
import numpy as np
import polars as pl
import xgboost
from quant import disk,resources
from quant.paths import ROOT,STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import shared_signal_meta as meta
from scripts.investment import shared_direction_model as common
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import audit_shared_direction as audit
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.investment.bybit_cost_inputs import snapshot_cost
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS,append_event

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
    Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1_000_000

def main():
    ap=argparse.ArgumentParser()
    for k in ('protocol','run-dir','output'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--recovery-binding',type=Path)
    a=ap.parse_args();spec=json.loads(a.protocol.read_bytes());run=a.run_dir.resolve();out=a.output.resolve()
    engine.need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and
        pl.thread_pool_size()<=2 and run.parent==STATE and not run.exists() and
        out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(),'Bounded fresh CPU2 D paths')
    engine.need(sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d','Lock SHA only')
    engine.need(spec['model']==meta.MODEL and spec['threshold']==.5 and spec['label_band_bps']==37 and
        spec['fit_cutoff']=='2025-03-01' and spec['economics_start']=='2025-03-01' and spec['economics_end']=='2025-07-01',
        'Single declared fixed mature fit and paired development window')
    import xml.etree.ElementTree as ET
    test=spec['regression'];engine.need(sha(ROOT/test['path'])==test['sha256'] and
        sha(ROOT/'tests/test_shared_signal_meta.py')==test['source_sha256'],'Actual related regression bytes')
    counts=[(int(s.get('tests',0)),int(s.get('failures',0))+int(s.get('errors',0)))
        for s in ET.parse(ROOT/test['path']).getroot().iter('testsuite')]
    engine.need(sum(c[0] for c in counts)==2 and not any(c[1] for c in counts),'Two causal regressions passed')
    source_paths=['scripts/investment/'+p for p in ('run_shared_meta.py','shared_signal_meta.py','shared_direction_model.py',
        'public_sma_daily.py','public_sma_perpetual.py','multi_asset_data.py','perpetual_directional.py',
        'perpetual_closing_exempt_account.py','bybit_cost_inputs.py','audit_shared_direction.py','vol_managed_perpetual_target.py')]
    source_paths+=['src/quant/perpetual_account.py','tests/test_shared_signal_meta.py',
        'third_party/jesse_example_smacrossover/smacrossover_original.py','third_party/jesse_example_smacrossover/LICENSE']
    manifest=spec['data_manifest'];engine.need(sha(manifest['path'])==manifest['sha256'],'Accepted input identity')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={p:sha(ROOT/p) for p in source_paths},protocol_sha256=sha(a.protocol),input_manifest_sha256=manifest['sha256'],
        command=[sys.executable,*sys.argv],xgboost_version=xgboost.__version__)
    run.mkdir();write(run/'RUN_BINDING.json',binding)
    recovery=None;prior=None;previous=None
    if a.recovery_binding:
        recovery=json.loads(a.recovery_binding.read_bytes());previous=Path(recovery['previous_run'])
        engine.need(previous.parent==STATE and previous!=run and sha(recovery['failed_report'])==recovery['failed_report_sha256'],
            'Closed failed predecessor and retained evidence')
        prior=json.loads(Path(recovery['failed_report']).read_bytes())
        engine.need(prior['status']=='FAILED' and prior['models_fit']+prior.get('fit_reused',{}).get('actual_fits_total',0)==1 and
            prior['binding']['protocol_sha256']==binding['protocol_sha256'],'Same fixed fit/protocol; recovery is evidence-scope correction')
        for p,h in prior['binding']['source_hashes'].items():
            if p not in ('scripts/investment/run_shared_meta.py','scripts/investment/audit_shared_direction.py'):
                engine.need(sha(ROOT/p)==h,'Unchanged recovery model/data/finance '+p)
        for p,h in recovery['observed_artifact_hashes'].items():engine.need(sha(p)==h,'Observed retained fit/account bytes')
        stop_test=recovery['stopped_audit_regression']
        engine.need(sha(ROOT/stop_test['path'])==stop_test['sha256'] and
            sha(ROOT/'tests/test_stopped_account_audit.py')==stop_test['test_source_sha256'] and
            sha(ROOT/'scripts/investment/audit_shared_direction.py')==stop_test['audit_source_sha256'],
            'Stopped reference behavior regression and source identity')
        counts=[(int(s.get('tests',0)),int(s.get('failures',0))+int(s.get('errors',0)))
            for s in ET.parse(ROOT/stop_test['path']).getroot().iter('testsuite')]
        engine.need(sum(c[0] for c in counts)==1 and not any(c[1] for c in counts),'Stopped and full calendar reference regression passed')
    event=dict.fromkeys(FIELDS);event.update(experiment_id=spec['experiment_id'],event_id=spec['experiment_id']+':'+run.name+':START',
        event_type='OPERATIONAL_RESEARCH_START',git_commit=binding['git_commit'],data_manifest_hash=manifest['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set=spec['features'],labels=spec['labels'],model_family='PUBLIC_SMA_INTENT_SHARED_XGB_META',hyperparameters=spec['model'],
        seed=20261005,thresholds='FIXED_P_EXECUTE_GT0.5',cost_assumptions=spec['cost'],all_folds=spec['split'],
        success_failure='START_BEFORE_FIT_OR_ECONOMIC_ACCOUNT',reason_for_next_experiment=spec['question'],result_influenced_later_choice=False,
        new_fits=0 if recovery else 1)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    progress=Progress();started=time.monotonic();shared_peak=0;result=dict(status='FAILED',binding=binding,protocol=spec,
        run_dir=str(run),cases=[],required_accounts=12,models_fit=0,GPU_hours=0.,candidate='NONE/CASH',locked_consumed=False,orders_sent=0)
    def guard():
        nonlocal shared_peak
        shared_peak=max(shared_peak,resources.status()['ram_current_bytes'])
        engine.need(time.monotonic()-started<spec['budget']['wall_seconds'] and
            sum(p.stat().st_size for p in run.rglob('*') if p.is_file())<spec['budget']['owned_bytes'] and
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes'],'Finite actual fit/accounts budget')
    try:
        progress.update('磁盘实扫；总量未知',None,None,'扫描')
        result['disk_before']=dict(disk.check(spec['budget']['owned_bytes']),measured_utc=datetime.now(UTC).isoformat())
        symbols=tuple(spec['symbols']);start=stamp('2024-09-01');cutoff=stamp(spec['fit_cutoff']);end=stamp(spec['economics_end'])
        progress.update('复用已接受来源与公共日线特征',None,None,'文件')
        whole=load_portfolio_window(manifest['path'],symbols,start,end);bars=whole['daily']
        features,columns=common.feature_table(bars,symbols);columns+=['signal_direction']
        public_targets,intents,public_receipt=meta.public_intents(bars,symbols,start,end)
        result['public_intent_reference']=meta.verify_public_intents(bars,intents,symbols,start,end)
        result['public_adapter']=public_receipt
        table=meta.meta_table(features,bars,intents)
        table.write_parquet(run/'shared_meta_dataset.parquet',compression='zstd')
        train=meta.matured_train(table,columns,start,cutoff)
        score=table.filter((pl.col('close_us')>=cutoff)&(pl.col('close_us')<end)).sort(['close_us','symbol'])
        engine.need(train.height>1000 and set(train['execute_label'])=={0,1} and score.height==122*len(symbols) and
            score.select(columns).null_count().select(pl.sum_horizontal(pl.all())).item()==0,'Mature shared train and complete common score')
        result['split_evidence']=dict(train_rows=train.height,score_rows=score.height,
            maximum_training_label_available_us=int(train['label_available_us'].max()),fit_cutoff_us=cutoff,
            primary_signal_fits=0,probabilities_from_primary_model_used=False,all_symbols_common_cutoff=True,
            score_role='ALREADY_SEEN_DEVELOPMENT_OUT_OF_FIT_NOT_UNSEEN',feature_columns=columns)
        progress.update('一个共享execute/reject模型拟合',0,1,'模型')
        fit=time.monotonic();clf=xgboost.XGBClassifier(**meta.MODEL)
        if recovery:
            engine.need(result['split_evidence']==prior['split_evidence'],'Exact maturity/features/rows on recovery')
            clf.load_model(previous/'shared_meta_xgb.json')
            result['fit_reused']=dict(binding=str(a.recovery_binding),binding_sha256=sha(a.recovery_binding),
                previous_run=str(previous),actual_fits_total=1)
        else:
            clf.fit(train.select(columns).to_numpy(),train['execute_label'].to_numpy());result['models_fit']=1
        result['fit_seconds']=time.monotonic()-fit;clf.save_model(run/'shared_meta_xgb.json')
        p=clf.predict_proba(score.select(columns).to_numpy())[:,1]
        raw=meta.direction_predictions(score);filtered=meta.direction_predictions(score,p)
        raw.write_parquet(run/'raw_intents.parquet');filtered.write_parquet(run/'filtered_intents.parquet')
        if recovery:
            engine.need(raw.equals(pl.read_parquet(previous/'raw_intents.parquet')) and
                filtered.equals(pl.read_parquet(previous/'filtered_intents.parquet')),'Recovery no probability/direction retuning')
        engine.need(np.all((filtered['prediction'].to_numpy()==1)|(filtered['prediction'].to_numpy()==raw['prediction'].to_numpy())),
            'Meta only keeps original sign or cash')
        result['gate_counts']={k:int(np.sum(v['prediction'].to_numpy()==i)) for k,v,i in
            [('raw_LONG',raw,2),('raw_SHORT',raw,0),('raw_CASH',raw,1),('meta_LONG',filtered,2),('meta_SHORT',filtered,0),('meta_CASH',filtered,1)]}
        window=dict(whole,start=cutoff,end=end,events=[v for v in whole['events'] if cutoff<=v['event_us']<end],
            minute_blocks=lambda:whole['minute_blocks'](cutoff,end))
        decisions=np.arange(cutoff,end,common.DAY,dtype=np.int64)
        raw_rebuilt,_=common.targets(raw,bars,decisions,'LONG_SHORT',symbols)
        ref=public_targets.filter(pl.col('available_us')>=cutoff).sort(['available_us','symbol'])
        actual=raw_rebuilt.sort(['available_us','symbol'])
        engine.need(actual.select('available_us','symbol').equals(ref.select('available_us','symbol')) and
            np.allclose(actual['target_weight'],ref['target_weight'],rtol=0,atol=1e-12),'Raw public intent weights same common ordered risk')
        result['raw_target_golden']='PASS_ORIGINAL_PUBLIC_INTENT_SIZING_ATOL1E-12'
        btc=features.filter((pl.col('symbol')=='BTCUSDT')&(pl.col('close_us')>=cutoff)&(pl.col('close_us')<end))
        from scripts.investment.market_regime import past_state
        states={r['close_us']:past_state(r) for r in btc.iter_rows(named=True)}
        for name,pred in [('PUBLIC_SMA_INTENT',raw),('PUBLIC_SMA_META',filtered),('HOLD',None)]:
            factory=(lambda b,d,m:hold.fixed_targets(b,d,m,symbols=symbols)) if pred is None else (
                lambda b,d,m,pred=pred:common.targets(pred,b,d,m,symbols))
            for oldcost in engine.COSTS:
                cost=snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=symbols,
                    fee_zone_by_symbol={s:'DERIVATIVES_CRYPTO_STANDARD' for s in symbols},scenario_id=oldcost['id'],
                    half_spread_bps=oldcost['half_spread_bps'],slippage_bps=oldcost['slippage_bps'],
                    execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY',execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
                for unit in engine.UNITS:
                    guard();progress.update('真实共享资本策略配对',len(result['cases']),12,'账户',strategy=name)
                    case_id=name+'_'+cost['id']+'_'+unit['id'];directory=run/case_id;began=time.monotonic()
                    mode='LONG_ONLY' if pred is None else 'LONG_SHORT'
                    reused=recovery and len(result['cases'])<len(prior['cases'])
                    if reused:
                        old=prior['cases'][len(result['cases'])]
                        engine.need(old['id']==case_id,'Ordered retained account identity')
                        directory=Path(old['artifacts']['targets.parquet']['path']).parent
                        saved=dict(summary=old['summary'],artifacts=old['artifacts'])
                        case=None
                    else:
                        case=engine.simulate(window,mode,cost,unit,progress,guard,target_factory=factory,
                            account_factory=USDTLinearPerpetualAccount,persist_cash_close=True)
                        saved=engine.save_case(case,directory);write(directory/'summary.json',saved['summary'])
                    complete=saved['summary']['completed_minutes']==122*1440
                    engine.need(complete or saved['summary']['completion'].startswith('NOT_EVALUABLE_'),
                        'Complete calendar or explicit risk/data halt, never filled missing returns')
                    checked=audit.verify(directory,symbols,unit['scale'])
                    if pred is not None:
                        checked['target_reference']=audit.verify_direction_targets(pl.read_parquet(directory/'targets.parquet'),pred,bars,symbols,mode)
                    buckets={}
                    for day in checked['daily_direction_contributions']:
                        key=states[day['day_end_us']-common.DAY];v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        v['days']+=1
                        for k in ('LONG','SHORT','CASH'):v[k]+=day[k]
                        v['net']+=day['LONG']+day['SHORT']
                    if not complete:
                        part=checked['partial_stop_direction_contribution'];key=states[(part['stop_us']//common.DAY)*common.DAY]
                        v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        for k in ('LONG','SHORT','CASH'):v[k]+=part[k]
                        v['net']+=part['LONG']+part['SHORT'];v['includes_partial_stop_day']=True
                    checked['by_past_regime']=buckets
                    result['cases'].append(dict(id=case_id,strategy=name,cost=cost['id'],unit=unit['id'],
                        elapsed_seconds=time.monotonic()-began,**saved,independent=checked,account_reused_from_closed_predecessor=bool(reused)))
                    write(run/'CHECKPOINT.json',result);del case;gc.collect()
        result['status']='COMPLETE_ONE_SHARED_META_FIT_TWELVE_FRESH_MATCHED_ACCOUNTS_CONDITIONAL_PROXY'
    except Exception as e:result.update(error_type=type(e).__name__,error=str(e));raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-started,shared_RAM_sampled_peak_bytes=shared_peak,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=spec['experiment_id']+':'+run.name+':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT',success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],accounts=len(result['cases']),models_fit=result['models_fit'])))

if __name__=='__main__':main()
