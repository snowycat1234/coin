"""Reproduce five repaired findings against the preserved pre-review source."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'coin_bot_native_adapter_synthetic_20261014'
ARCHIVE = CANDIDATE / 'preliminary/PRE_REVIEW_NATIVE_ADAPTER.py'
EXPECTED = '5c1e1dfc66f05b3deab88856065a7e017a3d273bb5b6d63a8e75c1cf93d7585a'
assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == EXPECTED
sys.path.insert(0, str(CANDIDATE))
spec = importlib.util.spec_from_file_location('independent_archived_grid_adapter', ARCHIVE)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
from generated_fixtures import make, finish


def sim(weights, name='RANGE', prices=None, quote=None, cls=None):
    window, _, closes, _, _ = make(name)
    if prices is not None:
        for key in ('open', 'close', 'mark'):
            window['market'][old.BTC][key] = np.asarray(prices, dtype=float).copy()
    if quote is not None:
        for symbol in old.S:
            window['market'][symbol]['quote_volume'][:] = quote
    def factory(daily, clocks, mode):
        return old.PORT.native.pl.DataFrame([dict(available_us=int(clock), symbol=s,
                   target_weight=float(weights[j])) for clock in clocks for j, s in enumerate(old.S)]), \
               dict(source='INDEPENDENT_FIXED_GENERATED_PRE_FIX_REPRODUCTION')
    return (cls or old.GridNativeAdapter)(window, 'LONG_SHORT', old.PORT.native.COSTS[0],
              old.PORT.native.UNITS[0], target_factory=factory, account_factory=old.ACCOUNT,
              arm='GRID', daily_closes=closes,
              covariance={int(clock): np.eye(5) * .001 for clock in range(window['start'], window['end'], old.DAY)})


def main():
    findings = []
    neutral = finish(sim([.2, 0, 0, 0, -.2]))
    grid_legs = sum(a['owner'] == 'GRID' for a in neutral.allocations)
    assert grid_legs > 0
    findings.append(dict(id='F1', issue='Missing original-target absolute-net/gross/asset bounds',
                         observed_GRID_fill_legs=grid_legs, original_target_abs_net=0))
    cash = sim([.2, .05, 0, 0, -.1])
    cash.arm = 'CASH'
    target = dict.fromkeys(old.S, old.ZERO)
    target[old.BTC] = old.D('19.8')
    kinds = dict.fromkeys(old.S, 'DAILY_TARGET')
    kinds[old.S[-1]] = 'POOL_EXIT'
    cash.schedule(target, cash.start, kinds)
    assert cash.pending[old.BTC]['target'] == old.D('19.8')
    findings.append(dict(id='F2', issue='Unrelated symbol exit bypasses fixed CASH replacement',
                         observed_BTC_target=str(cash.pending[old.BTC]['target']), expected_BTC_target='17.82'))
    stale = []
    class Spy(old.GridNativeAdapter):
        def risk_schedule(self, stamp):
            super().risk_schedule(stamp)
            pending = self.pending.get(old.BTC)
            if self.breaches and pending and pending['kind'] == 'DAILY_TARGET' and pending['target'] > self.account.positions[old.BTC].quantity:
                stale.append(dict(event_us=stamp, stale_target=str(pending['target']),
                                  actual_paid_quantity=str(self.account.positions[old.BTC].quantity)))
    gap = np.r_[np.full(30, 100.), np.full(1410, 200.)]
    finish(sim([.29, 0, 0, 0, -.1], prices=gap, quote=5_000_000., cls=Spy))
    assert stale
    findings.append(dict(id='F3', issue='Hard-risk settlement schedules obsolete pre-breach base',
                         witness=stale[0], native_finance_blocks_increase=True))
    prices = np.full(8 * 1440, 111.)
    prices[:20] = 100.
    prices[20:35] = 105.
    prices[35:50] = 110.
    prices[7 * 1440 - 1:] = 100.
    weekly = sim([.2, 0, 0, 0, 0], name='WEEK_RESET', prices=prices, quote=5_000_000.)
    weekly.window['events'] = []
    finish(weekly)
    later = [e for e in weekly.policy_events if e['kind'] == 'GRID_NATIVE_BOUND' and e['event_us'] >= weekly.start + 7 * old.DAY]
    expiries = [e for e in weekly.policy_events if e.get('reason') == 'FIXED_WEEK_END']
    assert not later and len(expiries) > 1
    findings.append(dict(id='F4', issue='Paid-flat expired grid blocks successor and repeats expiry',
                         successor_native_bindings=len(later), repeated_week_expiries=len(expiries)))
    try:
        finish(sim([.0492, 0, 0, 0, 0], quote=5_000_000.))
    except ValueError as error:
        assert str(error) == 'opening minimum notional cannot be met'
        findings.append(dict(id='F5', issue='Actual .99 collar minimum-notional failure escapes fallback',
                             preliminary_budget='49.2', actual_budget='48.708', error=str(error)))
    else:
        raise AssertionError('Archived minimum boundary no longer reproduces')
    result = dict(schema='INDEPENDENT_ARCHIVED_NATIVE_GRID_FINDINGS_V1', archive_source_SHA256=EXPECTED,
                  reproduced_findings=findings, status='ALL_FIVE_REPRODUCED_AND_FIXED_IN_FINAL_FREEZE',
                  historical_GO=False, market_arrays_loaded=0, producer_files_edited=False)
    (HERE / 'PRE_FIX_FINDINGS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], reproduced=len(findings))))


if __name__ == '__main__':
    main()
