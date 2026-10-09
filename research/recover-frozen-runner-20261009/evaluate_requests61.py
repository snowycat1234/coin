"""Strict frozen-request adapter for the unchanged native May-June61 account."""
import argparse
from datetime import datetime, UTC
import hashlib, json, os, re
from pathlib import Path, PurePosixPath
import resource, shutil, signal, socket, subprocess, sys, time, types, zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen

E5=('CASH','VOL_MANAGED_HOLD','PUBLIC_SMA50_200_SIGNED','DONCHIAN_EXIT10','CSMOM21')
COMPACT=(E5[0],E5[1],E5[4])
SHORT='MOMENTUM30_SHORT_ONLY'
INPUT_SHA='9290615ff090e1560d5fe5823e2b721a93f3079c2f060ebff96a07df548e81e9'
SHORT_SHA='89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d'
SCHEMA='SOURCE_HASHED_FROZEN_NATIVE61_REQUESTS_V1'


def digest(value):
    frozen.require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'Exact lowercase SHA256 required')
    return value


def clock(value,shape,name):
    import numpy as np
    a=np.asarray(value)
    frozen.require(a.dtype==np.dtype('int64') and a.shape==shape and (a>=0).all(),name+' requires nonnegative int64 microseconds')
    return a


def member(root,name):
    frozen.require(isinstance(name,str) and name and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and '\\' not in name,'Relative bundle member required')
    p=(root/name).resolve();frozen.require(p.is_relative_to(root.resolve()),'Bundle symlink escape rejected');return p


def load_bundle(path,expected):
    import numpy as np
    frozen.require(path.stat().st_size<262144 and frozen.sha(path)==digest(expected),'Externally pinned request manifest differs')
    m=frozen.read(path);frozen.require(m['schema']==SCHEMA and re.fullmatch('[A-Za-z0-9_]{1,64}',m['arm_id']),'Explicit request schema and arm identity required')
    frozen.require(type(m['objective_version']) is int and m['objective_version']==2 and m['prediction_role']=='HISTORICAL_FROZEN_REPLAY_NOT_LIVE_PREDICTIONS','Explicit daily surrogate v2 and retrospective prediction role required')
    frozen.require(isinstance(m['source_files'],list) and m['source_files'] and len(set(m['source_files']))==len(m['source_files']),'Hashed producer sources required')
    frozen.require(any(PurePosixPath(n).suffix=='.py' for n in m['source_files']),'At least one actual producer Python source member required')
    frozen.require(all(n in m['files'] for n in [m['request_file'],*m['source_files']]),'Missing bound producer/request member')
    for n,v in m['files'].items():
        p=member(path.parent,n);frozen.require(type(v['bytes']) is int and v['bytes']>=0 and p.stat().st_size==v['bytes'] and frozen.sha(p)==digest(v['sha256']),'Source-hashed bundle member differs: '+n)
    for k in ('model_sha256','scaler_sha256','training_plan_sha256'):digest(m[k])
    frozen.require(re.fullmatch('[0-9a-f]{40}',m['producer_commit']) is not None,'Exact producer commit required')
    for k in ('training_cutoff_us','maximum_training_label_available_us','maximum_scaler_input_available_us'):
        frozen.require(type(m[k]) is int and m[k]>=0,'Explicit nonnegative training clock required')
    frozen.require(m['maximum_training_label_available_us']<m['training_cutoff_us']<=frozen.START and m['maximum_scaler_input_available_us']<=m['training_cutoff_us'],'Training labels/scaler cross the pre-May cutoff')
    actual_fit=datetime.fromisoformat(m['actual_fit_completed_UTC']);frozen.require(actual_fit.tzinfo is not None,'Actual fit timestamp must retain timezone; never backdate the2026fit')
    frozen.require(actual_fit<=datetime.now(UTC),'Actual fit completion is in the future')
    request=member(path.parent,m['request_file']);frozen.require(request.stat().st_size<4*2**20,'Request NPZ exceeds bounded input size')
    with zipfile.ZipFile(request) as z:frozen.require(sum(v.file_size for v in z.infolist())<=8*2**20,'Request NPZ decompression limit exceeded')
    with np.load(request,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    return m,a


def contexts(state,extended):
    import numpy as np
    p=state/'h1_validation/original/h1_market/inputs/H1_E5_INPUTS.npz';frozen.require(frozen.sha(p)==INPUT_SHA,'Original E5 contexts differ')
    with np.load(p,allow_pickle=False) as z:
        tt=np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64);ix=np.searchsorted(z['decision_us'],tt)
        frozen.require(np.array_equal(z['decision_us'][ix],tt) and z['expert_order'].tolist()==list(E5) and z['symbol_order'].tolist()==list(frozen.SYMBOLS),'Original E5 slot/calendar/symbol identity differs')
        c={k:z[k][ix].copy() for k in ('expert_targets','expert_eligible','target_available_us','past_returns30')}
    order=E5
    if extended:
        p=HERE/'short-candidate-contexts/DEV61_MOMENTUM_SHORT_CONTEXTS.npz';frozen.require(frozen.sha(p)==SHORT_SHA,'Frozen momentum short context differs')
        with np.load(p,allow_pickle=False) as z:
            frozen.require(np.array_equal(z['decision_us'],tt) and z['expert_order'].tolist()==[SHORT] and z['symbol_order'].tolist()==list(frozen.SYMBOLS),'Appended short identity differs')
            for key in ('expert_targets','expert_eligible','target_available_us'):c[key]=np.concatenate([c[key],z[key]],axis=1)
        order=E5+(SHORT,)
    c['expert_order']=order
    frozen.require(c['expert_eligible'].dtype==bool and c['expert_eligible'][:,0].all() and (c['target_available_us']<=tt[:,None]).all() and np.isfinite(c['expert_targets']).all() and np.isfinite(c['past_returns30']).all(),'Canonical context masks/clocks/values invalid')
    return c


