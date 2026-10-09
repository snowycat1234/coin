"""Original E5 mapper parity and bounded native61 replay; no fitting."""
import argparse
from datetime import datetime, UTC
import hashlib
import importlib.util
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
REPO = HERE.parents[1]
START, END, DAY, MINUTE = 1714521600000000, 1719792000000000, 86400000000, 60000000
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
POLICIES = ('NO_CASH', 'WITH_CASH', 'STATIC50', 'CASH50')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def modules(state):
    os.environ['QUANT_ROOT'] = str(REPO)
    sys.path[:0] = [str(REPO / 'src'), str(REPO)]
    load('scripts.research.conditional_selector_core', HERE / 'auxiliary/conditional_selector_core.py')
    package = types.ModuleType('recovered_e5')
    package.__path__ = [str(state / 'e5-bear-original/source_increment/modules/native_action')]
    sys.modules['recovered_e5'] = package
    return load('recovered_e5.e5_inputs', state / 'h1_validation/original/source_increment/modules/native_action/e5_inputs.py')


def targets(state, handoff):
    import numpy as np
    mapper = modules(state)
    original = np.load(state / 'h1_validation/original/h1_market/inputs/H1_E5_INPUTS.npz', allow_pickle=False)
    manifest = read(handoff / 'MANIFEST.json')
    for name, r in manifest['files'].items():
        require((handoff / name).stat().st_size == r['bytes'] and sha(handoff / name) == r['SHA256'], 'Frozen handoff member differs')
    arms, report = {}, {}
    for policy in POLICIES:
        a = np.load(handoff / 'requests' / ((policy if policy in POLICIES[:2] else 'NO_CASH') + '_NATIVE61_REQUESTS.npz'), allow_pickle=False)
        require(a['symbol_order'].tolist() == list(SYMBOLS) and np.array_equal(a['decision_us'], np.arange(START, END, DAY)), 'Exact calendar/symbol order required')
        index = np.searchsorted(original['decision_us'], a['decision_us'])
        for key in ('expert_targets', 'expert_eligible', 'target_available_us', 'past_returns30'):
            require(np.array_equal(a[key], original[key][index]), 'Original H1 source differs: ' + key)
        require(np.array_equal(a['feature_available_us'], original['market_state13_available_us'][index]), 'Original feature clocks differ')
        require(np.array_equal(a['completed_decision_daily_close'], original['market_close'][index]), 'Original completed daily prices differ')
        require(np.all(a['target_available_us'] <= a['decision_us'][:, None]) and np.all(a['feature_available_us'] <= a['decision_us']), 'Future source clock rejected')
        requests = a['desired_expert_budget'] if policy in POLICIES[:2] else np.tile(
            [0, .5, 0, 0, .5] if policy == 'STATIC50' else [.5, .25, 0, 0, .25], (61, 1))
        prior = np.array([1., 0., 0., 0., 0.])
        fractions, budgets = [], []
        for i, stamp in enumerate(a['decision_us']):
            context = types.SimpleNamespace(decision_us=int(stamp), expert_eligible=a['expert_eligible'][i],
                expert_targets=a['expert_targets'][i], past_returns30=a['past_returns30'][i], binding={'symbol_order': list(SYMBOLS)})
            proposal = mapper.mapper(prior, requests[i], context)
            budget, fraction = np.asarray(proposal.budget), np.asarray(proposal.targets)
            require(np.abs(budget - prior).sum() <= .1 + 1e-10, 'Original budget ramp exceeded')
            if i == 60:
                fraction = fraction * 0
            if policy in POLICIES[:2]:
                require(np.array_equal(budget, a['ramped_expert_budget'][i]), 'All61 original mapper budget parity required')
                require(np.array_equal(fraction, a['mapper_target_fractions'][i]), 'All61 original mapper fraction parity required')
            fractions.append(fraction); budgets.append(budget); prior = budget
        arms[policy] = (np.asarray(fractions), np.asarray(budgets))
        report[policy] = dict(days=61, mapper='ORIGINAL_E5', maximum_budget_error=0 if policy in POLICIES[:2] else None,
            maximum_fraction_error=0 if policy in POLICIES[:2] else None, request_origin='FROZEN_HEAD' if policy in POLICIES[:2] else 'FIXED_REFERENCE')
    return arms, report


