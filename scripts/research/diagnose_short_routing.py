"""Read-only economic diagnosis of completed expert routing; no fits or wallets."""
import argparse, hashlib, json, os, resource, shutil, time
from bisect import bisect_left
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np
import polars as pl

DAY = 86_400_000_000

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def utc(stamp):
    return datetime.fromtimestamp(stamp / 1e6, UTC).isoformat()

def journal_bridge(trades, funds, unit, scenario):
    """Independent closed-inventory cash identity, not investable short proceeds."""
    D = Decimal
    totals = {s: dict(gross=D(0), fees=D(0), execution_cost=D(0), funding=D(0), net=D(0))
              for s in ('LONG', 'SHORT')}
    q = D(0); episodes = []; active = None
    clocks = [r['event_us'] for r in trades]
    assert clocks == sorted(clocks)
    with localcontext() as ctx:
        ctx.prec = 50
        for r in trades:
            x = r['decimal_strings']; before = D(x['quantity_before']); after = D(x['quantity_after'])
            delta = D(x['position_delta']); assert q == before and after == before + delta
            assert not (before * after < 0), 'Reversal must have separate close/open legs'
            side = before if r['leg'] == 'CLOSE' else delta
            label = 'LONG' if side > 0 else 'SHORT'
            value = totals[label]
            gross = -delta * D(x['mid_price']); fee = D(x['fee_amount'])
            execution = D(x['execution_cost']); cash = -delta * D(x['fill_price']) - fee
            value['gross'] += gross; value['fees'] += fee
            value['execution_cost'] += execution; value['net'] += cash
            if label == 'SHORT':
                if active is None:
                    assert before == 0 and after < 0
                    active = dict(entry_us=r['event_us'], exit_us=None, gross=D(0), fees=D(0),
                                  execution_cost=D(0), funding=D(0), net=D(0), fill_legs=0)
                for k, v in (('gross', gross), ('fees', fee), ('execution_cost', execution), ('net', cash)):
                    active[k] += v
                active['fill_legs'] += 1
                if after == 0:
                    active['exit_us'] = r['event_us']; episodes.append(active); active = None
            q = after
        assert q == 0 and active is None, 'Only complete paid-flat accounts'
        for r in funds:
            prior = bisect_left(clocks, r['event_us']) - 1
            owned_q = D(trades[prior]['decimal_strings']['quantity_after']) if prior >= 0 else D(0)
            assert abs(owned_q - D(str(r['quantity']))) < D('1e-12')
            if not owned_q:
                assert r['signed_funding_USDT'] == 0
                continue
            x = r['decimal_strings']; assert D(x['quantity']) == owned_q
            rate = D(str(r['raw_rate'])) * (D(1) if unit == 'RAW_AS_FRACTION' else D('.01'))
            assert D(r['assumed_fraction_decimal']) == rate
            multiplier = (D(2) if owned_q * rate > 0 else D('.5') if owned_q * rate < 0 else D(1)) if scenario == 'FUNDING_ADVERSE' else D(1)
            effective = rate * multiplier
            assert D(x['rate_fraction']) == effective and r['mark_close_us'] < r['event_us']
            amount = -owned_q * D(x['mark_price']) * effective
            assert abs(amount - D(x['signed_funding_USDT'])) < D('1e-7')
            label = 'LONG' if owned_q > 0 else 'SHORT'
            totals[label]['funding'] += amount; totals[label]['net'] += amount
            if label == 'SHORT':
                owners = [e for e in episodes if e['entry_us'] < r['event_us'] <= e['exit_us']]
                assert len(owners) == 1, 'Short funding must have one actual owned episode'
                owners[0]['funding'] += amount; owners[0]['net'] += amount
        for v in [*totals.values(), *episodes]:
            assert abs(v['net'] - (v['gross'] - v['fees'] - v['execution_cost'] + v['funding'])) < D('1e-7')
    def native(v): return {k: float(x) if isinstance(x, D) else x for k, x in v.items()}
    return {s: native(v) for s, v in totals.items()}, [native(e) for e in episodes]

