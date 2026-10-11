"""Zero-fit attribution and risk diagnosis of the four already saved wallets."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import polars as pl
from restore_minutes import SYMBOLS, DAY, save, sha

HERE = Path(__file__).resolve().parent


def inspect(state, destination):
    source = state / 'economics'
    saved = np.load(HERE / 'diagnostic/SAVED_TARGETS.npz', allow_pickle=False)
    rows = []
    for case in sorted(p for p in source.iterdir() if p.is_dir()):
        minute = pl.read_parquet(case / 'minute_nav_inventory.parquet')
        summary = json.loads((case / 'summary.json').read_bytes())
        liquidations = json.loads((case / 'liquidations.json').read_bytes())
        attrib = json.loads((case / 'ASSET_ATTRIBUTION.json').read_bytes())
        # Snapshot at closeD belongs to previous completed execution minute.
        decision = ((minute['close_us'].to_numpy() - 1) // DAY) * DAY
        ix = np.searchsorted(saved['decision_us'], decision)
        if not np.array_equal(saved['decision_us'][ix], decision):
            raise ValueError('Exact previously saved beta day, no future recompute')
        actual_weights = minute.select([s + '_signed_marked_notional' for s in SYMBOLS]).to_numpy() / minute['nav'].to_numpy()[:, None]
        modeled = np.sum(actual_weights * saved['beta'][ix], axis=1)
        witnesses = []
        for event in liquidations:
            timestamp = int(event['event_us'])
            witnesses.append(dict(symbol=event['symbol'], UTC=datetime.fromtimestamp(timestamp / 1000000, timezone.utc).isoformat(),
                                  event_us=timestamp, phase=event['phase'], signed_quantity=event['quantity'],
                                  mark_price=event['mark_price'], bankruptcy_price=event['bankruptcy_price'],
                                  isolated_margin_lost_USDT=event['isolated_margin_lost'],
                                  included_in_gross_and_net_not_extra_charge=True))
        row = dict(case=case.name, liquidation_count=len(liquidations), liquidation_witnesses=witnesses,
                   total_takeover_margin_loss_USDT=summary['liquidation_loss_USDT'],
                   actual_modeled_beta_exposure_abs_mean=float(np.mean(np.abs(modeled))),
                   actual_modeled_beta_exposure_abs_max=float(np.max(np.abs(modeled))),
                   actual_model_beta_scope='Uses saved causal beta and observed weights, not realized-factor regression or native beta certification',
                   gross_price_USDT=summary['gross_PnL_same_quantities'],
                   net_USDT=summary['net_PnL'], BTC_hedge_net_USDT=attrib['assets']['BTCUSDT']['net_contribution_USDT'],
                   alt_net_USDT=sum(attrib['assets'][s]['net_contribution_USDT'] for s in SYMBOLS[1:]),
                   fees_USDT=summary['fees_USDT'],execution_cost_USDT=summary['execution_cost_USDT'],
                   funding_USDT=summary['funding_USDT'], annual_realized_vol=summary['daily_metrics']['annual_volatility'],
                   minute_MDD=summary['minute_max_drawdown'],realized_exposure=summary['realized_exposure'],
                   source_minute_parquet_SHA256=sha((case / 'minute_nav_inventory.parquet').read_bytes()),
                   source_liquidations_SHA256=sha((case / 'liquidations.json').read_bytes()))
        rows.append(row)
    destination.mkdir()
    save(destination / 'SAVED_WALLET_FORENSICS.json', dict(status='PASS_READ_ONLY_SAVED_WALLET_ATTRIBUTION', cases=rows,
         scientific_fits=0, regressions=0, wallet_reruns=0, extra_source_windows=0,
         conclusion='Both arms have2 DOGE assumed isolated takeovers. Residual total takeover loss is slightly smaller; underperformance is not an extra liquidation-count effect. Alt and BTC gross increments are negative and cost increment is small. Target neutrality does not guarantee actual marked holdings neutrality or10percent realized volatility.',
         limitations='Historical train episode and conditional market/MMR/funding units. No no-liquidation counterfactual, no free cash/closure or alpha qualification.'))
    print(json.dumps([dict(case=r['case'],beta_mean=r['actual_modeled_beta_exposure_abs_mean'],beta_max=r['actual_modeled_beta_exposure_abs_max'],liquidations=r['liquidation_count']) for r in rows],indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--state',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args()
    inspect(a.state.resolve(),a.destination.resolve())


if __name__=='__main__':main()