def market(state):
    from modules.collector_research.validation import runtime
    runtime.WORK = state / 'h1_validation/original/h1_market'
    from modules.collector_research.validation import data
    data.WORK = runtime.WORK
    return data.market_window(list(SYMBOLS), START, END)


def check(state, handoff):
    import numpy as np
    import polars as pl
    baseline = load('frozen_baseline', HERE / 'baseline.py')
    baseline.source_check()
    root = state / 'h1_validation/original/h1_market'
    m = read(root / 'reports/DATASET_MANIFEST.json')
    for r in m['artifacts']:
        p = root / r['relative_path']
        require(p.stat().st_size == r['bytes'] and sha(p) == r['sha256'], 'Registered source bytes differ')
    _, reports = targets(state, handoff)
    window = market(state)
    minute_count = 0
    for block in window['minute_blocks']():
        stamps = block['times']
        require(set(block['market']) == set(SYMBOLS), 'No dropped or filled asset gaps')
        require(np.array_equal(stamps, np.arange(START + minute_count * MINUTE, START + (minute_count + len(stamps)) * MINUTE, MINUTE)), 'Complete continuous actual minute grid required')
        minute_count += len(stamps)
    require(minute_count == 87840 and len(window['events']) == 915, 'Full61 minute/funding coverage required')
    for s in SYMBOLS:
        daily = pl.read_parquet(root / 'data/normalized' / (s + '_daily.parquet'))
        available, price = daily['available_us'].to_numpy(), daily['close'].to_numpy()
        a = np.load(handoff / 'requests/NO_CASH_NATIVE61_REQUESTS.npz', allow_pickle=False)
        for i, t in enumerate(a['decision_us']):
            j = np.searchsorted(available, t)
            require(available[j] == t and price[j] == a['completed_decision_daily_close'][i, SYMBOLS.index(s)], 'Completed daily decision price differs')
            require(np.array_equal(np.diff(price[j-30:j+1]) / price[j-30:j], a['past_returns30'][i, :, SYMBOLS.index(s)]), 'Actual30day past covariance source differs')
    return dict(status='PASS_H1_BYTE_IDENTITIES_MINUTE_COMPLETENESS_AND_ALL61_ORIGINAL_MAPPER',
        engine_sha256=sha(REPO / 'scripts/investment/resumable_perpetual.py'), registered_files=len(m['artifacts']),
        minutes_per_asset=minute_count, asset_days=305, trade_and_mark_rows=878400, funding_events=915,
        mapper_checks=reports, fits=0, provider_downloads=0, wallet_runs=0)


