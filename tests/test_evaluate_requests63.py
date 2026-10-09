"""63-day adapter fixtures: no model fits, inference or account advancement."""
import importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'research/recover-frozen-runner-20261009';sys.path.insert(0,str(HERE))
import evaluate_requests63 as native
base=native.base;CAL=native.CALENDAR;STATE=ROOT.parent/'coin-recovery-state'


def binding(root,m):
    m['files']={p.name:dict(bytes=p.stat().st_size,sha256=base.frozen.sha(p)) for p in sorted(root.iterdir()) if p.is_file() and p.name!='MANIFEST.json'}
    for field,digest in [('model_file','model_sha256'),('scaler_file','scaler_sha256'),('training_plan_file','training_plan_sha256'),('initial_state_file','initial_state_sha256')]:
        if field in m:m[digest]=m['files'][m[field]]['sha256']
    path=root/'MANIFEST.json';path.write_text(json.dumps(m));return path


def bundle(root,control=None):
    c=native.canonical_contexts(STATE);tt=np.arange(CAL['start'],CAL['end_exclusive'],base.frozen.DAY,dtype=np.int64);order=base.E5+(base.SHORT,);allowed=base.COMPACT+(base.SHORT,)
    weights=base.fixed_control_requests(control,CAL) if control else np.tile([.25,.25,0,0,.25,.25],(63,1))
    a=dict(decision_us=tt,symbol_order=np.array(base.frozen.SYMBOLS),expert_order=np.array(order),action_eligible=c['expert_eligible']&np.array([s in allowed for s in order]),desired_expert_budget=weights,feature_available_us=tt.copy(),request_available_us=tt.copy())
    np.savez_compressed(root/'REQUESTS.npz',**a);(root/'producer.py').write_text('# Fixture producer only; no model, account or provider.\n')
    plan=dict(policy_role='FIXED_CONTROL',fits=0,calendar=CAL,control=control) if control else dict(prefix_only=True,warm_start=False,fold_start_us=CAL['start'])
    (root/'PLAN.json').write_text(json.dumps(plan))
    m=dict(schema=native.SCHEMA,arm_id=control or 'FIXTURE_FRESH63',policy_role='FIXED_CONTROL' if control else 'LEARNED_FROZEN',objective_version=2,prediction_role='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS',expert_order=list(order),allowed_actions=list(allowed),uses_feedback_features=False,source_files=['producer.py'],request_file='REQUESTS.npz',model_sha256=None,scaler_sha256=None,training_plan_file='PLAN.json',producer_commit='4'*40,training_cutoff_us=CAL['start'],maximum_training_label_available_us=0,maximum_scaler_input_available_us=0,actual_fit_completed_UTC=None if control else '2026-10-01T00:00:00+00:00',actual_export_completed_UTC='2026-10-01T00:00:00+00:00',calendar=CAL.copy(),adapter_contract_sha256=base.frozen.sha(native.CONTRACT))
    if not control:
        (root/'MODEL.bin').write_bytes(b'fixture model bytes; never load');(root/'INITIAL.bin').write_bytes(b'fixture random initial state; never load');np.savez_compressed(root/'SCALER.npz',center=np.zeros(2),scale=np.ones(2))
        (root/'INITIALIZATION.json').write_text(json.dumps(dict(kind='FRESH_RANDOM_NO_WARM_START',seed=1,parent_checkpoint_sha256=None,optimizer_updates=0,initial_state_sha256=base.frozen.sha(root/'INITIAL.bin'))))
        tt_train=np.array([CAL['start']-3*base.frozen.DAY,CAL['start']-2*base.frozen.DAY],np.int64)
        labels=tt_train+base.frozen.DAY+1;np.savez_compressed(root/'TRAINING_CLOCKS.npz',sample_decision_us=tt_train,feature_available_us=tt_train,expert_input_available_us=tt_train,label_available_us=labels,scaler_input_available_us=tt_train)
        np.savez_compressed(root/'TRAINING_SOURCE.npz',decision_us=tt_train,features=np.zeros((2,2)),labels=np.zeros((2,1)))
        (root/'CONTEXTS.npz').write_bytes((native.PUBLIC/'CANONICAL_CONTEXTS63.npz').read_bytes())
        m.update(model_file='MODEL.bin',scaler_file='SCALER.npz',initial_state_file='INITIAL.bin',initialization_file='INITIALIZATION.json',training_clock_file='TRAINING_CLOCKS.npz',training_data_files=['TRAINING_SOURCE.npz'],context_file='CONTEXTS.npz',maximum_training_label_available_us=int(labels.max()),maximum_scaler_input_available_us=int(tt_train.max()))
    path=binding(root,m);return path,m,a,c


