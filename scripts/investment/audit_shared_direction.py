"""Independent signed cash-flow/marked inventory identity, not a simulator.

Synthetic inventory cash is only a NAV bridge: a short sale never adds
investable wallet cash. Producer free cash and isolated margin are separately
reconciled to the reported futures wallet. No producer finance is imported.
"""
from decimal import Decimal, localcontext
import json
from pathlib import Path
import numpy as np
import polars as pl

def verify(directory, symbols, unit_scale):
    p = Path(directory)
    minute = pl.read_parquet(p/'minute_nav_inventory.parquet')
    summary = json.loads((p/'summary.json').read_bytes())
    trades = json.loads((p/'trades.json').read_bytes())
    funds = json.loads((p/'funding.json').read_bytes())
    times = minute['close_us'].to_numpy()
    stream = sorted([(r['event_us'], 1, i, r) for i, r in enumerate(trades)]+
                    [(r['event_us'], 0, i, r) for i, r in enumerate(funds)], key=lambda x:x[:3])
    D = Decimal
    q = {s:D(0) for s in symbols}
    cash = D(10000)
    fee = execution = funding = realized = D(0)
    entry = {s:D(0) for s in symbols}
    stamps, states = [int(times[0])-60_000_001], [[10000., 0., 0., 0., 10000., *[0. for s in symbols]]]
    long_cash = short_cash = D(0)
    short_open = 0
    direction_states = [[0., 0.]]
    with localcontext() as ctx:
        ctx.prec = 50
        for t, kind, _, r in stream:
            s = r['symbol']
            if s not in q:
                raise ValueError('Unknown asset in shared journal')
            if kind:
                exact = r['decimal_strings']
                delta = D(exact['position_delta'])
                if abs(float(q[s])-r['quantity_before']) > 1e-10:
                    raise ValueError('Signed quantity continuity')
                side = q[s] if r['leg'] == 'CLOSE' else delta
                fill = D(exact['fill_price'])
                if r['leg'] == 'CLOSE':
                    if q[s]*delta >= 0 or abs(delta) > abs(q[s]):
                        raise ValueError('Reduce-only signed leg')
                    realized += abs(delta)*(1 if q[s]>0 else -1)*(fill-entry[s])
                else:
                    if q[s] and q[s]*delta <= 0:
                        raise ValueError('Reversal must close before opening')
                    entry[s] = (abs(q[s])*entry[s]+abs(delta)*fill)/(abs(q[s])+abs(delta))
                amount = -delta*D(exact['fill_price'])-D(exact['fee_amount'])
                cash += amount
                if side > 0: long_cash += amount
                else: short_cash += amount
                if r['leg'] == 'OPEN' and delta < 0: short_open += 1
                q[s] += delta
                if not q[s]: entry[s] = D(0)
                fee += D(exact['fee_amount'])
                execution += D(exact['execution_cost'])
                if abs(float(q[s])-r['quantity_after']) > 1e-10:
                    raise ValueError('Signed fill result')
                if r['leg'] == 'CLOSE' and side*q[s] < 0:
                    raise ValueError('Closing leg cannot reverse through zero')
            else:
                if abs(float(q[s])-r['quantity']) > 1e-10:
                    raise ValueError('Funding ownership')
                if q[s]:
                    j = int(np.searchsorted(times, t, side='left'))-1
                    if j < 0 or r['mark_close_us'] != int(times[j]):
                        raise ValueError('Funding requires strictly past mark')
                    mark = float(minute[s+'_signed_marked_notional'][j])/float(minute[s+'_quantity'][j])
                    if abs(mark-r['mark_price']) > 1e-7:
                        raise ValueError('Funding mark identity')
                    amount = -q[s]*D(str(r['mark_price']))*D(str(r['raw_rate']))*D(str(unit_scale))
                else: amount = D(0)
                if abs(float(amount)-r['signed_funding_USDT']) > 1e-7:
                    raise ValueError('Signed conditional funding amount')
                cash += amount; funding += amount
                if q[s] > 0: long_cash += amount
                elif q[s] < 0: short_cash += amount
            stamps.append(t)
            states.append([float(cash), float(fee), float(execution), float(funding),
                float(D(10000)+realized-fee+funding), *[float(q[s]) for s in symbols]])
            direction_states.append([float(long_cash), float(short_cash)])
    ix = np.searchsorted(np.asarray(stamps), times, side='right')-1
    reference = np.asarray(states)[ix]
    dirs = np.asarray(direction_states)[ix]
    actual_q = minute.select([s+'_quantity' for s in symbols]).to_numpy()
    notionals = minute.select([s+'_signed_marked_notional' for s in symbols]).to_numpy()
    nav = reference[:, 0]+notionals.sum(axis=1)
    max_error = float(np.max(np.abs(nav-minute['nav'].to_numpy())))
    if max_error > 1e-7 or np.max(np.abs(reference[:, 5:]-actual_q)) > 1e-8:
        raise ValueError('Independent full minute NAV/signed inventory mismatch')
    for col, i in [('cumulative_fees', 1), ('cumulative_execution_costs', 2), ('cumulative_funding', 3)]:
        if np.max(np.abs(reference[:, i]-minute[col].to_numpy())) > 1e-7:
            raise ValueError('Independent cumulative cost/funding mismatch')
    wallet_error = float(np.max(np.abs(reference[:,4]-(minute['free_cash']+minute['isolated_balance']).to_numpy())))
    if wallet_error > 1e-7:
        raise ValueError('Independent realized wallet/free plus isolated collateral identity')
    if bool(summary['terminal_cash_realized']) != (not any(q.values())):
        raise ValueError('True terminal liquidation scope')
    if abs(nav[-1]-summary['NAV']) > 1e-7 or abs(nav[-1]-10000-summary['net_PnL']) > 1e-7:
        raise ValueError('Full capital/terminal marked NAV identity')
    net_dir = dirs+np.column_stack((np.maximum(notionals, 0).sum(axis=1), np.minimum(notionals, 0).sum(axis=1)))
    endpoints = np.flatnonzero(times % 86_400_000_000 == 0)
    daily_direction = np.diff(np.vstack(([0., 0.], net_dir[endpoints])), axis=0)
    for i, label in enumerate(('LONG', 'SHORT')):
        if abs(float(net_dir[-1, i])-summary['long_short_marked_contribution'][label]['net_contribution']) > 1e-7:
            raise ValueError('Independent long/short terminal attribution')
    return dict(status='PASS_INDEPENDENT_SIGNED_JOURNAL_MINUTE_MARKED_NAV_FUNDING_AND_WALLET_IDENTITY',
        minutes=minute.height, maximum_NAV_error_USDT=max_error, maximum_wallet_error_USDT=wallet_error,
        terminal_cash_realized=summary['terminal_cash_realized'],
        liquidated_return_scope='EVALUABLE' if summary['terminal_cash_realized'] else 'NOT_EVALUABLE_RETAIN_REAL_RESIDUAL',
        actual_short_open_legs=short_open,
        daily_direction_contributions=[dict(day_end_us=int(times[k]), LONG=float(v[0]), SHORT=float(v[1]), CASH=0.)
            for k, v in zip(endpoints, daily_direction, strict=True)],
        scope='RECORDED_FILLS_ACCOUNTING_NOT_INDEPENDENT_ORDER_SIZING_OR_NATIVE_RULES')
