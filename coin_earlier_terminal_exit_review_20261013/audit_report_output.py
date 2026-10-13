"""Independent final report/journal reconciliation. No financial advances."""
from pathlib import Path
from decimal import Decimal, localcontext
import csv
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
POST=ROOT/'coin_earlier_terminal_postrun_20261013'
MODULE=ROOT/'coin_earlier_terminal_exit_20261013'
STATE=MODULE/'state_resumed_authorized_once'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())

assert sha(POST/'RESULTS_COMPACT.json')=='8c9ab943b7fe743dff4423ebf5a2867dc8e2172f2ea647b9aab8231442d5e9ca'
assert sha(POST/'SUMMARY.md')=='d63dc78f27b946f844c686c4e81dc85d6e8bf9092bdc2fdc0b1aec11bb16b6a4'
plan=read(MODULE/'CASE_BINDINGS.json')
report=read(POST/'RESULTS_COMPACT.json')
summary=(POST/'SUMMARY.md').read_text()
assert report['case_count']==len(report['cases'])==2
assert report['capital_per_wallet_USDT']==10000
assert report['year']==2025 and report['calendar_end_us']==1767225600000000
assert report['terminal_real_opens']==60
assert report['original_resource_STOP_preserved'] is True
assert report['original_resource_STOP_receipt_SHA256']==sha(MODULE/'state_first_authorized_run/RESOURCE_RECEIPTS.json')
assert {r['case_id'] for r in report['cases']}=={c['case_id']+'_FINE_ORIGINAL' for c in plan['cases']}
checks=[]
for case in plan['cases']:
    identity=case['case_id']+'_FINE_ORIGINAL'
    entry=next(r for r in report['cases'] if r['case_id']==identity)
    assert entry['arm']==case['display_arm'] and entry['target_array_SHA256']==case['target_array_SHA256']
    for label,directory in (('old',ROOT/case['baseline_state_local_locator']),('new',STATE/identity)):
        result=read(directory/'RESULT.json')
        account=read(directory/'ACCOUNT.json')
        shown=entry[label]
        for key in ('full_calendar','paid_flat','paid_cash_PnL_USDT','marked_PnL_USDT','minute_drawdown',
                    'mean_actual_gross','max_actual_gross','trade_legs','terminal_residual_quantity',
                    'terminal_residual_gross_notional_USDT','terminal_residual_marked_notional_USDT',
                    'completion','account_status','completed_minutes','required_minutes','stop_us',
                    'mean_actual_signed_net','max_actual_abs_signed_net'):
            assert shown[key]==result.get(key),(identity,label,key)
        for key in ('gross_fill_turnover_USDT','fees_USDT','execution_cost_USDT','funding_USDT',
                    'risk_reduction_signal_count','minimum_actual_free_cash_all_observations_USDT'):
            assert shown[key]==account['summary'][key],(identity,label,key)
        with localcontext() as context:
            context.prec=50
            fees=sum((Decimal(x['decimal_strings']['fee_amount']) for x in account['trades']),Decimal(0))
            execution=sum((Decimal(x['decimal_strings']['execution_cost']) for x in account['trades']),Decimal(0))
            turnover=sum((Decimal(x['decimal_strings']['quantity'])*Decimal(x['decimal_strings']['fill_price'])
                          for x in account['trades']),Decimal(0))
            funding=sum((Decimal(x['decimal_strings']['signed_funding_USDT']) if 'decimal_strings' in x else
                         Decimal(str(x['signed_funding_USDT'])) for x in account['funding']),Decimal(0))
        assert shown['fees_USDT']==float(fees)
        assert shown['execution_cost_USDT']==float(execution)
        assert shown['gross_fill_turnover_USDT']==float(turnover)
        assert shown['funding_USDT']==float(funding)
        assert entry['account_hashes'][label]==sha(directory/'ACCOUNT.json')
        with (directory/'DAILY.csv').open() as f:
            rows=list(csv.DictReader(f))
        assert len(rows)==365
        nav=[10000.]+[float(r['nav']) for r in rows]
        returns=[nav[i+1]/nav[i]-1 for i in range(365)]
        mean=sum(returns)/365
        vol=math.sqrt(sum((r-mean)**2 for r in returns)/364*365)
        assert abs(shown['annual_daily_vol']-vol)<=1e-12
        if 'annual_daily_vol' in result:
            assert abs(shown['annual_daily_vol']-result['annual_daily_vol'])<=1e-12
        worst=min(nav[i]/nav[i-30]-1 for i in range(30,len(nav)))
        assert shown['worst_observed_30_days']==worst
        assert len(shown['month_end_cumulative_PnL_USDT'])==12
        assert set(shown['month_end_cumulative_PnL_USDT'])=={f'2025-{m:02d}' for m in range(1,13)}
        assert abs(shown['month_end_cumulative_PnL_USDT']['2025-12']-result['marked_PnL_USDT'])<=1e-9
        assert result['full_calendar'] is True
        if label=='old':
            assert result['paid_flat'] is False and shown['paid_cash_PnL_USDT'] is None
        else:
            assert result['paid_flat'] is True and shown['paid_cash_PnL_USDT']==shown['marked_PnL_USDT']
            assert all(Decimal(q)==0 for q in shown['terminal_residual_quantity'].values())
    for key,value in entry['same_clock_new_minus_old_numeric_delta'].items():
        assert value==entry['new'][key]-entry['old'][key]
    assert entry['cold']['pre_intervention_numeric_minutes_checked']==525540
    assert entry['recovery_cold']['financial_advances']==0
    assert f"Original marked PnL {entry['old']['marked_PnL_USDT']:+.6f} USDT; new paid cash PnL {entry['new']['marked_PnL_USDT']:+.6f} USDT." in summary
    checks.append(dict(case_id=identity,old_marked_PnL_USDT=entry['old']['marked_PnL_USDT'],
        new_paid_cash_PnL_USDT=entry['new']['paid_cash_PnL_USDT'],
        marked_new_minus_old_delta_USDT=entry['same_clock_new_minus_old_numeric_delta']['marked_PnL_USDT'],
        original_residual_gross_USDT=entry['old']['terminal_residual_gross_notional_USDT'],
        new_residual_gross_USDT=entry['new']['terminal_residual_gross_notional_USDT'],
        full_minutes=525600,exact_prefix_minutes=525540,month_count=12,
        Decimal_cost_funding_turnover_journal_sums_agree=True))
out=dict(status='PASS_INDEPENDENT_FINAL_REPORT_AND_DECIMAL_JOURNALS',
    results_SHA256=sha(POST/'RESULTS_COMPACT.json'),summary_SHA256=sha(POST/'SUMMARY.md'),
    report_review_SHA256=sha(POST/'REPORT_REVIEW_RECEIPT.json'),
    financial_advances=0,new_wallets=0,checks=checks,
    annual_vol_reporting_reduction_absolute_tolerance=1e-12,
    month_end_float_subtraction_absolute_tolerance_USDT=1e-9,
    exact_financial_metrics_and_journal_sums=True)
with (HERE/'FINAL_REPORT_OUTPUT_REVIEW_RECEIPT.json').open('x') as f:
    json.dump(out,f,indent=2,sort_keys=True)
    f.write('\n')
print(json.dumps(out,indent=2,sort_keys=True))
