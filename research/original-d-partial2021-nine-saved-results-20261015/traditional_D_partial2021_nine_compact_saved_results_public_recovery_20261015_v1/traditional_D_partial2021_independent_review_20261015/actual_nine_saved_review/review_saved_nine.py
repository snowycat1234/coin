"""Read completed actual2021 saved evidence only; no financial execution."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{6})
import sys,json,time,resource,subprocess,multiprocessing,fcntl,socket,urllib.request
from pathlib import Path
from hashlib import sha256
from contextlib import ExitStack
from decimal import Decimal as D,localcontext
from collections import defaultdict
from io import BytesIO
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;MODULE=ROOT/'traditional_D_partial2021_20261015'
ACTUAL=MODULE/'actual_nine_attempt001';PREPDIR=MODULE/'source_preparation_final'
sys.path.insert(0,str(MODULE))
import numpy as np
import partial_entry as e
import partial_d as integration
import run_partial as runner
from saved_native_reconciliation import reconcile_saved_native,checker_sha256
GO_SHA='79dfb608da4e423833df12f1e512a26ff5610ae2f7ea03d41c9e62e1a2a555f8'
REVIEW_SHA='5cd2fcc60a565a91866a0ddfbce1bd41e643f97d46aaddf17601e049815e6404'
GO_PATH=MODULE/'ROOT_GO_APPROVED_NINE_20261015_1117.json'
REVIEW_PATH=OUT.parent/'INDEPENDENT_ORIGINAL_D_PARTIAL2021_REVIEW.json'
def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
def pin(path):return dict(SHA256=digest(path),bytes=Path(path).stat().st_size)
def load(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    raw=runner.body(value)
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert digest(GO_PATH)==GO_SHA and digest(REVIEW_PATH)==REVIEW_SHA
PREP_RAW=(PREPDIR/'PREPARATION.json').read_bytes();PREP=e._validate_preparation(PREP_RAW)
assert PREP['code_identity']==e.code_identity()
GO=GO_PATH.read_bytes();REVIEW=REVIEW_PATH.read_bytes()
for cell_id in e.tranche_cells():
    p=e.validate_root_go(PREP_RAW,GO,GO_SHA,cell_id=cell_id)
    e._validate_independent_review(PREP_RAW,p,REVIEW,REVIEW_SHA,GO)
S=e.s.S;START=e.s.START;END=e.s.END;MINUTE=e.s.MINUTE
SOURCE_EVENTS=load(e.s.SOURCE_ROOT/'prepared_2021/EVENTS.json')
SOURCE_EVENTS=[r for r in SOURCE_EVENTS if START<=r['event_us']<END]
SOURCE_BY_KEY={(r['symbol'],r['event_us']):r for r in SOURCE_EVENTS}
assert len(SOURCE_EVENTS)==len(SOURCE_BY_KEY)==4110
MONTHS=[]
def load_quote_sources():
    if MONTHS:return
    index=load(e.s.SOURCE_ROOT/'prepared_2021/SOURCE_INDEX.json');cursor=e.s.FULL_START
    for rec in index['months']:
        count=rec['minutes'];last=cursor+count*MINUTE
        if last>START:
            name='prepared_2021/months/'+rec['month']+'.npz';p=PREP['years']['2021']['source_files'][name]
            data=e.s.exact(e.s.SOURCE_ROOT/name,p['SHA256'],p['bytes'])
            with np.load(BytesIO(data),allow_pickle=False) as z:
                arrays={s+'_'+field:z[s+'_'+field].copy() for s in S for field in ('open','quote_volume')}
            MONTHS.append((cursor,last,arrays))
        cursor=last
def source_quote(symbol,open_us,field):
    for first,last,arrays in MONTHS:
        if first<=open_us<last:return arrays[symbol+'_'+field][(open_us-first)//MINUTE]
    raise ValueError('SOURCE_NATIVE_QUOTE_CLOCK_OUTSIDE_SCOPE')

blocked=[(integration,'construct_case'),(integration.ExpansionAccount,'__init__'),(integration.D,'construct_case'),
    (integration.D.Guard50ExitAccount,'__init__'),(integration.V2,'construct_case'),(integration.V2.ContinuationAccount,'__init__'),
    (integration.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),(integration.V2.native,'_construct_case'),
    (e.s.g,'make_account'),(e.s.CapturedMinuteProvider,'__call__'),(integration.V2.native.runtime()[2].EarlierTerminalSimulator,'advance_day'),
    (e,'make_case'),(e.CaseExecutionScope,'__post_init__'),(runner,'case'),(runner,'controller'),(runner,'run_pool'),
    (runner,'_run_pool'),(runner,'claim_launch'),(runner,'controller_lease'),(runner,'save'),(runner,'write_bytes'),
    (subprocess,'Popen'),(subprocess,'run'),(multiprocessing.Process,'start'),(os,'system'),(fcntl,'flock'),
    (socket,'create_connection'),(urllib.request,'urlopen')]
def inspect(cell_id):
    began=time.monotonic();directory=ACTUAL/cell_id;descriptor=e.cell_descriptor(cell_id)
    cp_pin=pin(directory/'TERMINAL_CHECKPOINT.json');preliminary=OUT/(cell_id+'_PRELIMINARY.json')
    if preliminary.exists():
        pre=load(preliminary);assert pre['terminal_checkpoint_SHA256']==cp_pin['SHA256']
        checkpoint=load(directory/'TERMINAL_CHECKPOINT.json')
        assert all(digest(directory/name)==value for name,value in checkpoint['files'].items())
        receipt=load(directory/'CASE_RECEIPT.json');saved_validation_reused_from_exact_preliminary=True
    else:
        receipt=runner.validate_saved_terminal(directory,preparation_raw=PREP_RAW,preparation_directory=PREPDIR,
            cell_id=cell_id,expected_go_sha256=GO_SHA,expected_review_sha256=REVIEW_SHA)
        saved_validation_reused_from_exact_preliminary=False
    audit=load(directory/'ACCOUNT_FINANCIAL_AUDIT.json');result=load(directory/'NATIVE_RESULT.json')
    proof=load(directory/'NATIVE40_RECONSTRUCTION_PROOF.json');risk=load(directory/'ACTUAL_HELD_RISK_REPORT.json')
    quality=load(directory/'CAUSAL_MARK_QUALITY.json');legacy=load(directory/'LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json')
    binding=audit['historical_execution_scope'];expected=PREP['cells'][cell_id]
    assert binding['input_binding_SHA256']==expected['input_binding_SHA256']
    for key,value in dict(cell_id=cell_id,year=2021,strategy=descriptor['strategy'],tier_name=descriptor['tier'],config=descriptor['config'],
            preparation_SHA256=e._sha(PREP_RAW),source_identity=PREP['years']['2021']['source_identity'],
            code_identity_SHA256=e._json_sha(PREP['code_identity']),policy_identity=PREP['policy_identity'],independent_review_SHA256=REVIEW_SHA,
            root_GO_SHA256=GO_SHA,quality_sidecar_sha256=PREP['years']['2021']['quality_sidecar_sha256'],quality_intervals=[],
            calendar=[START,END],days=274,required_minutes=394560,generated_fixture_scope_used=False,fresh_genesis_only=True).items():
        assert e._same(binding.get(key),value),(cell_id,key)
    assert audit['bound_nominal_tier']==descriptor['tier'] and audit['contract']['scope_binding']==binding
    assert audit['historical_execution_admitted'] is True and audit['contract']['generated_only'] is False
    assert quality['identity']['intervals']==[] and quality['identity']['source_sidecar_sha256']==binding['quality_sidecar_sha256']
    assert not quality['receipts'] and quality['original_interpolated_marks_execution_admitted'] is False
    assert audit['config']['initial_cash']=='10000' and audit['config']['leverage']=='1'
    assert audit['contract']['free_cash_floor']=='1000' and audit['contract']['total_isolated_ceiling']=='8500'
    assert not audit['transfer_journal'] and not audit['transfer_ids'] and audit['contract']['topup_enabled'] is False
    assert audit['contract']['nominal_roundtrip_bps']==27.0
    assert audit['snapshot_recovery_certified'] is False and result['chronological_native40_saved_proof_required_before_terminal_admission'] is True
    assert proof['passed'] is True and proof['tolerance_or_epsilon_used'] is False
    assert result['legacy_delta_sum_reconciliation_is_authoritative'] is False and result['primary_financial_reconciliation']==legacy
    assert result['summary']['completed_minutes']==394560 and receipt['account_stop_us'] is None
    assert result['economics']['partial_DEV'] is True and result['economics']['partial_return_annualized'] is False
    assert result['economics']['annual_wallets_compounded'] is False and risk['complete_calendar_days']==274
    assert not audit['unpaid_liability'] or D(audit['unpaid_liability'])==0
    for s in S:
        profile=load(e.s.FROZEN/'sources/QUANTITY_PROFILE.json')['rows'][s]
        assert audit['instrument_profiles'][s]['quantity_step']==profile['quantity_step']
    # Source coverage is checked separately from native ownership. The first
    # five exact Apr2 flat events have no installed past mark and no charge.
    observed=result['funding'];funds=audit['funding']
    assert len(observed)==4110 and len(funds)==4105
    skipped=[];fund_by_key={(x['symbol'],x['event_us']):x for x in funds}
    assert len(fund_by_key)==4105
    source_funding_mark_checks=0
    for row in observed:
        key=row['symbol'],row['event_us'];source=SOURCE_BY_KEY[key]
        assert row['raw_rate']==source['raw_rate'] and row['reported_interval_hours']==source['reported_interval_hours']==8.0
        assert row['raw_rate_unit']=='UNCONFIRMED' and 'not_owned_under_fresh_CASH_start' not in row
        assert row['assumed_fraction_decimal']==str(D(str(source['raw_rate']))*D('1.0'))
        if key not in fund_by_key:
            assert row['event_us']==START and row['owned'] is False and row['quantity']==0 and row['signed_funding_USDT']==0
            assert row['status']=='NO_POSITION_NO_PAST_MARK' and row['mark_price'] is None
            skipped.append(key);continue
        f=fund_by_key[key];q=source['strict_prior_mark']
        assert f['mark_close_us']==q['mark_available_us']<f['event_us']
        assert D(f['decimal_strings']['mark_price'])==D(str(q['mark_close']))
        assert D(f['decimal_strings']['rate_fraction'])==D(str(source['raw_rate']))
        assert f['owned']==(D(f['decimal_strings']['quantity'])!=0)
        assert f['rate_available_us']==f['event_us'] and START<f['event_us']<END
        source_funding_mark_checks+=1
    assert len(skipped)==5 and {s for s,t in skipped}==set(S)
    trades=audit['trades'];paid=[x for x in trades if not x.get('liquidation_takeover')]
    assert all(START<=t['event_us']<END for t in trades)
    first_entry=min((x['event_us'] for x in paid if x['leg']=='OPEN'),default=None)
    assert first_entry is None or first_entry>=START+MINUTE+1
    first_owned=min((f['event_us'] for f in funds if f['owned']),default=None)
    assert first_owned is None or first_entry is not None and first_owned>=first_entry
    # Check actual paid mid-prices and aggregate same-open symbol capacity from
    # pinned local NPZ fields directly. This does not iterate a provider.
    load_quote_sources();by_open=defaultdict(lambda:D(0));coarse_checks=0
    with localcontext() as ctx:
        ctx.prec=40
        for trade in paid:
            assert (trade['event_us']-1)%MINUTE==0
            at=trade['event_us']-1;s=trade['symbol'];d=trade['decimal_strings'];amount=D(d['quantity'])
            assert D(d['execution_mid_price'])==D(str(source_quote(s,at,'open')))
            step=D(audit['instrument_profiles'][s]['quantity_step']);assert amount%step==0
            if trade['leg']=='OPEN':assert amount*D(d['fill_price'])>=D(10)
            by_open[s,at]+=amount;coarse_checks+=1
        for (s,at),amount in by_open.items():
            assert at>=START+MINUTE
            capacity=D(str(source_quote(s,at-MINUTE,'quote_volume')))*D('.001')/D(str(source_quote(s,at,'open')))
            assert amount<=capacity,(cell_id,s,at,'CAPACITY')
    terminal=[t for t in paid if t['signal_us']==END-61*MINUTE]
    assert all(END-60*MINUTE+1<=t['event_us']<=END-MINUTE+1 for t in terminal)
    warnings=[(r['event_us'],a) for r in audit['monitor_journal'] for a in r['actions'] if a['reason']=='GUARD50_PAID_EXIT_NO_TOPUP']
    warning_paid=0;warning_conditional=0
    for stamp,action in warnings:
        assert action['transferred']=='0' and action['full_actual_position_exit_required'] is True
        symbol=action['symbol'];closes=[t for t in paid if t['symbol']==symbol and t['leg']=='CLOSE' and t['signal_us']==stamp]
        if any(D(t['decimal_strings']['quantity_after'])==0 for t in closes):warning_paid+=1
        elif any(x['symbol']==symbol and x['event_us']>=stamp for x in audit['settlement_journal']):warning_conditional+=1
        else:raise ValueError('UNRESOLVED_SAVED_D_WARNING_EXIT:'+cell_id)
    assert pin(directory/'TERMINAL_CHECKPOINT.json')==cp_pin
    assert PREP['code_identity']==e.code_identity() and digest(REVIEW_PATH)==REVIEW_SHA and digest(GO_PATH)==GO_SHA
    record=dict(schema='INDEPENDENT_ACTUAL_ORIGINAL_D_PARTIAL2021_SAVED_CELL_REVIEW_V1',status='PASS_SAVED_ONLY_NO_FINANCIAL_RERUN',
        cell_id=cell_id,strategy=descriptor['strategy'],tier=descriptor['tier'],calendar=[START,END],days=274,completed_minutes=394560,
        root_GO_SHA256=GO_SHA,source_generated_review_SHA256=REVIEW_SHA,preparation_SHA256=e._sha(PREP_RAW),manifest_SHA256=e.MANIFEST_SHA256,
        source_identity=binding['source_identity'],input_binding_SHA256=binding['input_binding_SHA256'],code_identity=PREP['code_identity'],
        policy_identity=PREP['policy_identity'],quality_sidecar_SHA256=binding['quality_sidecar_sha256'],checker_SHA256=checker_sha256(),
        source_funding_coverage_events=4110,observed_funding_events=4110,native_applied_funding_events=4105,
        owned_funding_events=sum(f['owned'] for f in funds),initial_fresh_flat_unapplied_events=5,
        strict_prior_source_funding_mark_rate_clock_checks=source_funding_mark_checks,source_funding_coverage_is_not_charge_ownership=True,
        first_actual_paid_entry_us=first_entry,first_owned_funding_us=first_owned,no_charge_before_actual_exposure=True,
        exact_source_paid_mid_and_coarse_quantity_checks=coarse_checks,aggregate_source_shared_capacity_checks=len(by_open),
        terminal_signal_us=END-61*MINUTE,terminal_paid_legs=len(terminal),last_actual_paid_fill_us=max((x['event_us'] for x in paid),default=None),
        no_Jan1_execution_or_funding=True,D_warning_actions=len(warnings),paid_full_warning_exits=warning_paid,conditional_warning_takeovers=warning_conditional,
        transfers=0,unpaid_liability=audit['unpaid_liability'],conditional_settlements=len(audit['settlement_journal']),
        terminal_status=receipt['status'],economics=result['economics'],summary=result['summary'],actual_held_risk=risk,
        authoritative_native40_proof=proof,legacy_delta_sum_report_preserved=legacy,
        preliminary_exact_saved_validation_reused=saved_validation_reused_from_exact_preliminary,
        source_published_units_arrival_charge_price_and_venue_certified=False,partial_period_return_annualized=False,
        annual_or_cross_cell_wallets_compounded=False,nominal_tier_is_not_realized_risk_matching=True,
        review_account_constructions=0,review_financial_reruns=0,review_provider_iterations=0,review_process_launches=0,review_claims_created=0,review_GO_edits=0,
        root_process_exit_confirmed_by_reviewer=False,review_CPU_affinity=sorted(os.sched_getaffinity(0)),
        observed_helper_affinities=[sorted(os.sched_getaffinity(int(x.name))) for x in Path('/proc/self/task').iterdir()],
        maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,review_wall_seconds=time.monotonic()-began,
        evidence={name:pin(directory/name) for name in runner.TERMINAL_FILES},terminal_checkpoint=cp_pin,
        review_script=pin(__file__))
    save(OUT/(cell_id+'_SAVED_REVIEW.json'),record)
    print(json.dumps(dict(event='INDEPENDENT_SAVED_CELL_PASS',cell_id=cell_id,terminal_status=receipt['status'],paid_net_return=result['economics']['paid_net_return'],
        source_funding_applied=4105,owned_funding=sum(f['owned'] for f in funds),warnings=len(warnings),paid_source_quote_checks=coarse_checks,
        forecast_breach_minutes=risk['forecast_volatility_breach_minutes'])),flush=True)
    return record

with ExitStack() as stack:
    mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('SAVED_ONLY_FORBIDDEN:'+name))) for obj,name in blocked]
    records={}
    while len(records)<9:
        for cell_id in e.tranche_cells():
            if cell_id in records:continue
            if (ACTUAL/cell_id/'TERMINAL_CHECKPOINT.json').is_file():
                try:records[cell_id]=inspect(cell_id)
                except BaseException as error:
                    save(OUT/(cell_id+'_SAVED_REVIEW_FAILURE.json'),dict(status='INDEPENDENT_SAVED_REVIEW_BLOCKED',cell_id=cell_id,error=repr(error),
                        review_account_constructions=0,review_financial_reruns=0,review_provider_iterations=0,review_GO_edits=0))
                    print(json.dumps(dict(event='INDEPENDENT_SAVED_REVIEW_BLOCKED',cell_id=cell_id,error=repr(error))),flush=True);raise
        pauses=list(ACTUAL.glob('CONTROLLER_PAUSE_*.json'))
        if pauses and len(records)<9:
            print(json.dumps(dict(event='ROOT_CONTROLLER_PAUSED',reviewed_cells=list(records),pause_files=[str(x) for x in pauses])),flush=True)
            break
        if len(records)<9:time.sleep(5)
    for mock in mocks:mock.assert_not_called()
    boundary_counts=[dict(boundary=obj.__name__+'.'+name,calls=mock.call_count) for (obj,name),mock in zip(blocked,mocks)]
    if len(records)==9:
        rows=[]
        for cell_id in e.tranche_cells():
            r=records[cell_id];economics=r['economics'];risk=r['actual_held_risk']
            rows.append(dict(cell_id=cell_id,strategy=r['strategy'],tier=r['tier'],terminal_status=r['terminal_status'],days=274,minutes=394560,
                paid_net_return=economics['paid_net_return'],terminal_NAV=r['summary']['decimal_strings']['NAV'],
                all_observation_MDD=economics['all_observation_max_drawdown'],fees_USDT=economics['fees_USDT'],
                execution_cost_USDT=economics['execution_cost_USDT'],funding_USDT=economics['funding_USDT'],
                trade_legs=r['summary']['trade_legs'],owned_funding_events=r['owned_funding_events'],D_warning_actions=r['D_warning_actions'],
                conditional_settlements=r['conditional_settlements'],unpaid_liability=r['unpaid_liability'],
                forecast_annual_volatility_max=risk['forecast_annual_volatility_max'],forecast_breach_minutes=risk['forecast_volatility_breach_minutes'],
                gross_exposure_max=risk['gross_exposure_max'],actual_realized_daily_simple_return_annual_volatility=risk['realized_daily_simple_return_annual_volatility']))
        aggregate=dict(schema='INDEPENDENT_ACTUAL_ORIGINAL_D_PARTIAL2021_NINE_SAVED_REVIEW_V1',status='PASS_ALL_NINE_SAVED_TERMINALS_NO_FINANCIAL_RERUN',
            root_GO_SHA256=GO_SHA,source_generated_review_SHA256=REVIEW_SHA,preparation_SHA256=e._sha(PREP_RAW),manifest_SHA256=e.MANIFEST_SHA256,
            ordered_cells=list(e.tranche_cells()),calendar=[START,END],days_per_fresh_wallet=274,initial_USDT_per_separate_wallet='10000',
            reviewed_cell_count=9,aggregate_native_minutes_checked=9*394560,alias_mapping={},all_nine_executed_separately=True,
            aggregate_is_a_matrix_of_nine_separate_accounts_not_one_portfolio_or_compounded_account=True,
            partial_period_return_annualized=False,cross_year_or_cross_cell_wallet_compounding=False,nominal_tiers_not_realized_risk_matching=True,
            saved_only=True,account_constructions=0,financial_reruns=0,provider_iterations=0,process_launches=0,claims_created=0,GO_edits=0,
            root_process_exit_confirmed_by_reviewer=False,parent_root_owns_exit_confirmation=True,review_CPU_affinity=[6],
            numerical_threads={k:os.environ[k] for k in runner.THREAD_ENV},prohibited_boundary_call_counts=boundary_counts,
            source_units_publication_arrival_exact_venue_charge_price_and_native_venue_certified=False,
            rows=rows,cell_review_receipts={cell:pin(OUT/(cell+'_SAVED_REVIEW.json')) for cell in e.tranche_cells()},
            review_script=pin(__file__),original_source_generated_review_bytes_preserved=digest(REVIEW_PATH)==REVIEW_SHA)
        save(OUT/'INDEPENDENT_NINE_SAVED_REVIEW.json',aggregate)
        print(json.dumps(dict(event='INDEPENDENT_ALL_NINE_SAVED_PASS',receipt=str(OUT/'INDEPENDENT_NINE_SAVED_REVIEW.json'),SHA256=digest(OUT/'INDEPENDENT_NINE_SAVED_REVIEW.json'))),flush=True)