def validate(path,m,a,c):
    loaded,arrays=base.load_bundle(path,base.frozen.sha(path),CAL,native.SCHEMA);assert loaded==m
    proof=native.prefix_provenance(path,m,arrays,c);full,report=base.validate(m,arrays,c,CAL);return proof,full,report


def test_fresh_hashed63_bundle(tmp_path):
    path,m,a,c=bundle(tmp_path);proof,full,report=validate(path,m,a,c)
    assert proof['optimizer_updates_at_initialization']==0 and not proof['model_tensors_loaded'] and report['days']==63 and full.shape==(63,6)


@pytest.mark.parametrize('bad',['wrong_calendar','wrong_contract','warm_start','parent_checkpoint','nonzero_initial_optimizer','label_crosses_fold','expert_input_future','scaler_crosses_fold','clock_max_lie','wrong_source_context','plan_warm_start','float_clock','missing_training_source','evaluation_as_training_source','unplanned_action'])
def test_prefix_provenance_stops_before_account(tmp_path,bad):
    path,m,a,c=bundle(tmp_path)
    if bad=='wrong_calendar':m['calendar']['end_exclusive']+=base.frozen.DAY
    elif bad=='wrong_contract':m['adapter_contract_sha256']='0'*64
    elif bad in ('warm_start','parent_checkpoint','nonzero_initial_optimizer'):
        p=tmp_path/'INITIALIZATION.json';v=json.loads(p.read_bytes());v[{'warm_start':'kind','parent_checkpoint':'parent_checkpoint_sha256','nonzero_initial_optimizer':'optimizer_updates'}[bad]]={'warm_start':'WARM_START','parent_checkpoint':'1'*64,'nonzero_initial_optimizer':1}[bad];p.write_text(json.dumps(v))
    elif bad=='plan_warm_start':p=tmp_path/'PLAN.json';v=json.loads(p.read_bytes());v['warm_start']=True;p.write_text(json.dumps(v))
    elif bad=='wrong_source_context':
        p=tmp_path/'CONTEXTS.npz'
        with np.load(p,allow_pickle=False) as z:v={k:z[k].copy() for k in z.files}
        v['expert_targets'][0,1,0]+=.001;np.savez_compressed(p,**v)
    elif bad=='clock_max_lie':m['maximum_training_label_available_us']-=1
    elif bad=='missing_training_source':m['training_data_files']=[]
    elif bad=='evaluation_as_training_source':m['training_data_files']=[m['context_file']]
    elif bad=='unplanned_action':m['allowed_actions'].append(base.E5[2])
    else:
        p=tmp_path/'TRAINING_CLOCKS.npz'
        with np.load(p,allow_pickle=False) as z:v={k:z[k].copy() for k in z.files}
        if bad=='label_crosses_fold':v['label_available_us'][-1]=CAL['start']
        elif bad=='expert_input_future':v['expert_input_available_us'][0]=v['sample_decision_us'][0]+1
        elif bad=='scaler_crosses_fold':v['scaler_input_available_us'][-1]=CAL['start']
        elif bad=='float_clock':v['feature_available_us']=v['feature_available_us'].astype(float)
        np.savez_compressed(p,**v)
    path=binding(tmp_path,m)
    with pytest.raises(ValueError):validate(path,m,a,c)


@pytest.mark.parametrize('bad',['61days','shifted_calendar','future_request','changed_mask','short_replaces_slot','float_requests'])
def test63_request_identity_and_clock_rejections(tmp_path,bad):
    _,m,a,c=bundle(tmp_path)
    if bad=='61days':a={k:(v[:61] if k not in ('expert_order','symbol_order') else v) for k,v in a.items()}
    elif bad=='shifted_calendar':a['decision_us']+=base.frozen.DAY
    elif bad=='future_request':a['request_available_us'][0]+=1
    elif bad=='changed_mask':a['action_eligible'][0,5]=False
    elif bad=='short_replaces_slot':a['expert_order'][3]=base.SHORT
    elif bad=='float_requests':a['desired_expert_budget']=a['desired_expert_budget'].astype(np.float32)
    with pytest.raises(ValueError):base.validate(m,a,c,CAL)