def run(state, handoff, policy, output, plan_commit):
    import numpy as np
    from scripts.investment import perpetual_directional
    from scripts.investment.resumable_perpetual import NativeDailySimulator
    from quant.bybit_isolated_account import BybitIsolatedAccount
    plan = read(HERE / 'NATIVE61_PLAN.json')
    committed = subprocess.check_output(['git', '-C', str(REPO), 'show', plan_commit + ':research/recover-frozen-runner-20261009/NATIVE61_PLAN.json'])
    require(committed == (HERE / 'NATIVE61_PLAN.json').read_bytes(), 'Published plan identity required')
    for relative, digest in plan['source_sha256'].items():
        require(sha(REPO / relative) == digest, 'Published code identity differs: ' + relative)
    require(sha(state / 'h1_validation/PREFLIGHT61.json') == plan['preflight_sha256'], 'Completed data/mapper gate differs')
    public = plan['public_input']
    root = state / 'h1_validation/original'
    for path, digest in [
        (root / 'MANIFEST_SHA256.json', public['member_manifest_sha256']),
        (root / 'h1_market/reports/DATASET_MANIFEST.json', public['data_manifest_sha256']),
        (root / 'source_increment/modules/native_action/e5_inputs.py', public['original_mapper_sha256']),
        (state / 'e5-bear-original/source_increment/modules/native_action/e5_teacher.py', public['original_mapper_teacher_sha256']),
        (handoff / 'handoff.zip', plan['handoff']['sha256']),
        (handoff / 'MANIFEST.json', plan['handoff']['manifest_sha256'])]:
        require(sha(path) == digest, 'Frozen input/mapper identity differs')
    for r in read(root / 'h1_market/reports/DATASET_MANIFEST.json')['artifacts']:
        p = root / 'h1_market' / r['relative_path']
        require(p.stat().st_size == r['bytes'] and sha(p) == r['sha256'], 'Registered market bytes differ before replay')
    require(not output.exists(), 'Fresh independent wallet required')
    arms, _ = targets(state, handoff)
    fractions, budgets = arms[policy]
    window = market(state)
    cost = read(handoff / 'requests/NATIVE61_EXPORT.json')['financial_config']['cost']
    sim = NativeDailySimulator(window, 'LONG_SHORT', cost, dict(id='RAW_AS_FRACTION', scale=1.),
        account_factory=BybitIsolatedAccount, persist_cash_close=True, final_day_target_zero=True)
    sim.budget = [1., 0., 0., 0., 0.]
    require(float(sim.account.nav()) == 10000, 'Fresh10000 account required')
    output.mkdir(parents=True, exist_ok=False)
    status, error = 'RUNNING', None
    start = time.monotonic(); utc = datetime.now(UTC).isoformat()
    receipt = dict(policy=policy, plan_commit=plan_commit, started_UTC=utc, limits=plan['limits'])
    (output / 'STARTED.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def alarm(signum, frame):
        raise TimeoutError('600-second native61 wallet cap')
    signal.signal(signal.SIGALRM, alarm); signal.setitimer(signal.ITIMER_REAL, 600)
    try:
        for i in range(61):
            require(shutil.disk_usage(output).free >= 15 * 2**30, '15GiB disk reserve required')
            sim.budget = budgets[i].tolist()
            actual = sim.advance_day(dict(zip(SYMBOLS, fractions[i], strict=True)))
            require(actual['completed'], 'Incomplete wallet must stop')
            if (i + 1) % 10 == 0 or i == 60:
                print(json.dumps(dict(policy=policy, completed_days=i+1, total_days=61, NAV=float(sim.account.nav()))), flush=True)
        require(sim.rows_written == 87840 and all(p.quantity == 0 for p in sim.account.positions.values()), 'Full61 paid terminal flat required')
        status = 'COMPLETE_CONDITIONAL_ACCOUNT'
    except BaseException as e:
        status, error = 'FAILED_PREFIX_RETAINED', dict(type=type(e).__name__, message=str(e))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        saved = perpetual_directional.save_case(sim.result(), output / 'account')
        (output / 'account/summary.json').write_text(json.dumps(saved['summary'], indent=2) + '\n')
        receipt.update(status=status, error=error, finished_UTC=datetime.now(UTC).isoformat(),
            elapsed_seconds=time.monotonic()-start, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            completed_minutes=sim.rows_written, original_engine_sha256=sha(REPO/'scripts/investment/resumable_perpetual.py'),
            audit='PENDING_POST_RUN_INDEPENDENT_RECONCILIATION')
        (output / 'EXECUTION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: saved['summary'][k] for k in ('NAV','net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','completed_minutes','terminal_cash_realized','liquidation_count')}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('check', 'run'))
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--handoff', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--policy', choices=POLICIES)
    p.add_argument('--plan-commit')
    a = p.parse_args()
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[key] = '1'
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS, (6_000_000_000, 6_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    def blocked(*args, **kwargs):
        raise RuntimeError('Offline native61 forbids network connections')
    socket.create_connection = blocked; socket.socket.connect = blocked
    os.environ['QUANT_ROOT'] = str(REPO)
    sys.path[:0] = [str(REPO/'src'), str(REPO)]
    if a.command == 'check':
        result = check(a.state, a.handoff)
        a.output.write_text(json.dumps(result, indent=2)+'\n'); print(json.dumps(result), flush=True)
    else:
        require(a.policy is not None and a.plan_commit is not None, 'Published plan and explicit policy required')
        # Bind original modules before account imports.
        modules(a.state)
        run(a.state, a.handoff, a.policy, a.output, a.plan_commit)


if __name__ == '__main__':
    main()
