"""Small hand-arithmetic checks; no historical market/account replay."""
import argparse
from decimal import Decimal as D
import hashlib
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
SOURCE = args.source_root.resolve()
expected_sources = {
    'src/quant/perpetual_account.py': 'ffa57a4c3c3b031945fcbc5db429d8b5e6ef06e880a8a577265836602ad55110',
    'src/quant/bybit_isolated_account.py': 'd82cfca41a76f12aea60ea2608a5c5d26670d7c55394cb07619b69fdffd2619a',
    'scripts/investment/resumable_perpetual.py': '318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585',
}
for name, expected in expected_sources.items():
    assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected
os.environ['QUANT_ROOT'] = str(SOURCE)
sys.path[:0] = [str(SOURCE / 'src'), str(SOURCE)]
import numpy as np
import polars as pl
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment.resumable_perpetual import NativeDailySimulator

MINUTE = 60_000_000
START = 1_704_067_200_000_000
SYMS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
COST = dict(id='BASE27', half_spread_bps=4, slippage_bps=4, roundtrip_bps=27)
rows = []
for direction in (D(1), D(-1)):
    for exit_mid in (D(90), D(110)):
        for rate in (D('.001'), D('-.001')):
            a = BybitIsolatedAccount(symbols=('BTCUSDT',))
            a.update_marks(START, {'BTCUSDT': dict(price='100', close_us=START, available_us=START)})
            side = 'BUY' if direction > 0 else 'SELL'
            open_fill = D(100) * (1 + direction * D('.0008'))
            close_fill = exit_mid * (1 - direction * D('.0008'))
            opened = a.execute_fill('BTCUSDT', side, '1', START + MINUTE + 1, START, 'open',
                execution_mid_price='100', quote_available_us=START + MINUTE)
            assert opened['status'] == 'FILLED'
            # One positive funding rate debits LONG and credits SHORT; mark100.
            funding = a.apply_funding('BTCUSDT', 'fund', START + 2 * MINUTE, str(rate), START + 2 * MINUTE)
            expected_fund = -direction * D(100) * rate
            assert D(funding['decimal_strings']['signed_funding_USDT']) == expected_fund
            a.update_marks(START + 3 * MINUTE, {'BTCUSDT': dict(price=str(exit_mid), close_us=START + 3 * MINUTE, available_us=START + 3 * MINUTE)})
            closed = a.execute_fill('BTCUSDT', 'SELL' if direction > 0 else 'BUY', '1', START + 3 * MINUTE + 1, START + 2 * MINUTE, 'close',
                execution_mid_price=str(exit_mid), quote_available_us=START + 3 * MINUTE, reduce_only=True)
            assert closed['status'] == 'FILLED'
            expected_fee = (open_fill + close_fill) * D('.00055')
            expected_execution = D(100) * D('.0008') + exit_mid * D('.0008')
            expected_nav = D(10000) + direction * (exit_mid - D(100)) - expected_fee - expected_execution + expected_fund
            assert abs(a.nav() - expected_nav) < D('1e-30'), (a.nav(), expected_nav)
            assert a.unpaid_liability == 0 and a.positions['BTCUSDT'].quantity == 0
            rows.append(dict(direction=int(direction), exit_mid=float(exit_mid), funding_rate=float(rate), expected_NAV=str(expected_nav), observed_NAV=str(a.nav())))

# Twelve minutes, exactly 0.1% participation in the preceding minute's quote
# volume. Minute1 can fill despite its own volume=0; minute2 cannot fill.
n = 12
quote = np.full(n, 100_000.)
quote[1] = 0.
market = {s: dict(open=np.full(n, 100.), close=np.full(n, 100.), mark=np.full(n, 100.), quote_volume=quote.copy()) for s in SYMS}
window = dict(symbols=SYMS, start=START, end=START+n*MINUTE, market=market,
              daily=pl.DataFrame([dict(symbol=s, close_us=START, close=100.) for s in SYMS]), events=[])
sim = NativeDailySimulator(window, 'LONG_SHORT', COST, dict(id='RAW_AS_FRACTION', scale=1.), account_factory=BybitIsolatedAccount, persist_cash_close=True)
w = dict.fromkeys(SYMS, 0.)
w.update(BTCUSDT=.1, ETHUSDT=-.1)
assert sim.advance_day(w)['completed']
fills = sim.account.trades
assert len(fills) == 16 and all(r['quantity'] == 1 for r in fills)
assert not any(r['event_us'] == START + 2*MINUTE + 1 for r in fills)
assert any(r['event_us'] == START + MINUTE + 1 for r in fills)
assert min(r['event_us'] for r in fills) == START + MINUTE + 1
assert all(sim.account.positions[s].quantity == 0 for s in SYMS)
assert sim.account.nav() == D('9997.840000')
assert sim.account.fees == D('.880000') and sim.account.execution_cost == D('1.28')
assert all(r['signal_us'] == START + 6*MINUTE for r in fills if r['leg'] == 'CLOSE')

report = dict(status='PASS_INDEPENDENT_SIGN_COST_FUNDING_LATENCY_CAPACITY_AND_PAID_TERMINAL_CHECKS',
    source_commit='55ac3d2ee730b1cd1381696330a6abaf1925eb92',
    source_sha256={str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'src/quant/perpetual_account.py', SOURCE/'src/quant/bybit_isolated_account.py', SOURCE/'scripts/investment/resumable_perpetual.py']},
    single_symbol_cases=rows,
    scheduler=dict(minutes=n, ordinary_fill_legs=len(fills), NAV=str(sim.account.nav()), fees=str(sim.account.fees), execution_cost=str(sim.account.execution_cost), terminal_flat=True, future_quote_not_used=True),
    scope='eight one-contract cases plus twelve synthetic minutes; no historical source/data, training, backtest or trades')
print(json.dumps(report, indent=2))
args.output.write_text(json.dumps(report, indent=2)+'\n')