@pytest.mark.parametrize('control',['STATIC50','CASH50'])
def test_fixed_controls_exact_request_and_zero_append_parity(tmp_path,control,monkeypatch):
    path,m,a,c=bundle(tmp_path,control);proof,full,_=validate(path,m,a,c);assert proof['fits']==0 and (full[:,5]==0).all()
    mapper=base.frozen.modules(STATE);monkeypatch.setattr(mapper,'NativeDailySimulator',lambda *a,**k:pytest.fail('No fixture wallet'))
    target,budget=base.mapped(full,c,mapper.mapper,CAL)
    c5={k:(v[:,:5] if k in ('expert_targets','expert_eligible','target_available_us') else v) for k,v in c.items()};c5['expert_order']=base.E5
    old_target,old_budget=base.mapped(full[:,:5],c5,mapper.mapper,CAL)
    np.testing.assert_array_equal(target,old_target);np.testing.assert_array_equal(budget[:,:5],old_budget);assert (budget[:,5]==0).all() and (target[-1]==0).all() and (target[:-1]!=0).any()
    a['desired_expert_budget'][0]=[.4,.3,0,0,.3,0];np.savez_compressed(tmp_path/'REQUESTS.npz',**a);path=binding(tmp_path,m)
    with pytest.raises(ValueError):validate(path,m,a,c)


def test_forced_release63_is_separate_from_discretionary_ramp(tmp_path):
    _,m,a,c=bundle(tmp_path);a['desired_expert_budget'][:]=0;a['desired_expert_budget'][:3,5]=1;a['desired_expert_budget'][3:,1]=1;c['expert_eligible'][3:,5]=False;a['action_eligible'][3:,5]=False
    full,_=base.validate(m,a,c,CAL);mapper=base.frozen.modules(STATE);target,budget=base.mapped(full,c,mapper.mapper,CAL)
    np.testing.assert_allclose(budget[2],[.85,0,0,0,0,.15],atol=1e-15,rtol=0);np.testing.assert_allclose(budget[3],[.95,.05,0,0,0,0],atol=1e-15,rtol=0)
    assert abs(budget[3]-budget[2]).sum()>.1 and (target[-1]==0).all()


