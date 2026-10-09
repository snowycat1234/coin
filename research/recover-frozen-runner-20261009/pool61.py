"""Two fixed original E5 one-hot requests, on separate bounded native wallets."""
import argparse
from datetime import datetime, UTC
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import types

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native61 as frozen

POLICIES = {'SMA50_200_SIGNED': 2, 'DONCHIAN_EXIT10': 3}
INPUT_SHA = '9290615ff090e1560d5fe5823e2b721a93f3079c2f060ebff96a07df548e81e9'


def target_paths(state):
    import numpy as np
    mapper = frozen.modules(state)
    root = state / 'h1_validation/original/h1_market'
    source = frozen.read(root / 'reports/SOURCE_IDENTITY.json')
    for name, digest in source['verified_used_recipe_hashes'].items():
        frozen.require(frozen.sha(frozen.REPO / name) == digest, 'Original E5 recipe differs: ' + name)
    path = root / 'inputs/H1_E5_INPUTS.npz'
    frozen.require(frozen.sha(path) == INPUT_SHA, 'Original target/context NPZ differs')
    with np.load(path, allow_pickle=False) as z:
        a = {k: z[k].copy() for k in z.files}
    decisions = np.arange(frozen.START, frozen.END, frozen.DAY, dtype=np.int64)
    ix = np.searchsorted(a['decision_us'], decisions)
    frozen.require(np.array_equal(a['decision_us'][ix], decisions), 'Exact61 decision dates required')
    frozen.require(a['expert_order'].tolist() == ['CASH','VOL_MANAGED_HOLD','PUBLIC_SMA50_200_SIGNED','DONCHIAN_EXIT10','CSMOM21'], 'Original E5 identity/order required')
    frozen.require(a['symbol_order'].tolist() == list(frozen.SYMBOLS), 'Ordered CORE5 required')
    frozen.require(a['expert_eligible'][ix].all() and a['expert_asset_eligible'][ix].all(), 'No unavailable expert or asset permitted')
    frozen.require(np.all(a['target_available_us'][ix] <= decisions[:,None]), 'Causal original target clocks required')
    frozen.require(np.isfinite(a['expert_targets'][ix]).all() and np.isfinite(a['past_returns30'][ix]).all(), 'Finite actual original contexts required')
    frozen.require((a['expert_targets'][ix,3] >= 0).all(), 'Original Donchian exit10 is long only')
    arms, report = {}, {}
    for policy, k in POLICIES.items():
        prior = np.array([1.,0.,0.,0.,0.])
        request = np.eye(5)[k]
        fractions, budgets = [], []
        for row, t in zip(ix, decisions, strict=True):
            frozen.require(np.array_equal(a['action_desired_budgets'][row,k], request), 'Original one-hot action differs')
            context = types.SimpleNamespace(decision_us=int(t), expert_eligible=a['expert_eligible'][row],
                expert_targets=a['expert_targets'][row], past_returns30=a['past_returns30'][row], binding={'symbol_order':list(frozen.SYMBOLS)})
            proposal = mapper.mapper(prior, request, context)
            budget, fraction = np.array(proposal.budget), np.array(proposal.targets)
            frozen.require(np.abs(budget-prior).sum() <= .1+1e-10, 'Original budget ramp required')
            if t == decisions[-1]:
                fraction *= 0
            fractions.append(fraction); budgets.append(budget); prior = budget
        fractions, budgets = np.array(fractions), np.array(budgets)
        arms[policy] = fractions, budgets
        report[policy] = dict(expert_name=a['expert_order'][k].item(), context_origin='EXACT_SAVED_H1_E5_TARGETS_AND_COVARIANCE',
            request=request.tolist(), days=61, fractions_f64_bytes_sha256=hashlib.sha256(fractions.tobytes()).hexdigest(),
            budgets_f64_bytes_sha256=hashlib.sha256(budgets.tobytes()).hexdigest(), maximum_abs_target=float(abs(fractions).max()),
            maximum_gross_target=float(abs(fractions).sum(1).max()), final_day_zero=bool((fractions[-1]==0).all()))
    return arms, report