def validate(m,a,c):
    import numpy as np
    required={'decision_us','symbol_order','expert_order','action_eligible','desired_expert_budget','feature_available_us','request_available_us'}
    optional={'feedback_available_us','ramped_expert_budget','mapper_target_fractions'}
    frozen.require(required<=set(a) and set(a)<=required|optional,'Unknown/missing request fields; contexts are loaded from canonical inputs')
    tt=clock(a['decision_us'],(61,),'decision_us');frozen.require(np.array_equal(tt,np.arange(frozen.START,frozen.END,frozen.DAY,dtype=np.int64)),'Exact continuous May1-July1exclusive61 decisions required')
    order=tuple(a['expert_order'].tolist());frozen.require(order in (COMPACT,E5,COMPACT+(SHORT,),E5+(SHORT,)) and list(order)==m['expert_order'],'Unsupported order; preserve original E5 slots and append short only')
    extended=SHORT in order;canonical=E5+(SHORT,) if extended else E5;frozen.require(tuple(c['expert_order'])==canonical,'Declared extension differs from canonical context')
    frozen.require(c['expert_targets'].shape==(61,len(canonical),5) and c['expert_eligible'].shape==(61,len(canonical)) and c['expert_eligible'].dtype==bool and c['expert_eligible'][:,0].all() and c['past_returns30'].shape==(61,30,5),'Canonical context dimensions/CASH eligibility invalid')
    frozen.require((clock(c['target_available_us'],(61,len(canonical)),'canonical target availability')<=tt[:,None]).all() and np.isfinite(c['expert_targets']).all() and np.isfinite(c['past_returns30']).all(),'Canonical target/covariance clocks or values invalid')
    frozen.require(a['symbol_order'].tolist()==list(frozen.SYMBOLS),'Exact ordered CORE5 required')
    allowed=m['allowed_actions'];frozen.require(isinstance(allowed,list) and allowed and len(set(allowed))==len(allowed) and set(allowed)<=set(order),'Explicit unique admitted actions required')
    slots=[canonical.index(n) for n in order];mask=np.asarray(a['action_eligible'])
    expected=c['expert_eligible'][:,slots]&np.array([n in allowed for n in order])[None]
    frozen.require(mask.dtype==bool and mask.shape==(61,len(order)) and np.array_equal(mask,expected) and mask.any(1).all(),'Action mask differs from admitted actions/canonical eligibility')
    request=np.asarray(a['desired_expert_budget']);frozen.require(request.dtype==np.dtype('float64') and request.shape==mask.shape and np.isfinite(request).all() and (request>=0).all() and np.allclose(request.sum(1),1,atol=1e-12,rtol=0) and (request[~mask]==0).all(),'Finite normalized float64 requests must respect exact action masks')
    feature=clock(a['feature_available_us'],(61,),'feature_available_us');available=clock(a['request_available_us'],(61,),'request_available_us')
    frozen.require((feature<=available).all() and (available<=tt).all(),'Future feature/request clock rejected')
    frozen.require(type(m['uses_feedback_features']) is bool and ('feedback_available_us' in a)==m['uses_feedback_features'],'Feedback provenance declaration differs')
    if 'feedback_available_us' in a:frozen.require((clock(a['feedback_available_us'],(61,),'feedback_available_us')<tt).all(),'Feedback must be strictly past')
    frozen.require(('ramped_expert_budget' in a)==('mapper_target_fractions' in a),'Exported mapper parity fields must come as a pair')
    full=np.zeros((61,len(canonical)));full[:,slots]=request
    return full,dict(export_order=list(order),canonical_order=list(canonical),explicit_E5_slots=slots,short_extension=extended,days=61,action_mask_verified=True)


