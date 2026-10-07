"""Outcome-blind five-case supplement; original formal v2 N/E stays immutable."""
import argparse,json,time
from pathlib import Path
import numpy as np
import pandas as pd
from modules.transformer_v2.train import atomic,sha
from .sources import GAPS

SCENARIOS=('ZERO_EVENT','LINEAR_INTERPOLATION','PREVIOUS','NEXT','FORMULA_RECONSTRUCTED')

def formula_1minute(premium):
    p=np.asarray(premium,dtype=float)
    if p.shape!=(240,) or not np.isfinite(p).all():raise ValueError('Exactly240 observed finite premium minutes required')
    # Approximate twelve5-second observations per minute by its observed close.
    # Sum the official ordinal weights within each minute, without interpolating.
    weights=np.arange(1,2881,dtype=float).reshape(240,12).sum(1)
    average=float(p@weights/weights.sum())
    rate=(average+float(np.clip(.0001-average,-.0005,.0005)))/2.
    return average,rate

def scenario_rates(previous,next_rate,premium,scale):
    if not np.isfinite([previous,next_rate,scale]).all() or scale not in (1.,.01):raise ValueError('Observed neighbor rates and registered unit scale required')
    average,rate=formula_1minute(premium)
    raw=dict(ZERO_EVENT=0.,LINEAR_INTERPOLATION=(previous+next_rate)/2.,PREVIOUS=previous,NEXT=next_rate,FORMULA_RECONSTRUCTED=rate/scale)
    return [dict(scenario=name,engine_raw_rate=raw[name],normalized_rate_fraction=raw[name]*scale,
                 funding_scale=scale,role='FORMULA_APPROXIMATION_FROM_1MIN_PREMIUM' if name=='FORMULA_RECONSTRUCTED' else 'IMPUTED_UNCONFIRMED_EVENT_SENSITIVITY',
                 average_premium=average if name=='FORMULA_RECONSTRUCTED' else None,
                 exact_Binance_settlement=False) for name in SCENARIOS]

def premium_period(frame):
    period=np.arange(1782259200000000,1782273600000000,60_000_000)
    # mark/premium canonical tables retain timestamp_ms; only trade klines have open_us.
    q=frame.loc[(frame.timestamp_ms*1000>=period[0])&(frame.timestamp_ms*1000<1782273600000000)].sort_values('timestamp_ms')
    if not np.array_equal(q.timestamp_ms.to_numpy()*1000,period) or not (q.available_us<=1782273600000000).all():
        raise ValueError('Premium funding-period clock is incomplete or includes future observations')
    return q.close.to_numpy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);a=p.parse_args();state=Path(a.state);old=Path(a.v2_state)
    assert (state/'PHASE0_V2_PRESERVATION.json').exists() and (state/'FUNDING_SOURCE_REQUESTS.json').exists()
    assert not (state/'LOCKED_BRIDGE_PREREGISTRATION.json').exists()
    assert not any((state/'native').rglob('RESULT.json')) and not any((state/'fits').rglob('RESULT.json')),'Bridge must precede any new economic result or fit'
    manifest=json.loads((old/'LOCKED_DATA_MANIFEST.json').read_text());base=Path(manifest['work'])/'data/normalized'
    rows=[];proofs=[];event=1782273600000
    for symbol in GAPS:
        fund_path=base/f'{symbol}_funding_events.parquet';f=pd.read_parquet(fund_path)
        assert not ((f.calc_time_ms-event).abs()<1000).any(),'Exact official event already present; do not impute'
        left=f.loc[(f.calc_time_ms-1782259200000).abs()<1000];right=f.loc[(f.calc_time_ms-1782288000000).abs()<1000]
        assert len(left)==len(right)==1 and int(left.iloc[0].funding_interval_hours)==int(right.iloc[0].funding_interval_hours)==4
        price_path=base/'minute'/symbol/'premiumIndexKlines/2026-06.parquet';q=pd.read_parquet(price_path)
        premium=premium_period(q)
        for scale in (1.,.01):
            for r in scenario_rates(float(left.iloc[0].last_funding_rate),float(right.iloc[0].last_funding_rate),premium,scale):
                rows.append(dict(symbol=symbol,exchange='Binance USD-M',event_us=event*1000,settlement_UTC='2026-06-24 04:00:00 UTC',
                                 previous_timestamp_ms=int(left.iloc[0].calc_time_ms),next_timestamp_ms=int(right.iloc[0].calc_time_ms),
                                 previous_raw_rate=float(left.iloc[0].last_funding_rate),next_raw_rate=float(right.iloc[0].last_funding_rate),**r))
        proofs.extend([dict(symbol=symbol,path=str(p),sha256=sha(p)) for p in (fund_path,price_path)])
    result=dict(status='FIVE_SCENARIOS_FROZEN_BEFORE_NEW_PORTFOLIO_RESULTS',frozen_at=time.time(),scenarios=list(SCENARIOS),rows=rows,input_proofs=proofs,
                original_v2_locked_N_E_sha256=sha(old/'TRANSFORMER_V2_LOCKED_RESULTS.json'),source_requests_sha256=sha(state/'FUNDING_SOURCE_REQUESTS.json'),
                classification='IMPUTED_LOCKED_SENSITIVITY_UNLESS_EXACT_EVENT_RECOVERED',
                no_settlement_confirmation='NOT_ESTABLISHED_HTTP451_202_OR_AUTH_FAILURE_IS_NOT_ABSENCE',
                formula='F=(P+clamp(0.0001-P,-0.0005,+0.0005))/2; P ordinal5sec weighting approximated with observed1min closes',
                formula_caps='User specified formula; no historical funding cap or5sec orderbook exactness claimed',
                formula_unit='Fractional formula result used identically in both interpretations; neighboring archive values retain their respective1.0/0.01 conditional scaling',
                selection='RUN_ALL_FIVE_NO_BEST_SCENARIO_HEADLINE; REPORT_MIN_MEDIAN_MAX_AND_DECISION_CONSISTENCY',
                no_labels_for_training=True,no_portfolio_result_read=True,original_state_modified=False,
                official_formula_reference='https://www.binance.com/en/support/faq/detail/360033525031')
    atomic(state/'LOCKED_BRIDGE_PREREGISTRATION.json',result);print('Frozen five funding bridge scenarios for all three symbols and both conditional interpretations')

if __name__=='__main__':main()
