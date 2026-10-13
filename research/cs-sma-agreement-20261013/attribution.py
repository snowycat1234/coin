"""Read-only attribution of published saved holdings, never a policy replay.

Only full 2023/2025 saved CS, AGREEMENT and the predeclared diagnostic are read.
No economic kernel, signal builder, RNG, fitting, search, downloads or new
account state is invoked. All expenses are signed negative contributions.
Run `python attribution.py --self-test` for tiny arithmetic-only fixtures.
Run `python attribution.py` to verify source identity and write the two reports.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import unittest

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
              'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = ROOT.parent / 'inputs'
YEARS = (2023, 2025)
ARMS = ('CS', 'AGREEMENT', 'AGREEMENT_NO_REALLOCATION')
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
COMPONENTS = ('price_pnl_USDT', 'funding_cash_USDT',
              'rebalance_cost_contribution_USDT', 'terminal_cost_contribution_USDT')
COST = .00135
CAPITAL = 10000.
DAY_US = 86400_000000
TOLERANCE = 1e-8
RESULTS_PUBLICATION_COMMIT = '706493dd6a1c0e6da6d7cd68b6b3e66c197d9de2'


def read_json(path):
    return json.loads(Path(path).read_text())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_npz(path):
    with np.load(path, allow_pickle=False) as value:
        return {key: value[key] for key in value.files}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summed(value):
    return float(math.fsum(np.asarray(value, dtype=float).ravel()))


def totals(value):
    out = {key: summed(value[key]) for key in COMPONENTS}
    out['net_USDT'] = math.fsum(out.values())
    out['initial_capital_equivalent_percentage_points'] = out['net_USDT'] / CAPITAL * 100
    return out


def delta_totals(a, b):
    out = {key: a[key] - b[key] for key in COMPONENTS}
    out['net_USDT'] = math.fsum(out.values())
    out['initial_capital_equivalent_percentage_points'] = out['net_USDT'] / CAPITAL * 100
    return out


def side_of(q):
    return 'long' if q > 0 else 'short'


def gate_of(gate):
    return 'kept' if gate else 'removed'


def trade_parts(previous, current):
    """Minimal additive inventory endpoints, not a hypothetical trade plan.

    Entry/increase belongs to current inventory, exit/decrease to previous
    inventory; reversal comprises a close of old plus an open of new. Absolute
    units sum to abs(current-previous). This makes side/gate expenses additive.
    """
    if previous == current:
        return ()
    if previous == 0:
        return (('current', abs(current)),)
    if current == 0:
        return (('previous', abs(previous)),)
    if previous * current < 0:
        return (('previous', abs(previous)), ('current', abs(current)))
    if abs(current) > abs(previous):
        return (('current', abs(current - previous)),)
    return (('previous', abs(current - previous)),)


def trade_kind(previous, current):
    if previous == current:
        return 'unchanged'
    if previous == 0:
        return 'entry_from_cash'
    if current == 0:
        return 'exit_to_cash'
    if previous * current < 0:
        return 'sign_reversal'
    return 'same_sign_resize'


def components(q, p0, p1, funding, cost=COST):
    """Arithmetic on supplied held quantities; does not generate or resize q."""
    q, p0, p1, funding = map(lambda x: np.asarray(x, dtype=float), (q, p0, p1, funding))
    require(q.shape == p0.shape == p1.shape == funding.shape and q.ndim == 2,
            'Aligned day/asset arrays required')
    previous = np.vstack((np.zeros(q.shape[1]), q[:-1]))
    touched = (q != 0) | (previous != 0)
    held = q != 0
    require(np.isfinite(q).all(), 'Non-finite saved holdings')
    require(np.isfinite(p0[touched]).all() and (p0[touched] > 0).all(),
            'Missing touched execution prices')
    require(np.isfinite(p1[held]).all() and (p1[held] > 0).all()
            and np.isfinite(funding[held]).all(), 'Missing owned interval inputs')
    price = np.zeros_like(q)
    cash = np.zeros_like(q)
    rebalance = np.zeros_like(q)
    terminal = np.zeros_like(q)
    price[held] = q[held] * (p1[held] - p0[held])
    cash[held] = -q[held] * funding[held]
    rebalance[touched] = -abs(q[touched] - previous[touched]) * p0[touched] * cost
    active = q[-1] != 0
    terminal[-1, active] = -abs(q[-1, active]) * p1[-1, active] * cost
    return dict(zip(COMPONENTS, (price, cash, rebalance, terminal)))


def partition(q, gate, p0, values, symbols, cost=COST):
    """Joint asset x long/short x kept/removed inventory attribution."""
    q, gate = np.asarray(q), np.asarray(gate, dtype=bool)
    buckets = {
        asset: {side: {group: {key: 0. for key in COMPONENTS}
                       for group in ('kept', 'removed')}
                for side in ('long', 'short')}
        for asset in symbols}
    days, assets = q.shape
    for day in range(days):
        for j, asset in enumerate(symbols):
            current = q[day, j]
            previous = q[day - 1, j] if day else 0.
            if current:
                cell = buckets[asset][side_of(current)][gate_of(gate[day, j])]
                for key in COMPONENTS[:2]:
                    cell[key] += float(values[key][day, j])
            for endpoint, units in trade_parts(previous, current):
                owner_day = day if endpoint == 'current' else day - 1
                owner_q = current if endpoint == 'current' else previous
                cell = buckets[asset][side_of(owner_q)][gate_of(gate[owner_day, j])]
                cell[COMPONENTS[2]] -= float(units * p0[day, j] * cost)
            if day == days - 1 and current:
                cell = buckets[asset][side_of(current)][gate_of(gate[day, j])]
                cell[COMPONENTS[3]] += float(values[COMPONENTS[3]][day, j])
    for asset in symbols:
        for side in ('long', 'short'):
            for group in ('kept', 'removed'):
                buckets[asset][side][group] = totals(buckets[asset][side][group])
    return buckets


def aggregate_partition(joint, selected_assets=None, selected_sides=None, selected_gates=None):
    assets = selected_assets or tuple(joint)
    sides = selected_sides or ('long', 'short')
    gates = selected_gates or ('kept', 'removed')
    value = {key: [] for key in COMPONENTS}
    for asset in assets:
        for side in sides:
            for group in gates:
                for key in COMPONENTS:
                    value[key].append(joint[asset][side][group][key])
    return totals(value)


def partition_views(joint):
    return dict(
        by_asset={asset: aggregate_partition(joint, selected_assets=(asset,)) for asset in joint},
        by_side={side: aggregate_partition(joint, selected_sides=(side,))
                 for side in ('long', 'short')},
        by_gate={group: aggregate_partition(joint, selected_gates=(group,))
                 for group in ('kept', 'removed')},
        by_side_and_gate={side: {group: aggregate_partition(
            joint, selected_sides=(side,), selected_gates=(group,))
            for group in ('kept', 'removed')} for side in ('long', 'short')},
        joint_asset_side_gate=joint)


def delta_views(a, b):
    out = {}
    for view in ('by_asset', 'by_side', 'by_gate'):
        out[view] = {key: delta_totals(a[view][key], b[view][key]) for key in a[view]}
    out['by_side_and_gate'] = {
        side: {group: delta_totals(a['by_side_and_gate'][side][group],
                                   b['by_side_and_gate'][side][group])
               for group in ('kept', 'removed')}
        for side in ('long', 'short')}
    out['joint_asset_side_gate'] = {
        asset: {side: {group: delta_totals(a['joint_asset_side_gate'][asset][side][group],
                                          b['joint_asset_side_gate'][asset][side][group])
                       for group in ('kept', 'removed')}
                for side in ('long', 'short')} for asset in a['by_asset']}
    return out


def arithmetic_audit(rows, q, weights, p0, values, metrics, decision_us):
    """Compare additive quantities with saved rows; no NAV recursion or replay."""
    before = np.asarray([r['nav_before'] for r in rows])
    after = np.asarray([r['nav_after'] for r in rows])
    daily_net = sum(values.values()).sum(axis=1)
    current = totals(values)
    terminal = -current[COMPONENTS[3]]
    checks = {
        'daily_price_pnl': np.max(abs(values[COMPONENTS[0]].sum(axis=1)
                                     - [r['price_pnl'] for r in rows])),
        'daily_funding_cash': np.max(abs(values[COMPONENTS[1]].sum(axis=1)
                                        + [r['funding_debit_proxy'] for r in rows])),
        'daily_trading_cost': np.max(abs(-values[COMPONENTS[2]].sum(axis=1)
                                        - values[COMPONENTS[3]].sum(axis=1)
                                        - [r['trading_cost_proxy'] for r in rows])),
        'daily_rebalance_turnover': np.max(abs(-values[COMPONENTS[2]].sum(axis=1) / COST
                                               - [r['turnover_USDT'] for r in rows])),
        'daily_saved_NAV_change': np.max(abs(after - before - daily_net)),
        'daily_saved_NAV_continuity': np.max(abs(before[1:] - after[:-1])),
        'target_notional_identity': np.max(abs(q * p0 - before[:, None] * weights)),
        'summary_price_pnl': abs(current[COMPONENTS[0]] - metrics['price_pnl']),
        'summary_funding_cash': abs(current[COMPONENTS[1]] - metrics['funding_cash']),
        'summary_trading_cost': abs(-current[COMPONENTS[2]] - current[COMPONENTS[3]]
                                     - metrics['trading_cost']),
        'summary_terminal_cost': abs(terminal - metrics['terminal_cost_proxy_USDT']),
        'summary_net': abs(current['net_USDT'] - metrics['net_USDT']),
        'saved_final_NAV': abs(current['net_USDT'] - (after[-1] - CAPITAL)),
        'initial_NAV': abs(before[0] - CAPITAL),
        'summary_return_in_USDT': abs(current['net_USDT'] / CAPITAL - metrics['cumulative_net_return']) * CAPITAL,
    }
    daily_return_error = float(np.max(abs(after / before - 1 - [r['daily_return'] for r in rows])))
    require(all(float(x) <= TOLERANCE for x in checks.values()), f'Saved arithmetic failed: {checks}')
    require(daily_return_error <= 1e-14, 'Saved daily returns inconsistent')
    require(np.array_equal(np.array([r['decision_us'] for r in rows]), decision_us),
            'Saved row calendar mismatch')
    require(metrics['days'] == metrics['planned_days'] == len(rows) == 365
            and metrics['hypothetical_cost_terminal'], 'Incomplete published result')
    require(all(float(x) == 0 for x in metrics['positions']), 'Terminal position state differs')
    return dict(status='PASS', absolute_tolerance_USDT=TOLERANCE,
                max_absolute_errors_USDT={k: float(v) for k, v in checks.items()},
                max_absolute_daily_return_error=daily_return_error,
                additive_net_USDT=current['net_USDT'],
                published_net_USDT=metrics['net_USDT'],
                published_return=metrics['cumulative_net_return'],
                derived_return=current['net_USDT'] / CAPITAL)


def turnover_views(q, gate, p0, proof, values):
    previous = np.vstack((np.zeros(q.shape[1]), q[:-1]))
    fees = -values[COMPONENTS[2]]
    rank_day = np.array([r['cs_rank_us'] == r['decision_us'] for r in proof])
    categories = {k: 0. for k in ('unchanged', 'entry_from_cash', 'exit_to_cash',
                                 'sign_reversal', 'same_sign_resize')}
    for day in range(len(q)):
        for j in range(q.shape[1]):
            categories[trade_kind(previous[day, j], q[day, j])] += float(fees[day, j])
    flipped_gate = np.vstack((np.zeros(q.shape[1], bool), gate[1:] != gate[:-1]))
    return dict(rebalance_cost_USDT=summed(fees),
                cost_by_inventory_transition_USDT=categories,
                cost_on_CS_weekly_rank_dates_USDT=summed(fees[rank_day]),
                cost_on_other_dates_USDT=summed(fees[~rank_day]),
                cost_in_assets_whose_gate_changed_since_prior_date_USDT=summed(fees[flipped_gate]),
                CS_weekly_rank_dates=int(rank_day.sum()),
                caveat='Expense classification only. These costs are not certified avoidable; holding fewer rebalances would change inventory and price/funding PnL.')


def quantity_difference_identity(cs_q, agreement_q, cs_nav, agreement_nav, gate, p0, p1, funding):
    """Same-date attribution of kept-leg changes, not an account counterfactual.

    With A=AGREEMENT and C=CS, kept delta q =
      [q_A * NAV_C/NAV_A - q_C] + [q_A * (1-NAV_C/NAV_A)].
    First term isolates saved sizing at CS's contemporaneous NAV. Second is
    the saved NAV-path effect using AGREEMENT sizing. No portfolio is replayed,
    and no independent return/cost can be assigned to either term.
    """
    kept_cs = np.where(gate, cs_q, 0.)
    nav_term = agreement_q * (1 - cs_nav[:, None] / agreement_nav[:, None])
    sizing_term = agreement_q - nav_term - kept_cs
    difference = agreement_q - cs_q
    removed = -np.where(gate, 0., cs_q)
    residual = np.max(abs(difference - (removed + sizing_term + nav_term)) * p0)
    require(residual < TOLERANCE, 'Quantity difference identity failed')
    changes = {'removed_CS_holdings': removed,
               'kept_sizing_at_CS_contemporaneous_NAV': sizing_term,
               'kept_saved_NAV_path_effect_using_AGREEMENT_sizing': nav_term}
    out = {}
    for label, delta in changes.items():
        price, cash = delta * (p1 - p0), -delta * funding
        out[label] = dict(price_pnl_USDT=summed(price), funding_cash_USDT=summed(cash),
                          price_plus_funding_USDT=summed(price) + summed(cash),
                          by_asset={symbol: dict(price_pnl_USDT=summed(price[:, j]),
                                                 funding_cash_USDT=summed(cash[:, j]))
                                    for j, symbol in enumerate(SYMBOLS)})
    return dict(terms=out, max_quantity_identity_notional_error_USDT=float(residual),
                decomposition_order='Sizing evaluated at CS contemporaneous NAV; NAV path evaluated at AGREEMENT sizing. Alternative attribution orders can allocate the interaction differently.',
                caveat='Additive same-date identity for price/funding only, not causal marginal returns or equal-capital subportfolios. Costs remain actual saved inventory-difference expenses; no term is scored as a new arm.')


def verify_source(path, expected, evidence):
    actual = sha256(path)
    require(actual == expected, f'Published source SHA256 mismatch: {path.name}')
    evidence[str(path.relative_to(ROOT.parent))] = actual


def build_report():
    results_path = HERE / 'results/RESULTS.json'
    manifest = read_json(HERE / 'results/OUTPUTS_MANIFEST.json')
    results = read_json(results_path)
    evidence = {}
    verify_source(results_path, manifest['files']['RESULTS.json'], evidence)
    for relative, expected in results['code_target_hashes'].items():
        verify_source(ROOT / relative, expected, evidence)
    verify_source(HERE / 'PROTOCOL.json', results['protocol_SHA256'], evidence)
    verify_source(HERE / 'DEDUP_REVIEW.json', results['code_target_hashes'][
        'research/cs-sma-agreement-20261013/DEDUP_REVIEW.json'], evidence)
    years = {}
    for year in YEARS:
        frozen_year = results['years'][str(year)]
        ipath = INPUTS / f'Y{year}.npz'
        tpath = HERE / f'targets/Y{year}.npz'
        ppath = HERE / f'targets/Y{year}_PROOF.json'
        verify_source(ipath, results['input_hashes'][str(year)], evidence)
        for path in (tpath, ppath):
            verify_source(path, results['code_target_hashes'][str(path.relative_to(ROOT))], evidence)
        inputs, targets, proof = load_npz(ipath), load_npz(tpath), read_json(ppath)
        decisions = inputs['decision_us']
        require(np.array_equal(decisions, targets['decision_us']) and len(decisions) == 365
                and np.all(np.diff(decisions) == DAY_US), 'Not the complete saved daily calendar')
        start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
        end = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
        require(int(decisions[0]) == start and int(decisions[-1]) + DAY_US == end,
                'Calendar boundaries differ')
        require(tuple(inputs['symbol_order']) == tuple(targets['symbol_order']) == SYMBOLS,
                'CORE5 order mismatch')
        gate, raw = targets['agreement_mask'], targets['raw_CS']
        require(len(proof) == 365 and np.all(targets['source_status'] == 'READY'),
                'Saved target proof incomplete')
        for day, row in enumerate(proof):
            require(row['decision_us'] == int(decisions[day]) and row['status'] == 'READY'
                    and row['sma_close_count'] == 200 and row['risk_return_count'] == 30
                    and row['last_close_available_us'] <= row['decision_us'], 'Saved causal proof mismatch')
            require(np.array_equal(row['agreement_mask'], gate[day]), 'Saved gate proof mismatch')
            expected_gate = (raw[day] != 0) & np.array(row['sma_eligible'], bool) \
                & (np.array(row['sma_sign']) != 0) \
                & (np.sign(raw[day]) == np.array(row['sma_sign']))
            require(np.array_equal(expected_gate, gate[day]), 'Saved symmetric gate semantics mismatch')
        require(np.array_equal(targets['raw_AGREEMENT'], np.where(gate, raw, 0.)),
                'Saved agreement altered raw ranks')
        require(np.array_equal(targets['AGREEMENT_NO_REALLOCATION'],
                               np.where(gate, targets['CS'], 0.)), 'Saved diagnostic differs')
        arms, quantities, nav = {}, {}, {}
        for arm in ARMS:
            published = frozen_year['arms'][arm]
            rows_path = HERE / 'results' / published['quantity_rows_file']
            verify_source(rows_path, published['quantity_rows_SHA256'], evidence)
            require(manifest['files'][rows_path.name] == published['quantity_rows_SHA256'],
                    'Quantity identity manifests disagree')
            rows = read_json(rows_path)
            q = np.asarray([r['held_quantity'] for r in rows], dtype=float)
            require(q.shape == (365, 5), 'Saved quantity shape mismatch')
            require(np.array_equal(np.sign(q), np.sign(targets[arm])), 'Saved quantity signs differ')
            require(np.all(inputs['owned_interval_valid'][q != 0]), 'Unknown owned interval')
            if arm != 'CS':
                require(np.all(q[~gate] == 0), 'Agreement holds a removed leg')
            values = components(q, inputs['p0'], inputs['p1'], inputs['funding_per_unit'])
            audit = arithmetic_audit(rows, q, targets[arm], inputs['p0'], values,
                                     published['metrics'], decisions)
            joint = partition(q, gate, inputs['p0'], values, SYMBOLS)
            views = partition_views(joint)
            total = totals(values)
            grouped = aggregate_partition(joint)
            partition_error = max(abs(total[k] - grouped[k]) for k in COMPONENTS)
            require(partition_error <= TOLERANCE, 'Joint partitions do not reconcile')
            audit['max_joint_partition_reconciliation_error_USDT'] = partition_error
            arms[arm] = dict(totals=total, **views, reconciliation=audit,
                             published_metrics=published['metrics'],
                             published_exposure=published['exposure'],
                             turnover=turnover_views(q, gate, inputs['p0'], proof, values))
            quantities[arm] = q
            nav[arm] = np.array([r['nav_before'] for r in rows])
        delta = dict(totals=delta_totals(arms['AGREEMENT']['totals'], arms['CS']['totals']),
                     **delta_views(arms['AGREEMENT'], arms['CS']))
        require(abs(delta['totals']['net_USDT'] - (
            frozen_year['arms']['AGREEMENT']['metrics']['net_USDT']
            - frozen_year['arms']['CS']['metrics']['net_USDT'])) <= TOLERANCE,
            'Published between-wallet net delta differs')
        ratio = np.divide(targets['AGREEMENT'], targets['CS'],
                          out=np.zeros_like(targets['CS']), where=gate)
        counts = {side: {group: int(np.count_nonzero((raw * sign > 0)
                      & (gate if group == 'kept' else ~gate))) for group in ('kept', 'removed')}
                  for side, sign in (('long', 1), ('short', -1))}
        years[str(year)] = dict(
            calendar=dict(days=365, start_UTC=f'{year}-01-01', end_UTC=f'{year}-12-31',
                          full_calendar_no_date_selection=True),
            CS_leg_date_counts=counts,
            arms=arms, AGREEMENT_minus_CS=delta,
            kept_quantity_difference_identity=quantity_difference_identity(
                quantities['CS'], quantities['AGREEMENT'], nav['CS'], nav['AGREEMENT'],
                gate, inputs['p0'], inputs['p1'], inputs['funding_per_unit']),
            saved_weight_ratio_AGREEMENT_to_CS_on_kept_legs=dict(
                less_than_one_leg_dates=int(np.count_nonzero(ratio[gate] < 1 - 1e-12)),
                equal_to_one_leg_dates=int(np.count_nonzero(abs(ratio[gate] - 1) <= 1e-12)),
                greater_than_one_leg_dates=int(np.count_nonzero(ratio[gate] > 1 + 1e-12)),
                quantiles_min_p10_median_p90_max=np.quantile(ratio[gate], [0, .1, .5, .9, 1]).tolist()),
            predefined_diagnostic_deltas=dict(
                NO_REALLOCATION_minus_CS=delta_totals(arms['AGREEMENT_NO_REALLOCATION']['totals'],
                                                       arms['CS']['totals']),
                AGREEMENT_minus_NO_REALLOCATION=delta_totals(arms['AGREEMENT']['totals'],
                                                             arms['AGREEMENT_NO_REALLOCATION']['totals'])),
            published_primary_gates_pass=results['all_frozen_gates_pass'])
    return dict(
        analysis='Full-calendar saved-quantity economic attribution',
        results_publication_commit_from_task=RESULTS_PUBLICATION_COMMIT,
        frozen_code_targets_commit_in_RESULTS=results['published_commit'],
        status='PASS_ARITHMETIC_RECONCILIATION',
        diagnostic_code_SHA256=sha256(Path(__file__)),
        scope='2023 and 2025; all 365 dates each; original saved CS, AGREEMENT and predeclared AGREEMENT_NO_REALLOCATION holdings only',
        units='USDT contributions; funding cash positive means receipt; expense contributions negative. Percentage points are USDT/10000*100, not independent strategy returns.',
        method=dict(
            price='saved held_quantity * (original p1 - original p0)',
            funding='-saved held_quantity * original signed funding_per_unit',
            rebalance='-abs(current saved quantity - previous saved quantity) * original p0 * .00135; prior initial inventory is zero',
            terminal='-abs(last saved quantity) * last original p1 * .00135; separated from final saved row trading_cost_proxy',
            gate='Saved agreement_mask and target proof at ownership date; raw_CS defines original long/short leg intent',
            expense_partitions='Opening/increasing units use current holding side and gate; closing/decreasing units use previous holding side and previous ownership-date gate; reversals split close/open. Terminal cost uses final holding. This explicit convention is additive, not a causal cost allocation.',
            source_identity='Published RESULTS and quantity hashes, original input and saved target/proof hashes verified before arithmetic',
            excluded='No new account replay, target generation, RNG, fitting, parameter search, shortened calendar, winner selection, protected 2026 data, external downloads or publication'),
        source_SHA256=evidence, years=years,
        interpretation_limits=[
            'CS kept and removed quantities came from CS full-wallet NAV and risk sizing; their summed cash contributions are attribution, not separately tradable equal-capital strategies.',
            'AGREEMENT quantities incorporate a different realized NAV path and different covariance-based sizing. Removing CS contributions is not a causal return counterfactual.',
            'The saved NO_REALLOCATION diagnostic has independent wallet NAV, differs from literal CS-quantity subtraction, and can raise estimated risk when hedges are removed. It remains a diagnostic and cannot rescue failed primary gates.',
            'Known historical development years and conditional daily quantity proxy only; no execution, capacity, liquidation or pristine holdout qualification.'],
        next_research_direction=dict(
            recommendation='Preserve CS relative ranking and long/short hedge structure; prioritize a single predeclared transaction-cost-aware inventory/risk-rebalancing experiment rather than another absolute-sign hard gate.',
            rationale='2025 lost price PnL overwhelms saved fees; profitable rejected shorts show absolute downtrend is not necessary for cross-sectional shorts. In 2023 ungated CS has positive price PnL but is made net-negative by turnover costs and funding.',
            falsifiable_design='On admitted seen-development calendars only, retain CS rank rules, original signed funding and execution costs; freeze one causal inventory/risk adjustment recipe and full-calendar economic gates before replay. Preserve market-neutral hedge structure, account for covariance/cap constraints, and report turnover plus net and drawdown. No search or holdout access is authorized by this attribution.',
            no_free_savings='Same-sign and non-rank-date expenses are research targets, not avoidable-cost estimates. 2023 needs over 89.72 USDT improvement; even deleting all 81.63 non-rank-date fees arithmetically would still leave CS negative before inventory changes.',
            preserved_failures=[
                'CSMOM_ABSOLUTE_SHORT_20261008 own-21-day-return short gate: targeted DEDUP_REVIEW records worse net and drawdown in three windows despite removing historical XRP liquidation.',
                'Prior failed SMA hard gate and additive SMA/CS mix remain failed evidence; no reset, rescue by diagnostic, or untested rebranding of a sign gate.',
                'This frozen symmetric daily SMA200 AGREEMENT fails the published primary qualification in both full years.']))


def money(value):
    return f'{value:+,.2f}'


def markdown_report(report):
    lines = ['# Why the symmetric CS/SMA200 agreement gate failed', '',
             'Saved-holdings diagnostic only. All 365 dates in each of 2023 and 2025; no replay, new targets, fitting, random draws or parameter search. Original quantity rows, p0/p1/funding, target masks and proofs were hash-verified.', '',
             '## Net shortfall: mostly lost price PnL', '',
             '| Full year | CS net | AGREEMENT net | Difference | Price PnL difference | Funding difference | Rebalance expense difference | Terminal expense difference |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for y, value in report['years'].items():
        a = value['arms']; d = value['AGREEMENT_minus_CS']['totals']
        lines.append(f"| {y} | {money(a['CS']['totals']['net_USDT'])} | {money(a['AGREEMENT']['totals']['net_USDT'])} | {money(d['net_USDT'])} | {money(d[COMPONENTS[0]])} | {money(d[COMPONENTS[1]])} | {money(d[COMPONENTS[2]])} | {money(d[COMPONENTS[3]])} |")
    lines += ['', 'All amounts are USDT. Expense differences are signed contributions: positive means lower expense. These sum to the published separate-wallet net difference, within 1e-8 USDT.', '',
              '## What the gate removed versus what resizing changed', '',
              '| Full year | Removed CS long price PnL | Removed CS short price PnL | Total removed price PnL | Kept sizing effect at CS NAV | Kept NAV-path effect |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for y, value in report['years'].items():
        cs = value['arms']['CS']['by_side_and_gate']; identity = value['kept_quantity_difference_identity']['terms']
        removed = value['arms']['CS']['by_gate']['removed'][COMPONENTS[0]]
        lines.append(f"| {y} | {money(cs['long']['removed'][COMPONENTS[0]])} | {money(cs['short']['removed'][COMPONENTS[0]])} | {money(removed)} | {money(identity['kept_sizing_at_CS_contemporaneous_NAV'][COMPONENTS[0]])} | {money(identity['kept_saved_NAV_path_effect_using_AGREEMENT_sizing'][COMPONENTS[0]])} |")
    lines += ['',
              '2025 is the clearest failure: the gate removed profitable relative losers as well as profitable longs. Requiring a cross-sectional short to be in an absolute SMA downtrend discards shorts that can profit even while their own long-term trend is up. That mechanism is consistent with the observed attribution; it is not proof of a causal marginal effect. The remaining inventory was also resized differently: 548 of 819 kept leg-dates had smaller AGREEMENT weights than CS, and 131 had larger weights.', '',
              '2023 is mixed: rejected CS short legs carry −893.38 of price PnL, while rejected longs carry +995.03. Rejected shorts also carried 109.09 of funding receipts, versus 19.18 funding expense on rejected longs. Different sizing on the surviving legs further reduced price PnL; the more one-sided inventory carried greater net funding expense.', '',
              '### Asset contributions to AGREEMENT minus CS', '',
              '| Full year | Asset | Price | Funding | Rebalance expense | Terminal expense | Net |',
              '|---|---|---:|---:|---:|---:|---:|']
    for y, value in report['years'].items():
        for asset, d in value['AGREEMENT_minus_CS']['by_asset'].items():
            lines.append(f"| {y} | {asset} | {money(d[COMPONENTS[0]])} | {money(d[COMPONENTS[1]])} | {money(d[COMPONENTS[2]])} | {money(d[COMPONENTS[3]])} | {money(d['net_USDT'])} |")
    lines += ['',
              '2023 lost most incremental price PnL in SOL. In 2025 ETH, SOL and DOGE account for most of the price shortfall. DOGE retained holdings still produced −998.99 of AGREEMENT price PnL; this is descriptive, not permission to drop DOGE or select assets after seeing results.', '',
              '## Hedging and exposure changed', '',
              '| Full year | CS / AGREEMENT mean gross | AGREEMENT mean net-long | CS / AGREEMENT realized annual vol | CS / AGREEMENT drawdown |',
              '|---|---:|---:|---:|---:|']
    for y, value in report['years'].items():
        c, a = value['arms']['CS'], value['arms']['AGREEMENT']
        lines.append(f"| {y} | {c['published_exposure']['mean_gross']:.2%} / {a['published_exposure']['mean_gross']:.2%} | {a['published_exposure']['mean_net']:.2%} | {c['published_metrics']['annual_vol']:.2%} / {a['published_metrics']['annual_vol']:.2%} | {c['published_metrics']['drawdown']:.2%} / {a['published_metrics']['drawdown']:.2%} |")
    lines += ['',
              'The ungated CS wallet remains net-neutral; the gate removes that hedge structure. In 2025 it more than halves mean gross yet raises realized volatility and markedly worsens drawdown. A common nominal 10% risk policy did not create matched realized risk.', '',
              'The predefined NO_REALLOCATION diagnostic nets −249.45 in 2023 and +113.87 in 2025; AGREEMENT nets 272.63 and 512.36 less, respectively. This supports inspecting survivor sizing, but does not isolate a causal sizing return because the wallet NAV paths differ. Removing hedges pushes its estimated risk above 10% on 154 and 254 dates; its 2025 realized vol is 15.49% and drawdown 14.12%. It is not a qualified replacement winner.', '',
              '## Most useful next research direction', '',
              'Preserve the relative CS signal and long/short hedge structure. Prioritize one predeclared transaction-cost-aware inventory/risk-rebalancing experiment instead of another absolute-sign gate. CS 2023 earns +233.27 price PnL but pays 295.34 total costs and 27.65 funding; CS 2025 earns +2,560.22 price PnL and stays strongly net-positive. This targets a measured weakness without discarding the profitable 2025 relative shorts.', '',
              'CS same-sign resizing costs are 91.49 / 104.76 in 2023 / 2025; non-weekly-rank-date expenses are 81.63 / 84.80. These are overlapping classifications, not additive savings, and not certified avoidable. Even a perfect rebate of every non-rank-date 2023 fee would still leave CS negative by 8.09. A new design must explicitly trade reduced costs against changed inventory, achieved risk, net neutrality and missed price/funding PnL. Freeze one causal recipe and its full-calendar gates before any run; no tuning, shortened windows or protected holdout access follows from this report.', '',
              'Keep the prior failed own-21-day-return short gate, failed SMA hard-gate evidence and failed additive SMA/CS mixture intact. The symmetric gate also remains failed. The JSON contains complete additive asset × side × gate attribution, all expense conventions, turnover diagnostics and arithmetic reconciliations.', '',
              '## Attribution conventions and limits', '',
              '- Price PnL = q × (p1 − p0); funding cash = −q × original funding per unit; rebalance cost = −|q − prior q| × p0 × 0.00135; terminal cost = −|last q| × last p1 × 0.00135. q is exactly the saved binary-float quantity, without regenerated holdings.',
              '- Holding price/funding use the saved ownership-date gate and inventory direction. Opening/increasing cost follows current inventory; closing/decreasing cost follows prior inventory and prior gate. A reversal splits old close and new open. This convention makes every expense additive; alternative attribution conventions can move costs between buckets.',
              '- The kept-leg identity is qA − qC = (qA × NAVC/NAVA − qC) + qA × (1 − NAVC/NAVA). The first term is sizing at CS contemporaneous NAV; the second is the NAV-path effect at AGREEMENT sizing. The order determines allocation of their interaction. These are algebraic PnL/funding terms, not new quantities replayed in an account, independently tradable strategies or separately evaluated returns.',
              '- CS kept/removed components used the full CS wallet NAV and risk sizing. Their sum is an account attribution, not an equal-capital substitute portfolio or proof that removing a component causes the measured return difference.',
              '- Known historical development years, hypothetical filled daily proxy and paid hypothetical terminal only. No capacity, margin, liquidation, minQty, live-fill or pristine out-of-sample evidence.', '',
              'Reproduce: python attribution.py --self-test; python attribution.py. Existing scoring, protocol, targets and result artifacts are not modified.', '']
    return '\n'.join(lines)


class ArithmeticTests(unittest.TestCase):
    def test_trade_endpoints_sum_to_exact_inventory_change(self):
        for old, new in ((0, 2), (2, 0), (2, -3), (-2, 3), (2, 4), (4, 2),
                         (-2, -4), (-4, -2), (0, 0), (2, 2)):
            self.assertAlmostEqual(sum(x[1] for x in trade_parts(old, new)), abs(new - old))

    def test_price_funding_reversal_cash_exit_terminal_and_partitions(self):
        q = np.array([[2., -1.], [-3., -2.], [0., -1.]])
        p0 = np.full_like(q, 100.)
        p1 = np.array([[110., 90.], [90., 110.], [105., 90.]])
        fp = np.full_like(q, 2.)
        gate = np.array([[True, False], [False, True], [False, True]])
        value = components(q, p0, p1, fp, cost=.01)
        self.assertEqual(summed(value[COMPONENTS[0]]), 50.)
        self.assertEqual(summed(value[COMPONENTS[1]]), 10.)
        self.assertEqual(summed(value[COMPONENTS[2]]), -13.)
        self.assertEqual(summed(value[COMPONENTS[3]]), -.9)
        joint = partition(q, gate, p0, value, ('A', 'B'), cost=.01)
        self.assertAlmostEqual(aggregate_partition(joint)['net_USDT'], 46.1)
        self.assertEqual(joint['A']['long']['kept'][COMPONENTS[2]], -4.)
        self.assertEqual(joint['A']['short']['removed'][COMPONENTS[2]], -6.)
        self.assertEqual(joint['B']['short']['removed'][COMPONENTS[2]], -1.)

    def test_cash_unknown_inputs_do_not_fabricate_contributions(self):
        q = np.zeros((2, 2)); absent = np.full_like(q, np.nan)
        self.assertEqual(totals(components(q, absent, absent, absent))['net_USDT'], 0.)
        q[0, 0] = 1
        with self.assertRaises(ValueError):
            components(q, absent, absent, absent)

    def test_kept_sizing_and_NAV_identity_is_additive_not_replay(self):
        cs = np.array([[2., -3., 4., 0., 1.]])
        agreement = np.array([[1.5, 0., 5., 0., 0.]])
        gate = np.array([[True, False, True, False, False]])
        p0 = np.full_like(cs, 100.)
        p1 = np.array([[110., 90., 120., 100., 95.]])
        funding = np.array([[2., 3., -1., 0., 1.]])
        identity = quantity_difference_identity(cs, agreement, np.array([10000.]),
            np.array([9000.]), gate, p0, p1, funding)
        self.assertAlmostEqual(sum(x[COMPONENTS[0]] for x in identity['terms'].values()),
                               summed((agreement - cs) * (p1 - p0)))
        self.assertAlmostEqual(sum(x[COMPONENTS[1]] for x in identity['terms'].values()),
                               summed(-(agreement - cs) * funding))

    def test_long_funding_debit_short_funding_credit(self):
        q = np.array([[2., -3.]])
        p = np.full_like(q, 100.)
        value = components(q, p, p, np.full_like(q, 4.))
        np.testing.assert_array_equal(value[COMPONENTS[1]], [[-8., 12.]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true', help='Tiny synthetic arithmetic only')
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ArithmeticTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            raise SystemExit(1)
        return
    report = build_report()
    (HERE / 'ATTRIBUTION.json').write_text(json.dumps(report, indent=2, sort_keys=True,
                                                    allow_nan=False) + '\n')
    (HERE / 'ATTRIBUTION.md').write_text(markdown_report(report))
    print(json.dumps(dict(status=report['status'],
                         years={y: v['AGREEMENT_minus_CS']['totals'] for y, v in report['years'].items()},
                         outputs=['ATTRIBUTION.json', 'ATTRIBUTION.md']), indent=2))


if __name__ == '__main__':
    main()