def mapped(full,c,original_mapper):
    import numpy as np
    from scripts.investment.regime_ranking_screen import bounded_path
    from scripts.research.conditional_selector_core import shared_targets
    import polars as pl
    prior=np.zeros(full.shape[1]);prior[0]=1;fractions=[];budgets=[]
    for i,t in enumerate(range(frozen.START,frozen.END,frozen.DAY)):
        context=types.SimpleNamespace(decision_us=t,expert_eligible=c['expert_eligible'][i],expert_targets=c['expert_targets'][i],past_returns30=c['past_returns30'][i],binding={'symbol_order':list(frozen.SYMBOLS)})
        if full.shape[1]==5:
            proposal=original_mapper(prior,full[i],context);budget=np.asarray(proposal.budget);target=np.asarray(proposal.targets)
        else:
            # Explicit new append-only adapter, using the identical original
            # eligibility release, bounded_path and shared_targets operations.
            eligible=context.expert_eligible;released=prior.copy();released[0]+=released[~eligible].sum();released[~eligible]=0
            desired=full[i].copy();desired[0]+=desired[~eligible].sum();desired[~eligible]=0
            budget=bounded_path([desired],released,.1)[0];names=tuple(c['expert_order'][k] for k in np.flatnonzero(eligible))
            frames={c['expert_order'][k]:pl.DataFrame([dict(available_us=t,symbol=s,target_weight=float(context.expert_targets[k,j]),raw_signed_target=float(context.expert_targets[k,j]),mode='LONG_SHORT',eligibility_reason='ELIGIBLE') for j,s in enumerate(frozen.SYMBOLS)]) for k in np.flatnonzero(eligible)}
            frame,_=shared_targets(frames,names,np.array([t],np.int64),frozen.SYMBOLS,budget[None,eligible]);target=frame['target_weight'].to_numpy()
        frozen.require(abs(budget-prior).sum()<=.1+1e-10 and (budget>=0).all() and abs(budget.sum()-1)<1e-12,'Original daily simplex/ramp violated')
        cov=np.cov(context.past_returns30,rowvar=False,ddof=1)*365
        frozen.require(np.isfinite(target).all() and abs(target).sum()<=.6+1e-12 and abs(target).max()<=.3+1e-12 and target@cov@target<=.1**2+1e-12,'Original target/covariance caps violated')
        if i==60:target=target*0
        fractions.append(target);budgets.append(budget.copy());prior=budget.copy()
    return np.asarray(fractions),np.asarray(budgets)