def check(state):
    _, report = target_paths(state)
    old = frozen.read(HERE / 'NATIVE61_PLAN.json')
    for name, digest in old['source_sha256'].items():
        frozen.require(frozen.sha(frozen.REPO / name) == digest, 'Unchanged financial dependency required: ' + name)
    preflight = state / 'h1_validation/PREFLIGHT61.json'
    frozen.require(frozen.sha(preflight) == old['preflight_sha256'], 'Completed actual market preflight differs')
    market_root = state / 'h1_validation/original/h1_market'
    for r in frozen.read(market_root / 'reports/DATASET_MANIFEST.json')['artifacts']:
        p = market_root / r['relative_path']
        frozen.require(p.stat().st_size == r['bytes'] and frozen.sha(p) == r['sha256'], 'Original market bytes differ')
    return dict(status='PASS_EXACT_ORIGINAL_E5_ONEHOT_CONTEXTS_AND_FINANCIAL_SOURCE', original_input_sha256=INPUT_SHA,
        source_market_preflight_sha256=frozen.sha(preflight), policy_checks=report, new_wallets=0, fits=0, tuning=0, provider_downloads=0)


def run(state, policy, output, commit):
    plan_path = HERE / 'POOL61_PLAN.json'
    plan = frozen.read(plan_path)
    committed = subprocess.check_output(['git','-C',str(frozen.REPO),'show',commit+':research/recover-frozen-runner-20261009/POOL61_PLAN.json'])
    frozen.require(committed == plan_path.read_bytes(), 'Published pool61 plan required')
    for name, digest in plan['source_sha256'].items():
        frozen.require(frozen.sha(frozen.REPO/name) == digest, 'Published source differs: ' + name)
    preflight = check(state)
    frozen.require(preflight == frozen.read(HERE/'POOL61_PREFLIGHT.json'), 'Published exact target/data gate differs')
    arms, _ = target_paths(state)
    fractions, budgets = arms[policy]
    from scripts.investment import perpetual_directional as old
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    frozen.require(old.COSTS[0] == plan['cost'], 'Frozen cost contract differs')
    sim = NativeDailySimulator(frozen.market(state),'LONG_SHORT',old.COSTS[0],dict(id='RAW_AS_FRACTION',scale=1.),
        account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.budget = [1.,0.,0.,0.,0.]
    frozen.require(float(sim.account.nav()) == 10000 and not output.exists(), 'Fresh independent10000 wallet required')
    output.mkdir(parents=True,exist_ok=False)
    receipt = dict(policy=policy,plan_commit=commit,started_UTC=datetime.now(UTC).isoformat(),limits=plan['limits'])
    (output/'STARTED.json').write_text(json.dumps(receipt,indent=2)+'\n')
    status, error, start = 'RUNNING', None, time.monotonic()
    def alarm(signum,frame):
        raise TimeoutError('600-second wallet cap')
    signal.signal(signal.SIGALRM,alarm); signal.setitimer(signal.ITIMER_REAL,600)
    try:
        for i in range(61):
            frozen.require(shutil.disk_usage(output).free >= 15*2**30, '15GiB disk reserve required')
            sim.budget = budgets[i].tolist()
            actual = sim.advance_day(dict(zip(frozen.SYMBOLS,fractions[i],strict=True)))
            frozen.require(actual['completed'], 'Incomplete native day must stop')
            if (i+1)%10 == 0 or i == 60:
                print(json.dumps(dict(policy=policy,completed_days=i+1,total_days=61,NAV=float(sim.account.nav()))),flush=True)
        frozen.require(sim.rows_written == 87840 and all(p.quantity == 0 for p in sim.account.positions.values()), 'Complete paid terminal flat required')
        status = 'COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:
        status, error = 'FAILED_PREFIX_RETAINED', dict(type=type(e).__name__,message=str(e))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        saved = old.save_case(sim.result(),output/'account')
        (output/'account/summary.json').write_text(json.dumps(saved['summary'],indent=2)+'\n')
        receipt.update(status=status,error=error,finished_UTC=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,completed_minutes=sim.rows_written,
            original_engine_sha256=frozen.sha(frozen.REPO/'scripts/investment/resumable_perpetual.py'),audit='PENDING_INDEPENDENT_RECONCILIATION')
        (output/'EXECUTION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:saved['summary'][k] for k in ('NAV','net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','completed_minutes','terminal_cash_realized','liquidation_count')}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('check','run'));p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--policy',choices=POLICIES);p.add_argument('--plan-commit');a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6_000_000_000,6_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
    def blocked(*args,**kwargs):raise RuntimeError('Offline wallet forbids network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    frozen.modules(a.state)
    if a.command=='check':
        report=check(a.state);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    else:
        frozen.require(a.policy is not None and a.plan_commit is not None,'Explicit fixed policy and published plan required')
        run(a.state,a.policy,a.output,a.plan_commit)


if __name__=='__main__':main()