@pytest.mark.parametrize('bad',['capacity','carried_position','capital','cost'])
def test_simulator_constructor_original_cost_funding_and_paid_closure(monkeypatch,bad):
    base.frozen.modules(STATE)
    from scripts.investment import resumable_perpetual as engine,perpetual_directional as original
    from quant.bybit_isolated_account import BybitIsolatedAccount
    contract=base.frozen.read(native.CONTRACT);calls=[]
    def fixture_sim(window,mode,cost,unit,**kw):
        calls.append((window,mode,cost,unit,kw));return SimpleNamespace(previous_quote=None,account=SimpleNamespace(nav=lambda:10000,positions={s:SimpleNamespace(quantity=0) for s in base.frozen.SYMBOLS}))
    monkeypatch.setattr(engine,'NativeDailySimulator',fixture_sim);monkeypatch.setattr(base,'market',lambda *a:CAL.copy())
    sim=base.simulator(STATE,contract,CAL);window,mode,cost,unit,kw=calls[-1]
    assert window==CAL and mode=='LONG_SHORT' and cost==original.COSTS[0] and unit==dict(id='RAW_AS_FRACTION',scale=1.) and kw==dict(account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    if bad=='cost':contract=dict(contract,cost=dict(contract['cost'],slippage_bps=0))
    else:
        if bad=='capacity':sim.previous_quote={s:10 for s in base.frozen.SYMBOLS}
        elif bad=='carried_position':sim.account.positions['BTCUSDT'].quantity=1
        elif bad=='capital':sim.account.nav=lambda:20000
        monkeypatch.setattr(engine,'NativeDailySimulator',lambda *a,**k:sim)
    with pytest.raises(ValueError):base.simulator(STATE,contract,CAL)


def test63_future_request_never_reserves_a_wallet(tmp_path,monkeypatch):
    path,m,a,c=bundle(tmp_path);a['request_available_us'][0]+=1;np.savez_compressed(tmp_path/'REQUESTS.npz',**a);path=binding(tmp_path,m)
    monkeypatch.setattr(base,'source_market_check',lambda *a,**k:{'fixture':True});monkeypatch.setattr(base,'simulator',lambda *a,**k:pytest.fail('Rejected request cannot create an account'))
    contract=base.frozen.read(native.CONTRACT)
    with pytest.raises(ValueError):base.check(STATE,path,base.frozen.sha(path),CAL,native.CONTRACT,(native.PUBLIC/'MOMENTUM_SHORT_CONTEXTS63.npz',contract['context_files']['MOMENTUM_SHORT_CONTEXTS63.npz']['sha256']),native.SCHEMA,native.prefix_provenance)


@pytest.mark.parametrize('bad',['valid','wrong_minutes','unpaid_close','wrong_fee','wrong_friction','wrong_capacity','current_mark_for_funding','held_first_funding','invented_start_mark'])
def test_parameterized_actual_input_auditor_contracts_on_fixture_journals(monkeypatch,bad):
    # Synthetic dictionaries and sparse quote/mark rows exercise the audit's
    # input/contract checks. The financial audit is a stub, not a wallet result.
    import types,polars as pl
    import verify_native61 as auditor
    financial=types.ModuleType('modules.transformer_v3.isolated_audit');financial.verify=lambda *a:dict(status='FIXTURE_FINANCIAL_STUB_NOT_ACCOUNT',minutes=90720)
    monkeypatch.setitem(sys.modules,'modules.transformer_v3.isolated_audit',financial)
    summary=dict(completed_minutes=90720,required_minutes=90720,completion='COMPLETE_CONDITIONAL_ACCOUNT',terminal_cash_realized=True,terminal_not_forced_free_fill=True,positions={s:dict(quantity=0) for s in base.frozen.SYMBOLS},funding_original_events=945,liquidation_count=0)
    execution=dict(status='COMPLETE_CONDITIONAL_ACCOUNT',elapsed_seconds=1,peak_RSS_bytes=1000000)
    funds=[]
    for i in range(189):
        event=CAL['start']+i*8*3600000000+1000
        for symbol in base.frozen.SYMBOLS:funds.append(dict(symbol=symbol,event_us=event,raw_rate=.0001,conditional_rate_scale=1,owned=False,quantity=0,signed_funding_USDT=0,mark_price=None if i==0 else 100.,mark_close_us=None if i==0 else event-1000))
    trade=dict(symbol='BTCUSDT',event_us=CAL['start']+2*base.frozen.MINUTE+1,signal_us=CAL['start'],side='BUY',leg='CLOSE',fee_amount=.0027522,fee_asset='USDT',decimal_strings=dict(quantity='.05',position_delta='.05',execution_mid_price='100',fill_price='100.08',fee_amount='.0027522',mark_price='100'))
    if bad=='wrong_minutes':summary['completed_minutes']=87840
    elif bad=='unpaid_close':summary['terminal_not_forced_free_fill']=False
    elif bad=='wrong_fee':trade['decimal_strings']['fee_amount']='0'
    elif bad=='wrong_friction':trade['decimal_strings']['fill_price']='100'
    elif bad=='wrong_capacity':trade['decimal_strings']['quantity']=trade['decimal_strings']['position_delta']='.2';trade['decimal_strings']['fee_amount']='.0110088'
    elif bad=='current_mark_for_funding':funds[5]['mark_close_us']=funds[5]['event_us']
    elif bad=='held_first_funding':funds[0]['owned']=True;funds[0]['quantity']=1
    elif bad=='invented_start_mark':funds[0]['mark_price']=100.
    payload={'summary.json':summary,'EXECUTION.json':execution,'funding.json':funds,'trades.json':[trade],'liquidations.json':[]}
    monkeypatch.setattr(auditor,'read',lambda p:payload[p.name])
    mark_stamps={CAL['start'],CAL['start']+base.frozen.MINUTE}|{CAL['start']+i*8*3600000000-base.frozen.MINUTE for i in range(1,189)}
    def parquet(path):
        if path.name.endswith('_funding_events.parquet'):return pl.DataFrame(dict(calc_time_ms=[(CAL['start']+i*8*3600000000)//1000+1 for i in range(189)],last_funding_rate=[.0001]*189))
        if path.parent.name=='klines':return pl.DataFrame(dict(open_us=[CAL['start']+base.frozen.MINUTE,CAL['start']+2*base.frozen.MINUTE],open=[100.,100.],quote_volume=[10000.,10000.]))
        return pl.DataFrame(dict(timestamp_ms=[t//1000 for t in sorted(mark_stamps)],close=[100.]*len(mark_stamps)))
    monkeypatch.setattr(pl,'read_parquet',parquet)
    if bad=='valid':
        report=auditor.verify(Path('fixture-results'),Path('fixture-state'),calendar=CAL);assert report['continuous_days']==63 and report['actual_input_check']['funding_events']==945
    else:
        with pytest.raises(ValueError):auditor.verify(Path('fixture-results'),Path('fixture-state'),calendar=CAL)
