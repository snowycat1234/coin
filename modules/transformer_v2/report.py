"""Development evidence tables and one immutable model-selection manifest."""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
from .train import atomic,sha

BASELINES=('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3')

def compact_case(case,legacy=False):
    s=case['summary'];task=case.get('task',{})
    family=case['model'] if legacy else task['family']
    if legacy and family=='TRANSFORMER_SHARED':family='OLD_FROZEN_TRANSFORMER_SHARED'
    attribution=s['long_short_marked_contribution'];metrics=s.get('daily_metrics') or {};exposure=s.get('realized_exposure') or {}
    full=case['economic_calendar_complete'] and case['terminal_cash_realized']
    return dict(family=family,seed='FROZEN_LEGACY' if legacy else task['seed'],mapping='DIRECTIONAL' if legacy else task['mapping'],
        funding_scale=case['funding_scale'] if legacy else task['funding_scale'],window=case['window']['id'] if legacy else task['window']['id'],
        days=case['window']['days'] if legacy else task['window']['days'],full_calendar_and_paid_cash=full,
        native_completion=s.get('completion','UNKNOWN'),completed_minutes=s.get('completed_minutes'),required_minutes=s.get('required_minutes'),
        noncausal=False if legacy else task.get('noncausal',False),net_USDT=s['net_PnL'] if full else None,
        net_return_percent=s['net_return_on_full_initial_capital_percent'] if full else None,
        gross_price_USDT=sum(r['gross'] for r in attribution.values()),fees_USDT=s['fees_USDT'],
        gross_price_return_percent=sum(r['gross'] for r in attribution.values())/100.,
        spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],funding_USDT=s['funding_USDT'],
        turnover_USDT=s['gross_fill_turnover_USDT'],Sharpe=metrics.get('sharpe'),realized_vol=metrics.get('annual_volatility'),
        MDD=s.get('minute_max_drawdown'),long_net_USDT=attribution['LONG']['net_contribution'],short_net_USDT=attribution['SHORT']['net_contribution'],
        long_gross_USDT=attribution['LONG']['gross'],short_gross_USDT=attribution['SHORT']['gross'],
        mean_gross=exposure.get('minute_mean_gross_weight'),max_gross=exposure.get('minute_max_gross_weight'),
        mean_signed_exposure=exposure.get('minute_mean_net_signed_weight'),risk_reduction_signals=s.get('risk_reduction_signal_count'),
        risk_reduction_latency_us=s.get('maximum_observed_first_risk_reduction_latency_us'),
        cost_share_of_positive_gross=(s['fees_USDT']+s['execution_cost_USDT'])/sum(r['gross'] for r in attribution.values()) if sum(r['gross'] for r in attribution.values())>0 else None,
        cost_plus_net_funding_share_of_positive_gross=(s['fees_USDT']+s['execution_cost_USDT']-s['funding_USDT'])/sum(r['gross'] for r in attribution.values()) if sum(r['gross'] for r in attribution.values())>0 else None,
        NAV_audit_error=case['independent_audit']['maximum_NAV_error_USDT'],summary_sha256=case['summary_sha256'],
        monthly_PnL=s.get('months',[]),
        contribution_sum_error=abs(attribution['LONG']['net_contribution']+attribution['SHORT']['net_contribution']-s['net_PnL']))

