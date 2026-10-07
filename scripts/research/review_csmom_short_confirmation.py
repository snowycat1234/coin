"""Independent stdlib JSON arithmetic only: no ledger, market, fit or wallet reads."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
DAY = 86_400_000_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def near(a, b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-7), (a, b)


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', type=Path, default=ROOT/'reports/CSMOM_ABSOLUTE_SHORT_20261008.json')
    ap.add_argument('--output', type=Path, default=ROOT/'reports/CSMOM_ABSOLUTE_SHORT_REVIEW_20261008.json')
    a = ap.parse_args(); began = time.monotonic()
    protocol = ROOT/'protocols/CSMOM_ABSOLUTE_SHORT_20261008.json'
    r, p = load(a.result), load(protocol)
    assert r['status'] == 'COMPLETE_ONE_ABSOLUTE_SHORT_CONFIRMATION'
    assert r['protocol'] == p and r['protocol_sha256'] == sha(protocol)
    assert r['new_wallets'] == p['budget']['new_wallets'] == 10 and r['new_fits'] == p['budget']['new_fits'] == 0
    assert p['budget']['new_configs'] == 1 and r['qualification'] == p['qualification'] == 'NONE_CASH'
    assert r['locked_consumed'] is False and p['data_role'].startswith('ALL_SEEN_DEVELOPMENT_ONLY')
    assert (p['capital'], p['max_asset_abs'], p['max_gross'], p['leverage']) == (10000, .3, .6, 1)
    assert p['automatic_margin_topup'] is False and p['funding_scales'] == [1, .01]
    assert sha(ROOT/p['parent_protocol']) == p['parent_protocol_sha256']
    for name, expected in p['input_report_hashes'].items():
        assert sha(ROOT/name) == expected, name
    prior, extension = (load(ROOT/name) for name in p['input_reports'][:2])
    assert not all(prior['checks'].values()) and not all(extension['checks'].values())
    assert extension['prior_allstage_failure_unchanged'] and extension['prior_checks'] == prior['checks']
    assert extension['decision'] == 'PAUSE_UNCONDITIONAL_FIXED_BLEND_RECIPE'
    original = prior['reused_csmom_controls'] + [x for x in extension['cases'] if x['family'] == 'PUBLIC_CSMOM21_WEEKLY']
    key = lambda x: (x['window'], x['funding_scale'])
    windows = {w['id']: w for w in p['windows']}
    assert len(windows) == 5 and [(w['fold'], w['days']) for w in windows.values()] == [(1, 182), (2, 41), (2, 142), (3, 181), (4, 184)]
    for w in windows.values():
        assert w['end'] - w['start'] == w['days'] * DAY and w['end'] < 1772323200000000
        assert w['active_symbols'] == p['core_symbols']
    expected = {(w, s) for w in windows for s in p['funding_scales']}
    new = {key(x): x for x in r['cases']}; old = {key(x): x for x in r['reused_controls']}
    saved = {key(x): x for x in original}
    assert set(new) == set(old) == set(saved) == expected
    assert len(r['cases']) == len(r['reused_controls']) == len(original) == 10
    for cell, control in old.items():
        assert control['family'] == 'PUBLIC_CSMOM21_WEEKLY'
        for field, value in control.items():
            if field != 'kind':
                assert saved[cell][field] == value, (cell, field)
    losses = [x for x in old.values() if x['window'].startswith('fold1')]
    assert len(losses) == 2 and all(x['net_PnL'] < 0 for x in losses)

    errors, summaries = [], []
    for role, accounts in (('NEW', new), ('REUSED', old)):
        for cell, x in sorted(accounts.items()):
            w = windows[cell[0]]; m = x['daily_metrics']; legs = x['contributions']; months = x['months']
            family = 'CSMOM21_ABSOLUTE_SHORT' if role == 'NEW' else 'PUBLIC_CSMOM21_WEEKLY'
            unit = 'raw_fraction' if cell[1] == 1 else 'raw_percent'
            assert x['family'] == family and x['result_path'].endswith('/'+unit+'/'+cell[0]+'/'+family+'/RESULT.json')
            assert digest(x['result_sha256']) and x['terminal_cash_realized'] is True
            assert x['complete_minutes'] == w['days'] * 1440 and m['days'] == w['days']
            assert m['initial_nav'] == 10000 and x['audit_status'].startswith('PASS_') and 0 <= x['maximum_NAV_error'] <= 1e-7
            assert x['fees'] >= 0 and x['execution_cost'] >= 0 and x['liquidations'] >= 0
            bridge = x['gross_PnL'] - x['fees'] - x['execution_cost'] + x['funding']
            near(bridge, x['net_PnL']); errors.append(abs(bridge-x['net_PnL']))
            near(m['final_nav']-10000, x['net_PnL']); near(m['total_return'], x['net_PnL']/10000)
            near(m['annual_return'], (m['final_nav']/10000)**(365/w['days'])-1)
            near(m['fees'], x['fees']); near(m['execution_costs'], x['execution_cost']); near(m['turnover']/10000, x['turnover'])
            assert set(legs) == {'LONG', 'SHORT'}
            for leg in legs.values():
                near(leg['gross']-leg['fees']-leg['execution_cost']+leg['funding'], leg['net_contribution'])
            for field, total in (('gross', 'gross_PnL'), ('fees', 'fees'), ('execution_cost', 'execution_cost'), ('funding', 'funding'), ('net_contribution', 'net_PnL')):
                near(sum(z[field] for z in legs.values()), x[total])
            assert months and sum(z['days'] for z in months) == w['days'] and len({z['month'] for z in months}) == len(months)
            nav = 10000.
            for z in months:
                near(z['gross_PnL']-z['fees']-z['spread_cost']-z['slippage_cost']+z['funding_USDT'], z['net_PnL'])
                nav += z['net_PnL']; near(nav, z['ending_NAV'])
            for field, total in (('gross_PnL', 'gross_PnL'), ('net_PnL', 'net_PnL'), ('fees', 'fees'), ('funding_USDT', 'funding')):
                near(sum(z[field] for z in months), x[total])
            near(sum(z['spread_cost']+z['slippage_cost'] for z in months), x['execution_cost'])
            assert set(months[-1]['ending_signed_quantities']) == set(p['symbols'])
            assert all(v == 0 for v in months[-1]['ending_signed_quantities'].values())
            summaries.append(dict(role=role, window=cell[0], funding_scale=cell[1], net_PnL=x['net_PnL'], LONG_net=legs['LONG']['net_contribution'], SHORT_net=legs['SHORT']['net_contribution'], vol=m['annual_volatility'], minute_MDD=x['minute_MDD'], cost=x['fees']+x['execution_cost'], gross_peak=x['exposure']['minute_max_gross_weight'], liquidations=x['liquidations']))

    contrasts = []
    declared = {key(x): x for x in r['contrasts']}
    assert set(declared) == expected and len(r['contrasts']) == 10
    for cell, x in sorted(new.items()):
        b = old[cell]
        delta = dict(window=cell[0], funding_scale=cell[1], net_increment=x['net_PnL']-b['net_PnL'], SHORT_increment=x['contributions']['SHORT']['net_contribution']-b['contributions']['SHORT']['net_contribution'], LONG_increment=x['contributions']['LONG']['net_contribution']-b['contributions']['LONG']['net_contribution'], MDD_change=x['minute_MDD']-b['minute_MDD'], vol_change=x['daily_metrics']['annual_volatility']-b['daily_metrics']['annual_volatility'], turnover_change=x['turnover']-b['turnover'], cost_change=x['fees']+x['execution_cost']-b['fees']-b['execution_cost'])
        assert set(declared[cell]) == set(delta)
        for field, value in delta.items():
            if field == 'window': assert declared[cell][field] == value
            else: near(declared[cell][field], value)
        near(delta['LONG_increment']+delta['SHORT_increment'], delta['net_increment'])
        contrasts.append(delta)
    proofs = r['target_proofs']; assert len(proofs) == 5 and {x['window'] for x in proofs} == set(windows)
    for x in proofs:
        assert digest(x['target_sha256']) and x['future_suffix_unchanged'] and x['no_target_leg_increased'] and x['available_us_never_after_decision']
        assert 0 <= x['asset_order_max_error'] <= 1e-14 and 0 <= x['mean_confirmed_gross'] <= x['mean_original_gross'] + 1e-14
        assert 0 <= x['days_any_suppressed'] <= windows[x['window']]['days'] and x['short_intents_suppressed'] >= x['days_any_suppressed']
    later = [x for x in new.values() if windows[x['window']]['fold'] in (3, 4)]; assert len(later) == 4
    gates = dict(no_liquidation=all(x['liquidations']==0 for x in new.values()), all_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in new.values()), all_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in new.values()), each_pair_net_or_DD_improves=all(x['net_increment']>=0 or x['MDD_change']<0 for x in contrasts), at_least8_of10_net_positive=sum(x['net_PnL']>0 for x in new.values())>=8, both2025_stages_SHORT_positive=all(x['contributions']['SHORT']['net_contribution']>0 for x in later))
    assert gates == r['checks'] and set(gates) == set(p['checks'])
    decision = 'RETAIN_FOR_INDEPENDENT_VALIDATION' if all(gates.values()) else 'PAUSE_EXACT_CONFIRMATION_RECIPE'
    assert decision == r['decision'] and r['GPU'] == r['swap'] == 0 and r['RAM_limit_bytes'] <= 8_000_000_000
    assert r['owned_bytes'] <= p['budget']['new_owned_bytes'] and r['elapsed_seconds'] <= p['budget']['wall_seconds']
    review = dict(status='PASS_WITH_LIMITATIONS', source_sha256=sha(__file__), result_sha256=sha(a.result), protocol_sha256=sha(protocol), accounts_checked=20, new_cases=10, reused_controls=10, target_proofs_checked=5, max_abs_cash_bridge_error=max(errors), cells=summaries, paired_contrasts=contrasts, gates=gates, decision=decision, original_2024H1_negative_preserved=True, prior_fixed_blend_failure_preserved=True, qualification='NONE_CASH', new_review_wallets=0, new_review_fits=0, elapsed_seconds=time.monotonic()-began, limitations=['Only saved JSON arithmetic and exact old summary identities checked; no server ledger, market, target arrays or raw account CASE files reread.', 'Target default goldens, financial source/fee/unit identity and minute audit rely on the bound runner and existing independent audits; target proof booleans are not independently re-executed.', 'Five seen development windows remain separate full10k accounts; no return summation or NAV stitching. Two funding interpretations are not independent samples. Short-window annualized returns are descriptive, not stable APR.', 'Absolute-sign veto plus necessary covariance downscale changes exposure and shared capital paths; contribution differences are not pure timing alpha or matched-risk superiority.', 'Original losses, source gap, conditional funding/Bybit rules and historical gross-cap drift remain; no live safety or investment qualification.'])
    with a.output.open('x') as f:
        json.dump(review, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(status=review['status'], accounts=20, gates=gates, decision=decision, elapsed_seconds=review['elapsed_seconds'])))


if __name__ == '__main__':
    main()