def source_market_check(state):
    contract=frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json')
    for n,h in contract['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==h,'Frozen adapter/financial source differs: '+n)
    public=frozen.read(HERE/'NATIVE61_PLAN.json')['public_input'];base=state/'h1_validation/original'
    for p,h in [(base/'h1_market/reports/DATASET_MANIFEST.json',public['data_manifest_sha256']),(base/'source_increment/modules/native_action/e5_inputs.py',public['original_mapper_sha256']),
                (state/'e5-bear-original/source_increment/modules/native_action/e5_teacher.py',public['original_mapper_teacher_sha256']),(state/'h1_validation/PREFLIGHT61.json',contract['retained_preflight_sha256'])]:frozen.require(frozen.sha(p)==h,'Retained market/mapper proof differs')
    m=frozen.read(base/'h1_market/reports/DATASET_MANIFEST.json')
    for r in m['artifacts']:
        p=base/'h1_market'/r['relative_path'];frozen.require(p.stat().st_size==r['bytes'] and frozen.sha(p)==r['sha256'],'Retained actual market bytes differ')
    return dict(status='PASS_REUSED_EXACT_INPUT_GRID_PROOF_WITH_CURRENT_IDENTICAL_SOURCE_BYTES',registered_files=len(m['artifacts']),original_engine_sha256=contract['engine_sha256'],minutes=87840,funding_events=915)


def check(state,manifest,expected):
    import numpy as np
    source=source_market_check(state);m,a=load_bundle(manifest,expected);mapper=frozen.modules(state)
    c=contexts(state,SHORT in m['expert_order']);full,report=validate(m,a,c);fractions,budgets=mapped(full,c,mapper.mapper)
    if 'ramped_expert_budget' in a:
        slots=report['explicit_E5_slots'];b=a['ramped_expert_budget'];f=a['mapper_target_fractions']
        frozen.require(b.shape==(61,len(slots)) and f.shape==(61,5) and np.isfinite(b).all() and np.isfinite(f).all() and np.array_equal(b,budgets[:,slots]) and np.array_equal(f,fractions),'Frozen export vs current native mapper parity mismatch')
    report.update(status='PASS_FROZEN_REQUESTS_AND_CURRENT_NATIVE61_MAPPING_NO_WALLET',source_check=source,manifest_sha256=expected,request_payload_sha256=m['files'][m['request_file']]['sha256'],arm_id=m['arm_id'],
        fractions_f64_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),budgets_f64_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(),fits=0,wallets_run=0)
    return m,fractions,budgets,report


def audit(directory,state):
    import polars as pl
    import verify_native61
    trades=frozen.read(directory/'account/trades.json')
    if trades:return verify_native61.verify(directory,state)
    # A legitimately inactive request path has no fictitious paid close.
    from modules.transformer_v3.isolated_audit import verify as financial
    a=financial(directory/'account',list(frozen.SYMBOLS),1);s=frozen.read(directory/'account/summary.json');e=frozen.read(directory/'EXECUTION.json');funds=frozen.read(directory/'account/funding.json')
    frozen.require(a['minutes']==s['completed_minutes']==s['required_minutes']==87840 and s['completion']==e['status']=='COMPLETE_CONDITIONAL_ACCOUNT','Complete inactive61 account required')
    frozen.require(s['terminal_cash_realized'] and s['terminal_not_forced_free_fill'] and all(p['quantity']==0 for p in s['positions'].values()) and s['NAV']==10000 and all(s[k]==0 for k in ('fees_USDT','execution_cost_USDT','funding_USDT','net_PnL','liquidation_count')),'Inactive account has financial activity')
    frozen.require(e['elapsed_seconds']<=600 and e['peak_RSS_bytes']<=6000000000 and len(funds)==s['funding_original_events']==915,'Inactive source/resource calendar differs')
    rates={}
    for symbol in frozen.SYMBOLS:
        d=pl.read_parquet(state/'h1_validation/original/h1_market/data/normalized'/(symbol+'_funding_events.parquet'))
        rates.update({(symbol,int(r['calc_time_ms'])*1000):float(r['last_funding_rate']) for r in d.iter_rows(named=True) if frozen.START<=int(r['calc_time_ms'])*1000<frozen.END})
    frozen.require(len({(r['symbol'],r['event_us']) for r in funds})==915 and {(r['symbol'],r['event_us']) for r in funds}==set(rates),'Inactive actual funding events differ')
    frozen.require(all(r['raw_rate']==rates[r['symbol'],r['event_us']] and r['conditional_rate_scale']==1 and not r['owned'] and r['quantity']==0 and r['signed_funding_USDT']==0 for r in funds),'Inactive original signed funding differs')
    a.update(continuous_days=61,capital_USDT=10000,terminal_paid_flat=True,liquidations=0,account_stitching=False,activity='INACTIVE_ZERO_TRADING_NOT_ALPHA',actual_input_check=dict(status='PASS_ZERO_POSITION_ACTUAL_RAW_FUNDING_CALENDAR',funding_events=915,ordinary_fill_legs=0))
    return a


