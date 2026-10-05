"""Saved paired-wallet component diagnostic; no producer imports or replays."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(r):
    p=Path(r['path']).resolve();assert (p.is_relative_to(ROOT/'reports') or p.is_relative_to(ROOT/'docs/archive') or p.is_relative_to(STATE))
    assert p.is_file() and not p.is_symlink() and sha(p)==r['sha256'];return json.loads(p.read_bytes())
def frame(r):assert sha(r['path'])==r['sha256'];return pl.read_parquet(r['path'])
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();began=time.monotonic()
c=json.loads(Path(a.config).read_bytes());windows=[]
for label,spec in c['windows'].items():
    half,blend=read(spec['half']),read(spec['blend']);finance=read(spec['financial']);oldfinance=read(spec['control_financial']);target_audit=read(spec['targets']);diag=read(spec['diagnostic'])
    assert finance['input_sha256']==target_audit['input_sha256']==diag['input_sha256']==spec['half']['sha256']
    assert oldfinance['input_sha256']==spec['blend']['sha256']
    assert finance['status']==oldfinance['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
    assert target_audit['target_max_error']<=1e-12 and target_audit['producer_future_perturbation_early_error']<=1e-12
    assert half['daily_bars']==blend['daily_bars'] and half['market_minutes']==blend['market_minutes']
    h,b=frame(half['target_artifact']),frame(blend['target_artifact']);assert h['available_us'].to_list()==b['available_us'].to_list() and h['symbol'].to_list()==b['symbol'].to_list()
    component=np.array([w*.5 for r in blend['target_meta']['risk'] for w in r['component_HOLD_target']])
    component_gap=float(np.max(abs(component-h['target_weight'].to_numpy())));assert component_gap<=1e-12
    cases=[]
    for hc,bc,pair in zip(half['cases'],blend['cases'],diag['pairs'],strict=True):
        assert hc['id']==bc['id']==pair['cost_id'] and hc['symbols']==bc['symbols']
        for key in ('initial_cash','fee_bps','fee_settlement','start_us','end_us','half_spread_bps','slippage_bps','terminal_exit_minutes','min_notional','lot_step_by_symbol'):
            assert hc['config'][key]==bc['config'][key]
        delta=bc['summary']['final_nav']-hc['summary']['final_nav']
        gross=bc['summary']['gross_pnl_before_costs']-hc['summary']['gross_pnl_before_costs']
        cost=(bc['summary']['fees']+bc['summary']['execution_costs'])-(hc['summary']['fees']+hc['summary']['execution_costs'])
        assert abs(delta-(gross-cost))<1e-7
        months={m:-x for m,x in pair['monthly_net_deltas_USDT'].items()};assert abs(sum(months.values())-delta)<1e-7
        dominant=max(months,key=months.get)
        minute_h,minute_b=frame(hc['artifacts']['minute_nav_inventory.parquet']),frame(bc['artifacts']['minute_nav_inventory.parquet'])
        assert minute_h['close_us'].to_list()==minute_b['close_us'].to_list()
        cases.append(dict(id=hc['id'],full_capital=hc['config']['initial_cash'],half_net=hc['summary']['final_nav']-hc['config']['initial_cash'],blend_net=bc['summary']['final_nav']-bc['config']['initial_cash'],
            blend_minus_half_net_USDT=delta,gross_delta_USDT=gross,cost_delta_USDT=cost,monthly_increment=months,
            largest_increment_month=dominant,largest_increment_USDT=months[dominant],all_other_months_increment_USDT=delta-months[dominant],
            half_vol=hc['summary']['annual_volatility'],blend_vol=bc['summary']['annual_volatility'],half_minute_MDD=hc['risk']['minute_max_drawdown'],blend_minute_MDD=bc['risk']['minute_max_drawdown'],
            max_saved_minute_NAV_gap=float(np.max(abs(minute_h['nav'].to_numpy()-minute_b['nav'].to_numpy()))),
            trades_frame_exact_equal=frame(hc['artifacts']['trades']).equals(frame(bc['artifacts']['trades'])),
            half_terminal_cash_realized=hc['terminal_cash_realized'],blend_terminal_cash_realized=bc['terminal_cash_realized'],actual_risk_matched=False))
    windows.append(dict(window=label,days=half['actual_calendar_days'],input_references=spec,component_target_max_gap=component_gap,cases=cases))
out=Path(a.output).resolve();assert out.is_relative_to(ROOT/'reports') or out.is_relative_to(STATE)
with out.open('x') as f:json.dump(dict(status='PASS_PAIRED_COMPLETE_COMPONENT_WALLETS',windows=windows,
    source_sha256=sha(__file__),config_sha256=sha(a.config),elapsed_seconds=time.monotonic()-began,
    new_market_replays=0,scope='Paired full wallets, actual risk and descriptive concentration; no direct attribution of independent leg PnL, matched-risk alpha, joined capital history or independent evidence certification'),f,indent=2)
print(json.dumps(dict(status='PASS_PAIRED_COMPLETE_COMPONENT_WALLETS',windows=[dict(window=x['window'],delta=[v['blend_minus_half_net_USDT'] for v in x['cases']]) for x in windows])))