def compare(rows,protocol):
    index={(r['family'],str(r['seed']),r['mapping'],r['funding_scale'],r['window']):r for r in rows}
    windows=sorted({r['window'] for r in rows});summaries=[];paired=[]
    for family in protocol['models']:
      for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
        scenarios=[]
        for scale in (1.,.01):
            own=[index.get((family,'ENSEMBLE',mapping,scale,w)) for w in windows]
            complete=all(r and r['full_calendar_and_paid_cash'] for r in own)
            if not complete:
                scenarios.append(dict(funding_scale=scale,complete=False));continue
            values=np.array([r['net_return_percent'] for r in own]);delta=[];sma_delta=[];legacy_delta=[]
            for r,w in zip(own,windows):
                strongest=max(index[b,'FROZEN_LEGACY','DIRECTIONAL',scale,w]['net_return_percent'] for b in BASELINES)
                sd=r['net_return_percent']-index['BASE_SMA200_SIGNED','FROZEN_LEGACY','DIRECTIONAL',scale,w]['net_return_percent']
                ld=r['net_return_percent']-index['OLD_FROZEN_TRANSFORMER_SHARED','FROZEN_LEGACY','DIRECTIONAL',scale,w]['net_return_percent']
                delta.append(r['net_return_percent']-strongest);sma_delta.append(sd);legacy_delta.append(ld)
                paired.append(dict(family=family,mapping=mapping,funding_scale=scale,window=w,net_return_percent=r['net_return_percent'],
                    delta_strongest_static_pct=delta[-1],delta_SMA_pct=sd,delta_old_transformer_pct=ld))
            seeds=[]
            for seed in protocol['seeds']:
                seedrows=[index[family,str(seed),mapping,scale,w] for w in windows]
                if all(r['full_calendar_and_paid_cash'] for r in seedrows):seeds.append(np.array([r['net_return_percent'] for r in seedrows]))
            dispersion=float(np.median(np.std(np.array(seeds),axis=0))) if len(seeds)==3 else None
            stability=len(seeds)==3 and np.std(values)<=np.median([np.std(s) for s in seeds])+1e-9 and values.min()>=np.median([s.min() for s in seeds])-1e-9
            positive=values[values>0];concentration=float(positive.max()/positive.sum()) if len(positive) else None
            passes=bool((values>0).sum()>=4 and np.median(values)>0 and concentration is not None and concentration<=.5 and stability)
            scenarios.append(dict(funding_scale=scale,complete=True,median_net_return_percent=float(np.median(values)),positive_windows=int((values>0).sum()),
                median_paired_delta_strongest_pct=float(np.median(delta)),median_paired_delta_SMA_pct=float(np.median(sma_delta)),
                median_paired_delta_old_transformer_pct=float(np.median(legacy_delta)),wins_vs_SMA=int(sum(v>0 for v in sma_delta)),
                worst_window_return_percent=float(values.min()),positive_window_gain_concentration=concentration,
                ensemble_window_dispersion=float(np.std(values)),median_single_seed_window_dispersion=float(np.median([np.std(s) for s in seeds])) if seeds else None,
                seed_dispersion_median_within_window=dispersion,ensemble_stability_pass=bool(stability),development_gate_pass=passes))
        complete=all(s['complete'] for s in scenarios)
        summaries.append(dict(family=family,mapping=mapping,scenarios=scenarios,
            rank_worst_scale_median_net=min(s['median_net_return_percent'] for s in scenarios) if complete else None,
            rank_worst_scale_median_delta=min(s['median_paired_delta_strongest_pct'] for s in scenarios) if complete else None,
            development_gate_pass=all(s.get('development_gate_pass',False) for s in scenarios)))
    eligible=[s for s in summaries if s['rank_worst_scale_median_net'] is not None]
    assert eligible,'No complete common comparison; locked release prohibited'
    # Ties retain preregistered family and mapping order through stable sort.
    chosen=sorted(eligible,key=lambda s:(s['rank_worst_scale_median_net'],s['rank_worst_scale_median_delta']),reverse=True)[0]
    return summaries,paired,chosen

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--complete-run',required=True);a=p.parse_args()
    state=Path(a.state);repo=Path(__file__).resolve().parents[2];protocol_path=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    protocol=json.loads(protocol_path.read_text());data=json.loads((state/'NATIVE_DEV_RESULTS.json').read_text())
    assert data['status']=='COMPLETE' and not data['errors'] and len(data['cases'])==data['total_cases']
    legacy=json.loads(Path(a.complete_run,'NATIVE_RESULTS.json').read_text());rows=[]
    for case in data['cases']:
        assert sha(case['summary_path'])==case['summary_sha256'] and sha(case['independent_audit_path'])==case['independent_audit_sha256']
        rows.append(compact_case(case))
    for case in legacy['cases']:
        if case['model'] not in (*BASELINES,'BASE_CASH','TRANSFORMER_SHARED','PER_ASSET_XGB'):continue
        assert sha(case['summary_path'])==case['summary_sha256']
        rows.append(compact_case(case,True))
    assert max(r['contribution_sum_error'] for r in rows)<1e-6,'Long/short attribution does not reconcile'
    summaries,paired,chosen=compare(rows,protocol)
    proof=dict(status='DEVELOPMENT_COMPLETE_LOCKED_NOT_READ',protocol_sha256=sha(protocol_path),rows=rows,paired_deltas=paired,
        summaries=summaries,chosen=dict(family=chosen['family'],mapping=chosen['mapping'],seed_rule='FIXED_THREE_SEED_AVERAGE',pool_rule='FIXED_THREE_READOUT_AVERAGE'),
        development_gate_pass=chosen['development_gate_pass'],no_return_splicing=True,locked_consumed=False,
        oracle_role='NONCAUSAL_NONDEPLOYABLE_FUTURE_PROXY_DIAGNOSTIC_NOT_GLOBAL_OPTIMAL_MINUTE_WALLET_BOUND',
        oracle_missing_horizon='Missing 60d/30d future labels never bridge locked boundary; oracle is cash on such dates and cannot certify a tight full-window ceiling',
        old_frozen_baseline='Preserved as separate comparator; new old-architecture seeds use strict inner scaler and registered target scaling',
        prediction_metrics_sha256=sha(state/'PREDICTION_METRICS.json'),fit_binding_sha256=sha(state/'TRAIN_BINDING.json'))
    atomic(state/'TRANSFORMER_V2_DEV_RESULTS.json',proof)
    with (state/'TRANSFORMER_V2_DEV_SUMMARY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# Transformer v2 development report','',
        'Seen development history; these independent reset-wallet returns are never added into one APR. Locked 2026-03 through 2026-08 has not been read.',
        f'Native new cases: {len(data["cases"])}; reused baseline cases: {len(rows)-len(data["cases"])}. Every seed and ensemble is retained.',
        '## Fixed ranking',
        '|Architecture|Mapping|Worst funding median net %|Worst funding paired delta strongest static pct|Development gate|',
        '|---|---|---:|---:|---|']
    for s in summaries:
        def num(v):return 'NOT_EVALUABLE' if v is None else f'{v:.4f}'
        lines.append(f'|{s["family"]}|{s["mapping"]}|{num(s["rank_worst_scale_median_net"])}|{num(s["rank_worst_scale_median_delta"])}|{s["development_gate_pass"]}|')
    lines.extend(['','## Frozen locked candidate',json.dumps(proof['chosen']),
        'The development gate does not change the architecture or locked protocol. A failed gate is carried into the final decision; locked evidence cannot silently erase it.',
        '## Costs, participation and regimes',
        'Full per-seed/per-window net, price gross, fee, spread, slippage, funding, turnover, daily Sharpe/volatility, minute MDD, actual exposure and long/short contribution are in DEV_RESULTS.json and DEV_SUMMARY.csv.',
        'Paired SMA, strongest static and unchanged old Transformer deltas are retained in DEV_RESULTS.json. Prediction losses, IC, Spearman, hit rate and utility rank are in PREDICTION_METRICS.json.',
        'CLS/attention/last ensemble readouts are diagnostics only and are not candidate rankings.',
        '## Oracle qualification',proof['oracle_role'],proof['oracle_missing_horizon'],
        'No oracle is deployable; no oracle enters causal selection. Futures-dependent validity never becomes a candidate availability filter.',
        '## Remaining mandatory phase','Locked evaluation and final decision are not complete. Investment status remains NONE/CASH.'])
    (state/'TRANSFORMER_V2_DEV_REPORT.md').write_text('\n\n'.join(lines)+'\n')
    freeze=dict(status='FROZEN_AFTER_DEVELOPMENT_BEFORE_LOCKED_READ',protocol_sha256=sha(protocol_path),development_results_sha256=sha(state/'TRANSFORMER_V2_DEV_RESULTS.json'),
        development_report_sha256=sha(state/'TRANSFORMER_V2_DEV_REPORT.md'),chosen=proof['chosen'],development_gate_pass=proof['development_gate_pass'],
        prediction_metrics_sha256=sha(state/'PREDICTION_METRICS.json'),frozen_at=time.time(),locked_read=False)
    frozen=state/'LOCKED_CANDIDATE_FREEZE.json'
    if frozen.exists():
        old=json.loads(frozen.read_text());assert all(old[k]==v for k,v in freeze.items() if k!='frozen_at')
    else:atomic(frozen,freeze)
    print(json.dumps(freeze,indent=2))

if __name__=='__main__':main()
