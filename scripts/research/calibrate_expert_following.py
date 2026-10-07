"""Calibrate an existing daily proxy against seven owned native intervals.

This is a semantic calibration, not a strategy search or training run. Reuse
the daily quantity kernel and native isolated wallet without changing either.
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

from modules.collector_research.pipeline.economics import interval_arrays, replay
from modules.transformer_v3.storage import hydrated_account
from modules.transformer_v3.wallet import run_tasks
from scripts.research.public_cross_section_momentum import DAY_US, public_targets
from scripts.research.run_public_momentum import ROOT, load_past_inputs, save, sha, summary_row

EXEC_OFFSET_US = 60_000_001


def label_available_at(decision_us, horizon_days, *, actual_last_fill_us=None):
    """Nominal proxy boundary, extended by witnessed native close if supplied.

    Native partial-fill/close results cannot mature at a nominal proxy clock.
    This does not certify future marked-label availability or data ingestion.
    """
    if type(horizon_days) is not int or horizon_days < 1:
        raise ValueError('Positive integer horizon required')
    endpoint = int(decision_us) + horizon_days * DAY_US + EXEC_OFFSET_US
    if actual_last_fill_us is not None:
        endpoint = max(endpoint, int(actual_last_fill_us))
    return endpoint + 1


def mature_indices(decision_us, label_available_us):
    return np.flatnonzero(np.asarray(label_available_us, dtype=np.int64) <= int(decision_us))


def first_switch_cost_delta(previous_q, nav, target_weights, execution_prices, cost):
    """Diagnostic: actual first switch minus a zero-entry reference cost.

    This is not a substitute for rerunning the NAV-dependent future path.
    It uses explicit quantities/prices, never expert net-return averaging.
    """
    q, w, p = (np.asarray(x, float) for x in (previous_q, target_weights, execution_prices))
    if q.shape != w.shape or q.shape != p.shape or not np.isfinite([nav, cost]).all() or nav <= 0 or cost < 0:
        raise ValueError('Finite positive capital, nonnegative cost and ordered vectors required')
    if not all(np.isfinite(x).all() for x in (q, w, p)) or np.any(p <= 0):
        raise ValueError('Finite quantities, targets and positive prices required')
    desired = nav * w / p
    return float((np.abs(desired - q) @ p - np.abs(desired) @ p) * cost)


def proxy_rows(frames, indices, weights, scale, cost, capital):
    flat, trace = replay(frames, indices, weights, scale, cost, capital)
    # Separate marked utility from paid-close utility. No fees are removed from
    # the closed-account result or any historical evidence.
    marked_net = flat['net'] + flat['terminal_fee']
    arrays = [interval_arrays(f, indices, scale) for f in frames.values()]
    p0 = np.stack([a[0] for a in arrays], axis=1)
    q0 = capital * weights[0] / p0[0]
    return dict(closed=flat, marked_net=marked_net, price_pnl=float(trace.price_pnl.sum()),
                first_reference_q=q0.tolist(), terminal_fee=flat['terminal_fee'])


def fill_diagnostics(case, state):
    directory = Path(case['summary_path']).parent
    with hydrated_account(directory, state / 'diagnostic-scratch') as h:
        f = pl.read_parquet(h / 'trades.parquet')
        first = f['event_us'].min()
        last = f['event_us'].max()
        first_rows = f.filter(pl.col('event_us') == first).to_dicts()
    return dict(first_fill_us=first, last_fill_us=last, first_fill_legs=first_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--protocol', type=Path, required=True)
    ap.add_argument('--state', type=Path, required=True)
    a = ap.parse_args()
    began = time.monotonic()
    p = json.loads(a.protocol.read_text())
    state = a.state.resolve()
    assert os.uname().sysname == 'Linux' and state.is_relative_to(Path('/home/ubuntu/coin/execution-state'))
    assert p['budget']['new_wallets'] == 2 and p['budget']['new_fits'] == 0
    paths = [Path(__file__), a.protocol, ROOT / 'modules/collector_research/pipeline/economics.py',
             ROOT / 'scripts/research/public_cross_section_momentum.py', ROOT / 'scripts/research/run_public_momentum.py']
    for src in paths:
        assert hashlib.sha256(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + str(src.resolve().relative_to(ROOT))])).hexdigest() == sha(src)
    group = Path('/sys/fs/cgroup' + Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip())
    assert (group / 'memory.max').read_text().strip() != 'max' and int((group / 'memory.max').read_text()) <= 8_000_000_000
    assert (group / 'memory.swap.max').read_text().strip() == '0'
    state.mkdir(exist_ok=True)
    free_before = shutil.disk_usage(state).free
    assert free_before >= p['budget']['reserve_bytes']

    def progress(completed, failed, total, detail):
        save(state / 'progress.json', dict(status='running', stage='CALIBRATION', phase='标签与真实账户校准',
             completed=completed, failed=failed, total=total, unit='账户', detail=detail,
             elapsed_seconds=time.monotonic() - began, pid=os.getpid(), updated_at=time.time()))

    progress(0, 0, 2, 'DATA: verify past targets and admitted market bytes')
    parent_path = ROOT / p['parent_protocol']
    assert sha(parent_path) == p['parent_protocol_sha256']
    parent = json.loads(parent_path.read_text())
    close, available, input_refs = load_past_inputs(parent)
    w = p['window']
    assert w['start'] == parent['windows'][0]['start'] and w['end'] == w['start'] + 8 * DAY_US
    assert w['active_symbols'] == parent['windows'][0]['active_symbols'] and w['end'] <= parent['locked_start_us']
    dates = np.arange(w['start'], w['end'], DAY_US, dtype=np.int64)
    weights, _ = public_targets(close, available, dates, parent['symbols'], w['active_symbols'], anchor_us=parent['method']['anchor_us'])
    old_results_path = ROOT / p['parent_results']
    assert sha(old_results_path) == p['parent_results_sha256']
    old_results = json.loads(old_results_path.read_text())
    old = next(x for x in old_results['cases'] if x['window'] == parent['windows'][0]['id'] and x['funding_scale'] == 1)
    assert sha(old['result_path']) == old['result_sha256']
    saved = json.loads(Path(old['result_path']).read_text())
    assert sha(saved['task']['target_path']) == saved['task']['target_sha256']
    with np.load(saved['task']['target_path'], allow_pickle=False) as f:
        assert np.array_equal(f['weights'][:8], weights) and np.array_equal(f['decision_us'][:8], dates)
        assert f['symbol_order'].tolist() == parent['symbols']
    weights[-1] = 0.
    target = state / 'target.npz'
    if target.exists():
        with np.load(target, allow_pickle=False) as f:
            assert np.array_equal(f['weights'], weights) and np.array_equal(f['decision_us'], dates) and f['symbol_order'].tolist() == parent['symbols']
    else:
        np.savez_compressed(target, weights=weights, decision_us=dates, symbol_order=np.array(parent['symbols']))

    manifest_path = Path(parent['work']) / 'reports/DATASET_MANIFEST.json'
    assert sha(manifest_path) == parent['data_manifest_sha256'] == p['data_manifest_sha256']
    refs = {str((Path(x['path']) if 'path' in x else Path(parent['work']) / x['relative_path']).absolute()): x['sha256']
            for x in json.loads(manifest_path.read_text())['artifacts']}
    frames, daily_us = {}, {}
    daily_refs = []
    columns = ['dt', 'exec_price', 'mark_funding_per_unit', 'funding_interval_complete', 'complete_kline']
    for s in w['active_symbols']:
        path = Path(parent['work']) / 'data/normalized' / (s + '_daily.parquet')
        assert sha(path) == refs[str(path)]
        f = pl.read_parquet(path, columns=columns).sort('dt')
        dt = f['dt'].dt.epoch('us').to_numpy()
        assert np.all(np.diff(dt) == DAY_US) and dt.max() < parent['locked_start_us']
        daily_us[s] = dt
        frames[s] = f.to_pandas()
        daily_refs.append(dict(path=str(path), sha256=sha(path)))
    decision_rows = daily_us[w['active_symbols'][0]] + DAY_US
    idx = np.searchsorted(decision_rows, dates[:7])
    assert np.array_equal(decision_rows[idx], dates[:7])
    assert all(np.array_equal(dt + DAY_US, decision_rows) for dt in daily_us.values())
    selected = [parent['symbols'].index(s) for s in frames]
    proxies = {scale: proxy_rows(frames, idx, weights[:7, selected], scale, p['proxy_side_cost'], p['capital']) for scale in parent['funding_scales']}
    save(state / 'PROXY_BEFORE_WALLETS.json', dict(proxies=proxies, input_refs=input_refs, daily_refs=daily_refs,
         label_available_us=label_available_at(w['start'], 7), target_sha256=sha(target)))
    print('[DATA] verified; [TARGET] exact saved expert prefix; [PROXY] both unit interpretations complete', flush=True)
    tasks = []
    for scale in parent['funding_scales']:
        tasks.append(dict(id=('raw_fraction' if scale == 1 else 'raw_percent') + '/CALIBRATION7D', state=str(state),
            collector_root=parent['collector_root'], work=parent['work'], source_run=parent['source_run'],
            family='CSMOM21_CORE5_CALIBRATION', seed=0, profile='FULL', mapping='NEUTRAL', window=w, funding_scale=scale,
            target_path=str(target), target_sha256=sha(target), protocol_sha256=sha(a.protocol), noncausal=False))
    cases = run_tasks(tasks, state, 'CALIBRATION', workers=2, protocol_path=a.protocol, on_progress=progress)
    rows = []
    for c in cases:
        scale = c['task']['funding_scale']
        row = summary_row(c, state / 'native' / c['task']['id'] / 'RESULT.json', 'NEW_SEVEN_INTERVAL_CALIBRATION')
        assert c['summary']['contract'] == saved['summary']['contract'] and c['summary']['cost_scenario'] == saved['summary']['cost_scenario']
        proxy = proxies[scale]
        row['proxy'] = proxy
        row['native_minus_proxy'] = dict(net=row['net_PnL'] - proxy['closed']['net'],
            price_pnl=row['gross_PnL'] - proxy['price_pnl'],
            costs=row['fees'] + row['execution_cost'] - proxy['closed']['fees'],
            # Native summary is signed wallet cashflow; proxy is a charge.
            funding=-row['funding'] - proxy['closed']['funding'])
        row['funding_comparison_sign'] = 'Difference of CHARGES: -native_signed_cashflow - proxy_charge'
        assert abs(row['native_minus_proxy']['net'] - (row['native_minus_proxy']['price_pnl'] - row['native_minus_proxy']['costs'] - row['native_minus_proxy']['funding'])) < 1e-7
        row['fill_timing'] = fill_diagnostics(c, state)
        row['proxy_error_within_preregistered_limit'] = abs(row['native_minus_proxy']['net']) <= p['calibration_limit_USDT']
        rows.append(row)
    complete = all(x['proxy_error_within_preregistered_limit'] for x in rows)
    owned = sum(f.stat().st_size for f in state.rglob('*') if f.is_file())
    assert owned <= p['budget']['new_owned_bytes'] and time.monotonic() - began <= p['budget']['wall_seconds']
    result = dict(status='COMPLETE_SEMANTIC_CALIBRATION', source_commit=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip(),
        protocol=p, protocol_sha256=sha(a.protocol), cases=sorted(rows, key=lambda x:x['funding_scale']),
        decision='RETAIN_DAILY_PROXY_FOR_LIMITED_SCREENING_ONLY' if complete else 'REPAIR_PROXY_ALIGNMENT_BEFORE_MODEL_FITS',
        all_net_errors_within_limit=complete, actual_new_wallets=2, actual_new_fits=0, qualification='NONE_CASH', locked_consumed=False,
        elapsed_seconds=time.monotonic()-began, owned_bytes=owned, free_bytes_before=free_before, free_bytes_after=shutil.disk_usage(state).free,
        RAM_limit=(group/'memory.max').read_text().strip(), swap_limit=(group/'memory.swap.max').read_text().strip(), GPU=0,
        RAM_group_peak_bytes=int((group/'memory.peak').read_text()) if (group/'memory.peak').exists() else None,
        limitations=p['limitations'], input_refs=input_refs, daily_refs=daily_refs)
    save(state/'RESULTS.json', result)
    lines = ['# 七日专家跟随：日频代理与真实共享钱包校准', '',
             f"决定：{result['decision']}；零训练，投资资格NONE/CASH。", '',
             '|资金费解释|真实净PnL|代理收费终平净PnL|差额|价格PnL差|成本差|资金差|',
             '|---|---:|---:|---:|---:|---:|---:|']
    for r in result['cases']:
        d=r['native_minus_proxy']
        lines.append(f"|{r['funding_scale']}|{r['net_PnL']:.6f}|{r['proxy']['closed']['net']:.6f}|{d['net']:.6f}|{d['price_pnl']:.6f}|{d['costs']:.6f}|{d['funding']:.6f}|")
    lines += ['', '前七日按原冻结专家跟随，第八日清仓。对齐七个延迟执行区间；额外平仓日不是额外策略持有收益。',
              '代理marked值与收费终平值分开；后续可延续selector不应被强制每周平仓。旧连续60日标签没有改名为7日标签。',
              '标签成熟按执行结束后1微秒。周整点尚未成熟的上一周结果不能作为反馈。',
              '', *p['limitations'], '', '复现：python -B scripts/research/calibrate_expert_following.py --protocol protocols/EXPERT_FOLLOW_CALIBRATION_20261008.json --state /home/ubuntu/coin/execution-state/expert-follow-NEW，8GB/swap0/GPU0受限scope。']
    (state/'REPORT.md').write_text('\n'.join(lines)+'\n')
    save(state/'progress.json', dict(status='completed', stage='REPORT', phase='校准完成', completed=2, total=2,
         unit='账户', detail=result['decision'], elapsed_seconds=result['elapsed_seconds'], updated_at=time.time()))
    print(json.dumps(dict(status=result['status'], decision=result['decision'], errors=[r['native_minus_proxy']['net'] for r in rows])), flush=True)


if __name__ == '__main__':
    main()
