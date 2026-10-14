"""Offline fixed-observed-path arithmetic; no strategy engine or network access."""
import json
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec = 80
D = Decimal
TOL = D('1e-30')
MULTIPLIERS = ('1', '1.5', '2', '3')


def sensitivity(net, fees, execution):
    if fees < 0 or execution < 0:
        raise ValueError('Charges must be nonnegative')
    cost = fees + execution
    scenarios = {m: {'extra_charge_USDT': (D(m)-1)*cost,
                     'static_net_PnL_USDT': net-(D(m)-1)*cost}
                 for m in MULTIPLIERS}
    # A rational pair preserves the exact threshold even when division repeats.
    return {'combined_cost_USDT': cost, 'scenarios': scenarios,
            'breakeven_multiplier': 1+net/cost if cost else None,
            'breakeven_exact_numerator': cost+net if cost else None,
            'breakeven_exact_denominator': cost if cost else None}


def analyze(d):
    if not (d['complete_calendar'] and d['terminal_cash_realized'] and
            d['completed_minutes'] == d['required_minutes'] == 525600 and
            d['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'):
        raise ValueError('Incomplete or unrealized source')
    v = {k: D(x) for k,x in d['decimal_strings'].items()}
    if not all(x.is_finite() for x in v.values()):
        raise ValueError('Nonfinite value')
    if v['unpaid_liability'] != 0:
        raise ValueError('Unpaid liability')
    n,f,e,u,g = [v[k] for k in ('net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','gross_PnL_same_quantities')]
    bridge = n-(g-f-e+u)
    if abs(bridge) > TOL:
        raise ValueError('Signed funding accounting identity does not reconcile')
    capital = D(d['paid_NAV_decimal'])-n
    if capital != 10000 or D(d['paid_NAV_decimal']) != v['NAV']:
        raise ValueError('Capital or NAV mismatch')
    return {'initial_NAV_USDT':capital,'net_PnL_USDT':n,
            'fees_paid_USDT':f,'execution_cost_USDT':e,
            'signed_funding_USDT':u, 'funding_outflow_USDT':-u,
            'saved_gross_PnL_same_quantities_USDT':g,
            'reconstructed_gross_USDT':n+f+e-u,
            'accounting_residual_USDT':bridge,
            **sensitivity(n,f,e)}


def run(root):
    catalog=json.loads((root/'SOURCE_CATALOG.json').read_text())
    arms={s['id']:analyze(json.loads((root/s['input_file']).read_text())) for s in catalog}
    paired={}
    for year in (2023,2025):
        g,c=[arms[f'{year}_{a}'] for a in ('grid','cash')]
        dn=g['net_PnL_USDT']-c['net_PnL_USDT']
        dc=g['combined_cost_USDT']-c['combined_cost_USDT']
        paired[str(year)]={'baseline_GRID_minus_CASH_USDT':dn,
            'GRID_minus_CASH_cost_USDT':dc,
            'scenarios_GRID_minus_CASH_USDT':{m:dn-(D(m)-1)*dc for m in MULTIPLIERS},
            'equality_multiplier':1+dn/dc if dc else None,
            'equality_exact_numerator':dc+dn if dc else None,
            'equality_exact_denominator':dc if dc else None}
    result={'method':'STATIC_FIXED_OBSERVED_PATH_NOT_REBACKTEST',
            'decimal_precision':80,'accounting_check_tolerance_USDT':TOL,
            'funding_held_fixed':True,'funding_unit':'UNCONFIRMED',
            'arms':arms,'paired':paired}
    (root/'results').mkdir(exist_ok=True)
    (root/'results/RESULTS.json').write_text(json.dumps(result,default=str,indent=2)+'\n')
    return result

if __name__=='__main__':
    run(Path(__file__).resolve().parent)
