"""Read saved full-wallet comparisons; gate one predeclared fast-short rule."""
import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE


def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cost', choices=['BASE27','STRESS43'], required=True)
    a=ap.parse_args()
    producer=ROOT/f'reports/fast_research/SHORT_FAST4H_{a.cost}_20261006_V1.json'
    raw=json.loads(producer.read_bytes()); spec=raw['protocol']
    assert raw['status']=='COMPLETE_FROZEN_CTA_2_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS'
    assert raw['models_fit']==raw['search_configurations']==0 and len(raw['cases'])==2
    task=STATE/'task-progress'/('task-'+raw['binding']['task_id']+'.json')
    terminal=json.loads(task.read_bytes()); assert terminal['status']=='completed' and terminal['exit_code']==0
    assert datetime.fromisoformat(spec['created_utc']).timestamp() < terminal['started_at']
    for p,h in raw['binding']['source_hashes'].items(): assert sha(ROOT/p)==h,p
    p=ROOT/spec['research_primary_reference']['path']; assert sha(p)==spec['research_primary_reference']['sha256']
    prior=json.loads(p.read_bytes()); assert prior['actual_days']==303 and prior['initial_capital_per_counterfactual_USDT']==10000
    original=ROOT/f'reports/fast_research/SHORT_CONFIRMATION_{a.cost}_20261006_V1.json'
    old_raw=json.loads(original.read_bytes())
    for k in ('symbols','data_manifest','economics_start','economics_end_exclusive','cost','resources','locked_sha256'):
        assert old_raw['protocol'][k]==spec[k],k
    assert raw['fast_signal_reference']['status']=='PASS_INDEPENDENT_SCALAR_FAST_SIGNALS'
    pairs=[]
    for c in raw['cases']:
        s=c['summary']; independent=c['independent']
        assert independent['maximum_NAV_error_USDT']<1e-7 and independent['maximum_wallet_error_USDT']<1e-7
        assert independent['target_reference']['status']=='PASS_INDEPENDENT_ORDERED_INVERSE_VOL_SIGNED_COV_TARGETS'
        for v in c['artifacts'].values(): assert sha(v['path'])==v['sha256']
        old=next(r for r in prior['rows'] if r['cost']==a.cost and r['unit']==c['unit'])
        journal=json.loads(Path(c['artifacts']['protection_journal.json']['path']).read_bytes())
        triggers=[v for v in journal if v['kind']=='OBSERVED_FAST_CONFIRMATION_LOSS']
        fills=[v for v in journal if v['kind']=='FAST_CONFIRMATION_EXIT_FILL']
        for v in triggers: assert v['event_us']%14_400_000_000==0 and v['fast_state']!=-1
        for v in fills:
            assert abs(v['quantity_after'])<abs(v['quantity_before']) and v['quantity_before']*v['quantity_after']>=0
            assert v['event_us']>=v['signal_us']+60_000_000+1
        new=dict(id=c['id'],cost=a.cost,unit=c['unit'],complete=s['completed_minutes']==s['required_minutes'],
            paid_flat=s['terminal_cash_realized'],net=s['net_PnL'],gross=s['gross_PnL_same_quantities'],
            fees=s['fees_USDT'],execution=s['execution_cost_USDT'],funding=s['funding_USDT'],
            LONG=s['long_short_marked_contribution']['LONG']['net_contribution'],
            SHORT=s['long_short_marked_contribution']['SHORT']['net_contribution'],
            DD=s['minute_max_drawdown'],vol=s['daily_metrics']['annual_volatility'] if s['daily_metrics'] else None,
            Sharpe=s['daily_metrics']['sharpe'] if s['daily_metrics'] else None,
            turnover=s.get('normalized_total_turnover'),risk=s.get('realized_exposure'),
            residual=s['terminal_marked_notional'],regimes=independent['by_past_regime'],
            concentration=s.get('daily_net_gain_concentration'),actual_short_open_or_add_legs=independent['actual_short_open_legs'],
            short_exit_fill_fragments=sum(v['quantity_before']<0 for v in fills),
            long_cleanup_fill_fragments=sum(v['quantity_before']>0 for v in fills),
            four_hour_observed_short_exit_events=len(triggers),reference=old)
        assert abs(new['gross']+new['funding']-new['fees']-new['execution']-new['net'])<1e-7
        assert abs(new['LONG']+new['SHORT']-new['net'])<1e-7
        new['delta']={k:new[k]-old[k] if new[k] is not None else None for k in ('net','gross','fees','execution','funding','LONG','SHORT','DD','vol')}
        new['delta']['SHORT_BEAR']=new['regimes'].get('BEAR',{}).get('SHORT',0)-old['regimes'].get('BEAR',{}).get('SHORT',0)
        new['passes_predeclared']=(new['complete'] and new['paid_flat'] and new['delta']['net']>0 and new['delta']['SHORT']>0
            and new['delta']['SHORT_BEAR']>0 and new['delta']['DD']<=0 and new['delta']['vol']<=0
            and new['regimes'].get('BULL',{}).get('SHORT',0)>=0)
        # Every UTC calendar month, not a selection of profitable dates.
        new['months']=s['months']
        pairs.append(new)
    out=ROOT/f'reports/SHORT_FAST4H_{a.cost}_REVIEW_20261006_V1.json'; assert not out.exists()
    result=dict(status='PASS_PAIRED_FAST_SHORT_REVIEW_NOT_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],
        created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),
        producer=dict(path=str(producer.relative_to(ROOT)),sha256=sha(producer),task_id=raw['binding']['task_id'],task_sha256=sha(task)),
        protocol_sha256=raw['binding']['protocol_sha256'],reference_sha256=sha(p),pairs=pairs,
        all_pass=all(v['passes_predeclared'] for v in pairs),new_account_replays=0,models_fit=0,
        actual_days=raw['actual_days'],fast_warmup=raw['fast_warmup_scope'],
        short_daily_decisions_suppressed=raw['short_daily_decisions_suppressed'],
        scope='INDEPENDENT_SCALAR_FAST_SIGNAL_AND_DECIMAL_WALLET_CHECKS_BOUND; SAVED_ARTIFACT_PAIRED_REVIEW_NOT_NEW_REPLAY',
        limitations=['SEEN_DEVELOPMENT_NOT_UNSEEN','BINANCE_USDM_BYBIT_COST_PROXY',
            'FUNDING_UNIT_UNKNOWN_TWO_INTERPRETATIONS','NATIVE_MMR_TIERS_NOT_CERTIFIED',
            'PAST_BTC_REGIMES_NOT_OWN_ASSET_BULL_BEAR_TRUTH','SAME_CAPS_NOT_SAME_ACTUAL_RISK',
            'INTRADAY_FLATTENING_ONLY_REENTRY_DAILY_NOT_CONTINUOUS_FAST_STRATEGY',
            'ACTUAL_LONG_PNL_CAN_CHANGE_VIA_SIGNED_COVARIANCE_AND_SHARED_CAPITAL'])
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(dict(all_pass=result['all_pass'],pairs=[{k:v[k] for k in ('unit','net','SHORT','DD','vol','delta','passes_predeclared')} for v in pairs])))


if __name__=='__main__': main()
