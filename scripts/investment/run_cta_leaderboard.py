"""Frozen zero-fit CTA directions through the existing shared account."""
import argparse,gc,hashlib,json,os,resource,subprocess,time
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl
from quant import disk,resources
from quant.paths import ROOT,STATE
from scripts.investment import cta_classics as cta, audit_cta_classics as reference
from scripts.investment import perpetual_directional as engine,audit_shared_direction as finance
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount
from scripts.investment.bybit_cost_inputs import snapshot_cost
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS,append_event

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def native(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError('Unsupported research JSON type: '+type(value).__name__)
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=native)+'\n',encoding='utf-8')
def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1_000_000

def main():
    ap=argparse.ArgumentParser()
    for k in ('protocol','run-dir','output'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();spec=json.loads(a.protocol.read_bytes());run=a.run_dir.resolve();out=a.output.resolve()
    assert os.getenv('COIN_TASK_ID') and run.parent==STATE and not run.exists() and not out.exists()
    assert out.is_relative_to(ROOT/'reports/fast_research') and pl.thread_pool_size()<=2
    public_sma='PUBLIC_SMA50_200'
    assert spec['families'] and len(set(spec['families']))==len(spec['families']) and set(spec['families'])<=set(cta.SUPPORTED_FAMILIES)|{public_sma}
    assert spec['modes']==list(cta.MODES) and spec['models_fit']==0
    costs=[v for v in engine.COSTS if v['id'] in spec.get('cost_ids',[v['id'] for v in engine.COSTS])]
    assert costs and len(costs)==len(spec.get('cost_ids',costs)), 'Fixed known cost subset, no cheaper invented cost'
    for p,h in spec['frozen_source_hashes'].items():assert sha(ROOT/p)==h,'Frozen rule/source '+p
    assert sha(ROOT/'state/dataset_lock.json')==spec['locked_sha256']
    manifest=spec['data_manifest'];assert sha(manifest['path'])==manifest['sha256']
    import xml.etree.ElementTree as ET
    test=spec['regression'];assert sha(ROOT/test['path'])==test['sha256'] and sha(ROOT/'tests/test_cta_classics.py')==test['source_sha256']
    suites=list(ET.parse(ROOT/test['path']).getroot().iter('testsuite'))
    assert sum(int(v.get('tests',0)) for v in suites)==test.get('tests',2) and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
    paths=['scripts/investment/'+p+'.py' for p in ('cta_classics','audit_cta_classics','run_cta_leaderboard',
        'multi_asset_data','public_sma_perpetual','donchian_daily_pool_target','perpetual_directional','perpetual_closing_exempt_account',
        'bybit_cost_inputs','audit_shared_direction','market_regime','shared_direction_model')]
    paths+=['src/quant/perpetual_account.py','tests/test_cta_classics.py']
    paths+=['third_party/jesse_example_donchian/'+p for p in cta.PINNED_HASHES]
    if public_sma in spec['families']:
        from scripts.investment import public_sma_perpetual as public_targets, public_sma_daily
        pt=spec['public_hook_regression'];assert sha(ROOT/pt['path'])==pt['sha256']
        assert sha(ROOT/'tests/test_public_sma_perpetual.py')==pt['source_sha256']
        suites=list(ET.parse(ROOT/pt['path']).getroot().iter('testsuite'))
        assert sum(int(v.get('tests',0)) for v in suites)==pt['tests'] and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
        paths+=['scripts/investment/public_sma_daily.py','tests/test_public_sma_perpetual.py']
        paths+=['third_party/jesse_example_smacrossover/'+p for p in public_sma_daily.PINNED_HASHES]
    cycle_inputs=spec.get('input_adapter')=='FIXED_BTC_ETH_2022_2023_CYCLE'
    if cycle_inputs:
        from scripts.investment.cta_cycle_window import load_window as load_cycle_window
        paths+=['scripts/investment/cta_cycle_window.py']
        ct=spec['cycle_regression'];assert sha(ROOT/ct['path'])==ct['sha256']
        assert sha(ROOT/'tests/test_cta_cycle_window.py')==ct['source_sha256']
        suites=list(ET.parse(ROOT/ct['path']).getroot().iter('testsuite'))
        assert sum(int(v.get('tests',0)) for v in suites)==ct['tests'] and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
    fast_filter=spec.get('short_four_hour_filter')
    if fast_filter:
        from scripts.investment import short_fast_confirmation as fast_adapter
        assert fast_filter==fast_adapter.RULES and spec['families']==['DC_CONFIRMED_SHORT']
        assert spec.get('account_modes')==['LONG_SHORT']
        ft=spec['fast_regression'];assert sha(ROOT/ft['path'])==ft['sha256']
        assert sha(ROOT/'tests/test_short_fast_confirmation.py')==ft['source_sha256']
        suites=list(ET.parse(ROOT/ft['path']).getroot().iter('testsuite'))
        assert sum(int(v.get('tests',0)) for v in suites)==ft['tests'] and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
        paths+=['scripts/investment/short_fast_confirmation.py','tests/test_short_fast_confirmation.py']
    binding=dict(task_id=os.environ['COIN_TASK_ID'],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha(a.protocol),source_hashes={p:sha(ROOT/p) for p in paths},input_manifest_sha256=manifest['sha256'])
    controls=[]
    if not spec.get('include_controls',True) and cycle_inputs and 'reused_cycle_controls' in spec:
        from scripts.investment.reuse_cycle_controls import load as load_controls
        cr=spec['controls_reuse_regression'];assert sha(ROOT/cr['path'])==cr['sha256']
        assert sha(ROOT/'tests/test_reuse_cycle_controls.py')==cr['source_sha256']
        suites=list(ET.parse(ROOT/cr['path']).getroot().iter('testsuite'))
        assert sum(int(v.get('tests',0)) for v in suites)==cr['tests'] and not any(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
        controls,control_binding=load_controls(spec,binding['source_hashes'])
        binding['reused_cycle_controls']=control_binding
        binding['source_hashes']['scripts/investment/reuse_cycle_controls.py']=sha(ROOT/'scripts/investment/reuse_cycle_controls.py')
    elif not spec.get('include_controls',True):
        base=spec['baseline'];assert sha(ROOT/base['path'])==base['sha256']
        prior=json.loads((ROOT/base['path']).read_bytes())
        assert prior['status']=='ACCEPTED_FIXED_DONCHIAN_303D_TWO_COST_TASKS_NO_WALLET_JOIN' and prior['complete_accounts']==20
        allowed={'scripts/investment/'+p+'.py' for p in ('cta_classics','audit_cta_classics','run_cta_leaderboard')}
        allowed.add('tests/test_cta_classics.py')
        for p,h in prior['source_hashes'].items():
            if p not in allowed:assert sha(ROOT/p)==h,'Reused financial/data/kernel source changed: '+p
        for entry in prior['inputs']:
            for k in ('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','resources'):
                old=json.loads((ROOT/entry['path']).read_bytes())['protocol']
                assert old[k]==spec[k], 'Baseline input/capital/cost mismatch: '+k
        binding['reused_controls_baseline']=base
    run.mkdir();write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=spec['experiment_id'],event_id=spec['experiment_id']+':'+run.name+':START',
        event_type='OPERATIONAL_RESEARCH_START',git_commit=binding['git_commit'],data_manifest_hash=manifest['sha256'],protocol_hash=binding['protocol_sha256'],
        feature_set='CLOSED_1D_PRICE_PRIOR_CHANNEL_PAST30_RETURNS'+('_CLOSED4H_SHORT_CONFIRMATION' if fast_filter else ''),labels='NONE_ZERO_TRAINING',model_family='FROZEN_PUBLIC_CLASSIC_CTA',
        hyperparameters=spec['rules'],seed=None,thresholds='NO_FITTED_OR_POST_RESULT_THRESHOLD',cost_assumptions=spec['cost'],
        all_folds=spec['data_role']+':'+spec['economics_start']+':'+spec['economics_end_exclusive'],success_failure='START_BEFORE_ACCOUNTS',reason_for_next_experiment=spec['question'],
        result_influenced_later_choice=False,models_fit=0)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    started=time.monotonic();shared_peak=0;progress=Progress();progress.value['detail']=f"冻结经典CTA；零训练；同{len(spec['symbols'])}币共享资本代理账户";r=dict(status='FAILED',binding=binding,protocol=spec,
        run_dir=str(run),cases=[],models_fit=0,search_configurations=0,GPU_hours=0.,locked_consumed=False,orders_sent=0)
    def guard():
        nonlocal shared_peak
        shared_peak=max(shared_peak,resources.status()['ram_current_bytes'])
        assert time.monotonic()-started<spec['budget']['wall_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<spec['budget']['RSS_bytes']
        assert sum(p.stat().st_size for p in run.rglob('*') if p.is_file())<spec['budget']['owned_bytes']
    try:
        progress.update('CTA磁盘实扫；总量未知',None,None,'扫描')
        r['disk_before']=dict(disk.check(spec['budget']['owned_bytes']),measured_utc=datetime.now(UTC).isoformat())
        symbols=tuple(spec['symbols']);begin=stamp(spec['preparation_start']);start=stamp(spec['economics_start']);end=stamp(spec['economics_end_exclusive'])
        assert begin<=start<end and (end-start)%cta.DAY==0
        days=(end-start)//cta.DAY;r['actual_days']=days
        whole=(load_cycle_window(manifest['path'],symbols,begin,end) if cycle_inputs else
            load_portfolio_window(manifest['path'],symbols,begin,end));bars=whole['daily']
        signal,available=cta.signals(bars,np.arange(begin,end,cta.DAY,dtype=np.int64),symbols,
            include_components=bool(set(spec['families'])&set(cta.EXTRA_FAMILIES)) or 'legacy_signal_golden' in spec)
        r['signal_reference']=reference.verify_signals(signal,bars,np.arange(begin,end,cta.DAY,dtype=np.int64),symbols)
        signal.write_parquet(run/'frozen_signals.parquet');write(run/'SIGNAL_AVAILABILITY.json',available)
        score=signal.filter(pl.col('close_us')>=start)
        available_families=[f for f in spec['families'] if f!=public_sma]
        assert score.height==days*len(symbols)
        if available_families:assert score.select(available_families).null_count().select(pl.sum_horizontal(pl.all())).item()==0
        if 'legacy_signal_golden' in spec:
            golden=spec['legacy_signal_golden'];assert sha(golden['path'])==golden['sha256']
            saved=pl.read_parquet(golden['path'])
            assert signal.select(saved.columns).equals(saved), 'Original full-window rule signals changed'
            r['legacy_signal_golden']=dict(status='PASS_SAME_ORIGINAL_SIGNAL_COLUMNS_ALL_DECISIONS',**golden)
        decisions=np.arange(start,end,cta.DAY,dtype=np.int64)
        if 'legacy_control_targets' in spec:
            for golden in spec['legacy_control_targets']:
                assert sha(golden['path'])==golden['sha256']
                legacy,_=cta.targets(signal,bars,decisions,golden['mode'],symbols,golden['family'])
                assert legacy.equals(pl.read_parquet(golden['path'])), 'Reused control targets changed'
            r['legacy_control_targets_status']='PASS_SAME_CASH_AND_HOLD_ALL303D_ORDERED_TARGETS'
        original_signal=signal
        if controls:
            for c in controls:
                expected,_=cta.targets(signal,bars,decisions,c['mode'],symbols,
                    'HOLD' if c['strategy']=='HOLD' else 'SMA200_SIGNED')
                assert expected.equals(pl.read_parquet(c['artifacts']['targets.parquet']['path'])),'Reused controls target identity'
            r['reused_controls']=controls
        if 'unchanged_long_controls' in spec:
            assert spec['families']==['SMA200_SHORT50'] and spec['account_modes'] in (['SHORT_ONLY'],['LONG_SHORT'])
            prior_ref=spec['unchanged_long_controls'];assert sha(ROOT/prior_ref['path'])==prior_ref['sha256']
            old=json.loads((ROOT/prior_ref['path']).read_bytes())
            old_task=json.loads((STATE/'task-progress'/('task-'+old['binding']['task_id']+'.json')).read_bytes())
            assert old_task['status']=='completed' and old_task['exit_code']==0
            recipe_paths=set(spec['recipe_source_changes'])|{'scripts/investment/run_cta_leaderboard.py','scripts/investment/reuse_cycle_controls.py'}
            for p,h in old['binding']['source_hashes'].items():
                if p not in recipe_paths:assert sha(ROOT/p)==h,'Unchanged long financial source differs: '+p
            for k in ('symbols','data_manifest','locked_sha256','preparation_start','economics_start','economics_end_exclusive','cost','cost_ids','resources'):
                assert old['protocol'][k]==spec[k]
            longs=[c for c in old['cases'] if c['strategy']=='SMA200_SIGNED' and c['mode']=='LONG_ONLY']
            assert len(longs)==2 and {c['unit'] for c in longs}=={'RAW_AS_FRACTION','RAW_AS_PERCENT'}
            expected,_=cta.targets(signal,bars,decisions,'LONG_ONLY',symbols,'SMA200_SHORT50')
            for c in longs:
                assert c['summary']['terminal_cash_realized'] and c['summary']['completed_minutes']==days*1440
                assert c['independent']['maximum_NAV_error_USDT']<1e-7 and c['independent']['maximum_wallet_error_USDT']<1e-7
                for v in c['artifacts'].values():
                    p=Path(v['path']).resolve();assert p.is_relative_to(STATE) and sha(p)==v['sha256'] and p.stat().st_size==v['bytes']
                assert expected.equals(pl.read_parquet(c['artifacts']['targets.parquet']['path'])),'Unchanged long targets differ'
            r['reused_directional_controls']=longs
            r['unchanged_long_proof']=dict(status='PASS_ALL730D_TARGETS_EXACTLY_SAME',**prior_ref)
        if fast_filter:
            fast_bars=fast_adapter.aggregate_bars(manifest['path'],symbols,start,end,progress)
            fast_signal=fast_adapter.signals(fast_bars,symbols)
            r['fast_signal_reference']=fast_adapter.verify_signals(fast_signal,fast_bars,symbols)
            fast_signal.write_parquet(run/'fast_four_hour_signals.parquet')
            signal=fast_adapter.mask_daily(original_signal,fast_signal)
            signal.write_parquet(run/'gated_daily_signals.parquet')
            r['fast_rule']=fast_filter
            r['short_daily_decisions_suppressed']=original_signal.filter(pl.col('DC_CONFIRMED_SHORT')<0).height-signal.filter(pl.col('DC_CONFIRMED_SHORT')<0).height
            r['fast_warmup_scope']='FIRST20_COMPLETED_4H_BARS_UNKNOWN_SHORT_CASH_NO_PREWINDOW_MINUTES_ADDED'
        window=dict(whole,start=start,end=end,events=[v for v in whole['events'] if start<=v['event_us']<end],
                    minute_blocks=lambda:whole['minute_blocks'](start,end,trade_ranges=bool(fast_filter)))
        from scripts.investment.shared_direction_model import feature_table
        from scripts.investment.market_regime import past_state
        btc=feature_table(bars,symbols)[0].filter((pl.col('symbol')=='BTCUSDT')&(pl.col('close_us')>=start)&(pl.col('close_us')<end))
        states={v['close_us']:past_state(v) for v in btc.iter_rows(named=True)};r['descriptive_past_states']=states
        account_modes=spec.get('account_modes',['LONG_ONLY','SHORT_ONLY','LONG_SHORT'])
        assert account_modes and len(set(account_modes))==len(account_modes)
        assert set(account_modes)<= {'LONG_ONLY','SHORT_ONLY','LONG_SHORT'}
        plans=[(f,m) for f in spec['families'] for m in account_modes]
        if spec.get('include_controls',True):plans += [('CASH','CASH'),('HOLD','LONG_ONLY')]
        r['required_accounts']=len(plans)*len(costs)*len(engine.UNITS)
        reused={}
        if 'completed_case_reuse' in spec:
            reuse=spec['completed_case_reuse'];parent=Path(reuse['checkpoint_path'])
            assert parent.is_relative_to(STATE) and sha(parent)==reuse['checkpoint_sha256']
            receipt=ROOT/reuse['preservation_path'];assert sha(receipt)==reuse['preservation_sha256']
            preserved=json.loads(receipt.read_bytes());old=json.loads(parent.read_bytes())
            assert preserved['status']=='INTERRUPTED_TASK_AND_STOPPED_COLLECTORS_PRESERVED_NOT_RESTARTED'
            assert old['binding']['task_id']==preserved['parent_task_id']==reuse['parent_task_id']
            def financial_spec(v):
                v=dict(v);v.pop('completed_case_reuse',None);v.pop('created_utc',None)
                v['frozen_source_hashes']=dict(v['frozen_source_hashes'])
                v['frozen_source_hashes'].pop('scripts/investment/run_cta_leaderboard.py')
                return v
            assert financial_spec(old['protocol'])==financial_spec(spec),'Recovery cannot change the economic experiment'
            for p,h in old['binding']['source_hashes'].items():
                if p!='scripts/investment/run_cta_leaderboard.py':assert sha(ROOT/p)==h
            assert old['actual_days']==days and old['required_accounts']==r['required_accounts']
            assert pl.read_parquet(parent.parent/'frozen_signals.parquet').equals(original_signal)
            for c in old['cases']:
                assert c['id'] not in reused and c['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'
                for artifact in c['artifacts'].values():
                    p=Path(artifact['path']);assert p.is_relative_to(parent.parent) and sha(p)==artifact['sha256']
                directory=Path(c['artifacts']['targets.parquet']['path']).parent
                assert json.loads((directory/'summary.json').read_bytes())==c['summary']
                reused[c['id']]=c
            assert set(reused)==set(preserved['completed_case_ids'])
            r['recovery']=dict(**reuse,scope='REUSE_WHOLE_VERIFIED_COMPLETED_ACCOUNTS; NOT_JOIN_WALLETS_OR_REUSE_PARTIAL_CASE',
                parent_exit_code='UNKNOWN',reused_accounts=len(reused))
        for family,mode in plans:
            target_family='SMA200_SIGNED' if family=='CASH' else family
            if family==public_sma:
                target,meta=public_targets.fixed_targets(bars,decisions,mode,symbols=symbols,allocation='INVERSE_VOL_30D')
                target_ref=reference.verify_public_sma_targets(target,bars,decisions,symbols,mode)
            else:
                target,meta=cta.targets(signal,bars,decisions,mode,symbols,target_family)
                target_ref=reference.verify_targets(target,signal,bars,symbols,target_family,mode)
            if fast_filter:meta['short_four_hour_filter']=fast_filter
            for oldcost in costs:
                cost=snapshot_cost(ROOT/'docs/input_evidence/BYBIT_USER_FEE_SNAPSHOT_20261004.json',symbols=symbols,
                    fee_zone_by_symbol={s:'DERIVATIVES_CRYPTO_STANDARD' for s in symbols},scenario_id=oldcost['id'],
                    half_spread_bps=oldcost['half_spread_bps'],slippage_bps=oldcost['slippage_bps'],execution_source_ref='ACCEPTED_BINANCE_USDM_PROXY',
                    execution_status='FIXED_NON_NATIVE_SPREAD_SLIPPAGE_SCENARIO')
                for unit in engine.UNITS:
                    guard();case_id='_'.join((family+('_FAST4H' if fast_filter else ''),mode,cost['id'],unit['id']));directory=run/case_id;began=time.monotonic()
                    progress.value['detail']=f"CTA账户{len(r['cases'])+1}/{r['required_accounts']} · {case_id} · 零训练"
                    progress.update('经典CTA组合账户对照',len(r['cases']),r['required_accounts'],'账户',family=family,mode=mode)
                    if case_id in reused:
                        prior=reused.pop(case_id);directory=Path(prior['artifacts']['targets.parquet']['path']).parent
                        assert pl.read_parquet(directory/'targets.parquet').equals(target)
                        checked=finance.verify(directory,symbols,unit['scale'])
                        assert checked['maximum_NAV_error_USDT']<1e-7 and checked['maximum_wallet_error_USDT']<1e-7
                        checked['target_reference']=target_ref;checked['by_past_regime']=prior['independent']['by_past_regime']
                        prior=dict(prior,independent=checked,reused_completed_account=True,
                            recovery_validation_seconds=time.monotonic()-began,original_task_id=reuse['parent_task_id'])
                        r['cases'].append(prior);write(run/'CHECKPOINT.json',r);gc.collect();continue
                    case=engine.simulate(window,mode,cost,unit,progress,guard,target_factory=lambda b,d,m:(target,meta),
                        account_factory=USDTLinearPerpetualAccount,persist_cash_close=True,
                        position_protection=(fast_adapter.FastShortConfirmation(fast_signal,original_signal) if fast_filter else None))
                    saved=engine.save_case(case,directory);write(directory/'summary.json',saved['summary'])
                    checked=finance.verify(directory,symbols,unit['scale']);checked['target_reference']=target_ref
                    assert pl.read_parquet(directory/'targets.parquet').equals(target)
                    buckets={}
                    for day in checked['daily_direction_contributions']:
                        key=states[day['day_end_us']-cta.DAY];v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        v['days']+=1
                        for k in ('LONG','SHORT','CASH'):v[k]+=day[k]
                        v['net']+=day['LONG']+day['SHORT']
                    part=checked['partial_stop_direction_contribution']
                    if part:
                        key=states[part['stop_us']//cta.DAY*cta.DAY];v=buckets.setdefault(key,dict(days=0,LONG=0.,SHORT=0.,CASH=0.,net=0.))
                        for k in ('LONG','SHORT','CASH'):v[k]+=part[k]
                        v['net']+=part['LONG']+part['SHORT'];v['partial_stop_day']=True
                    checked['by_past_regime']=buckets
                    r['cases'].append(dict(id=case_id,strategy=family,mode=mode,cost=cost['id'],unit=unit['id'],
                        elapsed_seconds=time.monotonic()-began,**saved,independent=checked))
                    write(run/'CHECKPOINT.json',r);del case;gc.collect()
        assert not reused,'Every reused case must belong to the fixed plan'
        r['status']=f"COMPLETE_FROZEN_CTA_{r['required_accounts']}_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS"
    except Exception as e:r.update(error_type=type(e).__name__,error=str(e));raise
    finally:
        r.update(elapsed_seconds=time.monotonic()-started,shared_RAM_sampled_peak_bytes=shared_peak,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(out,r)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=spec['experiment_id']+':'+run.name+':RESULT',
            event_type='OPERATIONAL_RESEARCH_RESULT',success_failure=r['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=r['status'],accounts=len(r['cases']),models_fit=0)))

if __name__=='__main__':main()