def run(state,manifest,expected,output,execution_plan,plan_hash,commit):
    import numpy as np
    frozen.require(frozen.sha(execution_plan)==digest(plan_hash),'Pinned future execution plan differs')
    relative=execution_plan.resolve().relative_to(frozen.REPO).as_posix()
    frozen.require(subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':'+relative])==execution_plan.read_bytes(),'Published future request-specific execution plan required')
    plan=frozen.read(execution_plan);frozen.require(plan['request_manifest_sha256']==expected and plan['adapter_contract_sha256']==frozen.sha(HERE/'EVALUATE_REQUESTS61_ADAPTER.json'),'Future plan/request/adapter binding differs')
    m,fractions,budgets,gate=check(state,manifest,expected);frozen.require(plan['arm_id']==m['arm_id'] and not output.exists(),'Fresh explicitly planned arm required')
    ledger=state/'native61-request-ledger'/expected;ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open('x') as f:f.write('RESERVED_FROZEN_REQUEST_IDENTITY\n')
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    contract=frozen.read(HERE/'EVALUATE_REQUESTS61_ADAPTER.json');sim=NativeDailySimulator(frozen.market(state),'LONG_SHORT',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.budget=[1.]+[0.]*(budgets.shape[1]-1);frozen.require(float(sim.account.nav())==10000 and old.COSTS[0]==contract['cost'],'Original fresh account/cost differs')
    output.mkdir(parents=True,exist_ok=False);receipt=dict(policy=m['arm_id'],request_manifest_sha256=expected,request_payload_sha256=gate['request_payload_sha256'],plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=contract['limits'],export_provenance=m)
    (output/'STARTED.json').write_text(json.dumps(receipt,indent=2)+'\n');(output/'REQUEST_GATE.json').write_text(json.dumps(gate,indent=2)+'\n')
    status='RUNNING';error=None;start=time.monotonic()
    def alarm(s,f):raise TimeoutError('600-second native61 request evaluation cap')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(61):
            frozen.require(shutil.disk_usage(output).free>=15*2**30,'15GiB reserve required');sim.budget=budgets[i].tolist()
            frozen.require(sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))['completed'],'Incomplete request wallet must stop')
            if (i+1)%10==0 or i==60:print(json.dumps(dict(arm=m['arm_id'],completed_days=i+1,total_days=61,NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written==87840 and all(p.quantity==0 for p in sim.account.positions.values()),'Full61 paid terminal flat required');status='COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as ex:status='FAILED_PREFIX_RETAINED';error=dict(type=type(ex).__name__,message=str(ex));raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);saved=old.save_case(sim.result(),output/'account');(output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        receipt.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,original_engine_sha256=contract['engine_sha256'],audit='PENDING_POST_RUN_INDEPENDENT_RECONCILIATION')
        (output/'EXECUTION.json').write_text(json.dumps(receipt,indent=2)+'\n');ledger.write_text(json.dumps(dict(status=status,request_manifest_sha256=expected))+'\n')
    from pyarrow.parquet import read_table
    actual=read_table(output/'account/targets.parquet')['target_weight'].to_numpy().reshape(61,5);frozen.require(np.array_equal(actual,fractions),'Saved account targets differ from frozen mapped requests')
    report=audit(output,state);report['mapped_request_targets_exact']=True
    with (output/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    ledger.write_text(json.dumps(dict(status='COMPLETE_AND_AUDITED',request_manifest_sha256=expected))+'\n');print(json.dumps(dict(status='COMPLETE_AND_AUDITED',arm=m['arm_id'],net_PnL=saved['summary']['net_PnL'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('readiness','check','run'));p.add_argument('--state',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--manifest-sha256');p.add_argument('--output',type=Path);p.add_argument('--execution-plan',type=Path);p.add_argument('--execution-plan-sha256');p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*a,**kw):raise RuntimeError('Offline native evaluation forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    if a.command=='readiness':print(json.dumps(source_market_check(a.state)|dict(requests='NOT_YET_PROVIDED',wallets_run=0,fits=0)),flush=True)
    else:
        frozen.require(a.manifest is not None and a.manifest_sha256 is not None,'Actual frozen request manifest and external SHA required; no fallback policy')
        if a.command=='check':print(json.dumps(check(a.state,a.manifest,a.manifest_sha256)[3]),flush=True)
        else:
            frozen.require(all(v is not None for v in (a.output,a.execution_plan,a.execution_plan_sha256,a.plan_commit)),'Actual output and published request-specific execution plan required')
            run(a.state,a.manifest,a.manifest_sha256,a.output,a.execution_plan,a.execution_plan_sha256,a.plan_commit)