def main():
    ap = argparse.ArgumentParser()
    for name in ('state', 'protocol', 'output', 'repo'): ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args(); began = time.monotonic(); state = a.state.resolve(); output = a.output.resolve()
    assert os.uname().sysname == 'Linux' and str(state).startswith('/home/ubuntu/coin/execution-state/')
    assert str(output).startswith('/home/ubuntu/coin/execution-state/') and not output.exists()
    protocol = read(a.protocol); delivery = state / 'delivery'
    assert shutil.disk_usage(output.parent).free >= protocol['budget']['server_free_reserve_bytes']
    assert sha(delivery / 'RESULTS.json') == protocol['results_sha256']
    assert sha(delivery / 'FINAL_VERIFICATION.json') == protocol['verification_sha256']
    result = read(delivery / 'RESULTS.json'); final = read(delivery / 'FINAL_VERIFICATION.json')
    assert final['status'] == 'PASS_ALL_28_ACCOUNT_BYTES_AUDITS_CAUSAL_TARGETS_AND_FROZEN_SOURCES'
    assert result['native_account_count'] == final['full_calendar_complete_count'] == 28
    assert sha(state / 'PATHS.json') == result['path_index_sha256']
    cache_proof = read(state / 'cache/INPUT_BINDING.json'); names = cache_proof['names']
    assert cache_proof == result['input_binding'], 'Cache proof must equal the frozen economic input binding'
    assert names == ['CASH', 'HOLD', 'SMA200_SIGNED', 'DONCHIAN20_10', 'DC_TWO_SPEED',
                     'DC_CONFIRMED_SHORT', 'PUBLIC_SMA50_200', 'SMA200_SHORT50']
    assert sha(a.repo / 'scripts/investment/oracle_expert_opportunity.py') == protocol['oracle_source_sha256']
    from scripts.investment.oracle_expert_opportunity import optimal_path
    accounts = []; maximum_error = 0.; proofs = []; envelopes = []; opportunities = []
    lookup = {(r['algorithm'], r['unit'], r['scenario']): r for r in result['accounts']}
    print('[BINDING] 1/1 completed, immutable prior result and acceptance', flush=True)
    for i, detail in enumerate(result['account_details']):
        key = tuple(detail[k] for k in ('algorithm', 'unit', 'scenario')); row = lookup[key]
        assert row['complete'] and row['terminal_cash'] and row['full_calendar_days'] == 365
        files = detail['input_and_account_artifacts']; loaded = {}
        for name in ('trades.json', 'funding.json', 'targets.parquet', 'daily_nav.parquet'):
            ref = files[name]; path = Path(ref['path']).resolve()
            assert path.is_relative_to(state) and path.stat().st_size == ref['bytes'] and sha(path) == ref['sha256']
            proofs.append(dict(path=str(path), sha256=ref['sha256']))
            loaded[name] = pl.read_parquet(path) if name.endswith('.parquet') else read(path)
        bridge, episodes = journal_bridge(loaded['trades.json'], loaded['funding.json'], key[1], key[2])
        for side in ('LONG', 'SHORT'):
            original = detail['long_short_attribution'][side]
            for k in ('gross', 'fees', 'execution_cost', 'funding'):
                maximum_error = max(maximum_error, abs(bridge[side][k] - original[k]))
            maximum_error = max(maximum_error, abs(bridge[side]['net'] - original['net_contribution']))
        maximum_error = max(maximum_error, abs(sum(v['net'] for v in bridge.values()) - row['net_PnL_USDT']))
        daily = loaded['daily_nav.parquet'].sort('day_end_us')
        assert daily.height == 365 and np.all(np.diff(daily['day_end_us'].to_numpy()) == DAY)
        maximum_error = max(maximum_error, abs(daily['nav'][-1] - 10000 - row['net_PnL_USDT']))
        targets = loaded['targets.parquet'].sort('available_us'); weights = targets['target_weight'].to_numpy()
        assert targets.height == 365 and np.array_equal(targets['available_us'].to_numpy() + DAY, daily['day_end_us'].to_numpy())
        months = {}
        for day in detail['independent']['daily_direction_contributions']:
            month = utc(day['day_end_us'] - 1)[:7]; m = months.setdefault(month, {'LONG': 0., 'SHORT': 0.})
            for side in ('LONG', 'SHORT'): m[side] += day[side]
        maximum_error = max(maximum_error, abs(sum(m['SHORT'] for m in months.values()) - bridge['SHORT']['net']))
        accounts.append(dict(algorithm=key[0], unit=key[1], scenario=key[2], net=row['net_PnL_USDT'],
            MDD=row['all_observation_MDD'], volatility=row['daily_volatility'], mean_gross=row['realized_mean_gross'],
            negative_target_days=int((weights < -1e-12).sum()), short_episodes=episodes,
            actual_short_open_legs=sum(r['leg'] == 'OPEN' and r['position_delta'] < 0 for r in loaded['trades.json']),
            journal_bridge=bridge, calendar_month_contribution=months))
        print(f'[JOURNALS] {i+1}/28 {key[0]} {key[1]} {key[2]}', flush=True)
    assert maximum_error < 1e-7
    for unit in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT'):
        frames = []
        for name in names:
            filename = unit + '-' + name + '-targets.parquet'; ref = next(v for v in cache_proof['files'] if v['path'] == filename)
            path = state / 'cache' / filename; assert sha(path) == ref['sha256']
            frame = pl.read_parquet(path).sort('available_us'); assert frame.height == 730
            assert np.array_equal(frame['available_us'].to_numpy(), np.arange(1640995200000000,1704067200000000,DAY))
            frames.append(frame['target_weight'].to_numpy())
        z = np.array(frames).T; hold = z[:, names.index('HOLD')]; trend = z[:, 2:]
        assert np.isfinite(z).all() and (hold >= 0).all()
        lower = hold / 3 - np.abs(trend).sum(axis=1) / 18
        equal = hold / 3 + trend.sum(axis=1) / 18
        envelopes.append(dict(unit=unit, days=730, hold_dominates_each_trend=bool(np.all(np.abs(trend) <= hold[:, None] + 1e-12)),
            fixed_prior_nonshort_proven=bool(np.all(lower >= -1e-12)),
            equal_weight_lower_bound=float(lower.min()), actual_equal_target_minimum=float(equal.min()),
            negative_equal_target_days=int((equal < -1e-12).sum()),
            proof='Observed fixed-prior bound HOLD/3 - sum(abs(six trend targets))/18. Does not constrain dynamic FixedShare/Hedge weights or an expanded asset pool.'))
        path = state / 'cache' / (unit + '-feedback.npy')
        ref = next(v for v in cache_proof['files'] if v['path'] == path.name); assert sha(path) == ref['sha256']
        returns = np.load(path, allow_pickle=False); assert returns.shape == (730, 8)
        for year, offset in ((2022, 0), (2023, 365)):
            variants = {}
            for label, selected in (('SMA_HOLD_CASH', [2, 1, 0]), ('HOLD_CASH', [1, 0])):
                bounds = [(b, min(365, b + 60)) for b in range(0, 365, 60)]
                growth = [[np.prod(1 + returns[offset+b:offset+e, j]) for j in selected] for b, e in bounds]
                starts = [[ [z[offset+b, j]] for j in selected] for b, e in bounds]
                ends = [[ [z[offset+e-1, j]] for j in selected] for b, e in bounds]
                chosen, value = optimal_path(growth, starts, ends, .00135)
                variants[label] = dict(shadow_rebased_net=10000*(value-1), switches=sum(chosen[k] != chosen[k-1] for k in range(1,len(chosen))),
                    winners=[dict(begin_day=b, end_day=e, expert=names[selected[j]],
                        actual_days=e-b, partial_tail=e-b<60,
                        negative_intent_days=int((z[offset+b:offset+e, selected[j]] < -1e-12).sum()))
                        for (b,e),j in zip(bounds,chosen)])
            delta = variants['SMA_HOLD_CASH']['shadow_rebased_net'] - variants['HOLD_CASH']['shadow_rebased_net']
            opportunities.append(dict(year=year, unit=unit, horizon_days=60, variants=variants,
                adding_signed_expert_shadow_increment=delta,
                interpretation='Not isolated SHORT alpha: SMA also changes long exposure. Future informed rebased existing returns, not a new shared wallet.'))
    assert time.monotonic()-began < protocol['budget']['wall_seconds']
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < protocol['budget']['RAM_bytes']
    output.mkdir()
    summary = dict(status='COMPLETE_READ_ONLY_SHORT_ROUTING_DIAGNOSIS', parent_commit=protocol['parent_commit'],
        source_sha256=sha(__file__), protocol_sha256=sha(a.protocol), results_sha256=sha(delivery/'RESULTS.json'),
        verification_sha256=sha(delivery/'FINAL_VERIFICATION.json'), created_utc=datetime.now(UTC).isoformat(),
        accounts=accounts, journal_maximum_reference_error_USDT=maximum_error, prior_artifact_proofs=proofs,
        family_equal_direction_envelope=envelopes, shadow_opportunity_diagnostics=opportunities,
        qualification='NONE_CASH', new_models_fit=0, new_accounts=0, old_evidence_overwritten=False,
        locked_data_read=False, elapsed_seconds=time.monotonic()-began,
        peak_process_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        limits=['Seen BTC cycles; not a multi-asset candidate', 'No short-removal counterfactual; price profits cannot be held fixed when changing positions',
                'Oracle is noncausal and not a global actual-wallet optimum', 'Unknown funding units and assumed historical Bybit costs/risk tiers'])
    with (output/'RESULTS.json').open('x') as f: json.dump(summary,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps(dict(status=summary['status'],maximum_error=maximum_error,
        family_equal_envelopes=envelopes,opportunities=[{k:r[k] for k in ('year','unit','adding_signed_expert_shadow_increment')} for r in opportunities])), flush=True)

if __name__ == '__main__': main()
