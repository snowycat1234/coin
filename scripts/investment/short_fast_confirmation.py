"""Closed four-hour public Donchian adapter; existing account owns execution."""
import json
from pathlib import Path
import numpy as np
import polars as pl
from scripts.investment.cta_classics import channel_kernel, DAY
from scripts.investment.public_sma_perpetual import symbol_order

FOUR_HOURS = DAY // 6
RULES = dict(interval_minutes=240, entry_period=20, exit_period=10,
    fast_signal='VIRTUAL_PRIOR20_BREAKOUT_PRIOR10_EXIT_NO_SAME_BAR_REENTRY',
    short_permission='DAILY_DC20_10_AND_DC55_20_SHORT_AND_FAST_DC20_10_SHORT',
    unknown='CASH_FOR_SHORT_NO_IMPUTATION', long_forecast='UNCHANGED',
    exit='COMPLETED_4H_CONFIRMATION_LOSS_PAID_DELAYED_PERSISTENT_REDUCE_ONLY',
    reentry='NEXT_DAILY_DECISION_IF_FAST_AND_SLOW_RECONFIRMED',
    sizing='MASK_BEFORE_EXISTING_DAILY_ORDERED_SIGNED_COVARIANCE',
    intraday='REDUCTIONS_ONLY_NO_4H_ALPHA_INCREASE',
    full_Turtle_or_paper_replication=False)


def aggregate_bars(manifest_path, symbols, start, end, progress=None):
    """Reduce already accepted minute files one asset/month at a time."""
    manifest = json.loads(Path(manifest_path).read_bytes())
    records = [r for r in manifest['market_records']
               if r['kind'] == 'klines' and r['symbol'] in symbols]
    result = []
    for i, r in enumerate(records):
        minute = pl.scan_parquet(r['normalized_path']).filter(
            (pl.col('open_us') >= start) & (pl.col('close_us') <= end)).sort('open_us').collect()
        if minute.is_empty(): continue
        stamps = minute['open_us'].to_numpy()
        assert np.all(np.diff(stamps) == 60_000_000)
        assert minute['available_us'].equals(minute['close_us'])
        bars = minute.with_columns((pl.col('open_us') // FOUR_HOURS * FOUR_HOURS).alias('bucket')).group_by('bucket', maintain_order=True).agg(
            pl.col('open').first(), pl.col('high').max(), pl.col('low').min(),
            pl.col('close').last(), pl.col('volume').sum(),
            pl.col('open_us').first().alias('first_us'), pl.col('close_us').last().alias('last_us'),
            pl.len().alias('minutes'))
        assert bars['minutes'].min() == bars['minutes'].max() == 240
        assert bars['bucket'].equals(bars['first_us'])
        assert (bars['bucket'] + FOUR_HOURS).equals(bars['last_us'])
        result.append(bars.select(pl.lit(r['symbol']).alias('symbol'),
            pl.col('bucket').alias('open_us'), pl.col('last_us').alias('close_us'),
            pl.col('last_us').alias('available_us'), 'open', 'high', 'low', 'close', 'volume'))
        if progress: progress.update('已有分钟数据聚合4小时确认', i+1, len(records), '资产月份')
    out = pl.concat(result).sort(['symbol', 'close_us'])
    assert out.height == len(symbols) * (end-start) // FOUR_HOURS
    return out


def signals(bars, symbols):
    kernel = channel_kernel(); rows = []
    for s in symbol_order(symbols):
        b = bars.filter(pl.col('symbol') == s).sort('close_us')
        stamps = b['close_us'].to_numpy()
        assert np.all(np.diff(stamps) == FOUR_HOURS) and np.all(stamps % FOUR_HOURS == 0)
        assert b['available_us'].equals(b['close_us'])
        assert (b['open_us'] + FOUR_HOURS).equals(b['close_us'])
        c = np.column_stack((b['open_us'].to_numpy()/1000,
                            b.select('open', 'close', 'high', 'low', 'volume').to_numpy()))
        assert np.isfinite(c).all() and np.all(c[:, 1:5] > 0)
        state = 0
        for j, t in enumerate(stamps):
            if j >= 20:
                entry = kernel(c[:j], period=20); exit_ = kernel(c[:j], period=10)
                close = c[j, 2]
                if state == 1 and close < exit_.lowerband or state == -1 and close > exit_.upperband:
                    state = 0
                elif state == 0:
                    state = 1 if close > entry.upperband else (-1 if close < entry.lowerband else 0)
            rows.append(dict(symbol=s, close_us=int(t), available_us=int(t),
                             fast_state=state if j >= 20 else None))
    return pl.DataFrame(rows, infer_schema_length=None).sort(['close_us', 'symbol'])


def verify_signals(frame, bars, symbols):
    """Independent scalar extremes, not a second indicator implementation."""
    observed = {(r['close_us'], r['symbol']): r['fast_state'] for r in frame.iter_rows(named=True)}
    for s in symbols:
        b = list(bars.filter(pl.col('symbol') == s).sort('close_us').iter_rows(named=True)); state = 0
        for j, r in enumerate(b):
            if j >= 20:
                if state == 1 and r['close'] < min(v['low'] for v in b[j-10:j]) or state == -1 and r['close'] > max(v['high'] for v in b[j-10:j]): state = 0
                elif state == 0:
                    state = 1 if r['close'] > max(v['high'] for v in b[j-20:j]) else (-1 if r['close'] < min(v['low'] for v in b[j-20:j]) else 0)
            assert observed[(r['close_us'], s)] == (state if j >= 20 else None)
    return dict(status='PASS_INDEPENDENT_SCALAR_FAST_SIGNALS', rows=frame.height)


def mask_daily(slow, fast):
    lookup = {(r['available_us'], r['symbol']): r['fast_state'] for r in fast.iter_rows(named=True)}
    values = []
    for r in slow.iter_rows(named=True):
        v = r['DC_CONFIRMED_SHORT']; f = lookup.get((r['close_us'], r['symbol']))
        values.append(0. if v is not None and v < 0 and f != -1 else v)
    return slow.with_columns(pl.Series('DC_CONFIRMED_SHORT', values, dtype=pl.Float64))


class FastShortConfirmation:
    rules = RULES

    def __init__(self, fast, slow):
        self.fast = fast; self.slow = slow

    def prepare(self, bars, symbols, start, end):
        self.symbols = symbol_order(symbols); self.journal = []; self.blocks = set()
        self.fast_lookup = {(r['available_us'], r['symbol']): r['fast_state'] for r in self.fast.iter_rows(named=True)}
        self.slow_lookup = {(r['available_us'], r['symbol']): r['DC_CONFIRMED_SHORT'] for r in self.slow.iter_rows(named=True)}
        self.current_day = start
        for s in symbols:
            assert (start, s) in self.slow_lookup
        self._update(start)

    def _update(self, t):
        fast_t = t // FOUR_HOURS * FOUR_HOURS
        for s in self.symbols:
            slow = self.slow_lookup[(self.current_day, s)]
            blocked = slow is not None and slow < 0 and self.fast_lookup.get((fast_t, s)) != -1
            old = s in self.blocks
            if blocked: self.blocks.add(s)
            else: self.blocks.discard(s)
            if blocked != old:
                self.journal.append(dict(kind='SHORT_PERMISSION_CHANGE', symbol=s, event_us=int(t),
                    fast_available_us=int(fast_t), fast_state=self.fast_lookup.get((fast_t,s)),
                    slow_available_us=int(self.current_day), slow_forecast=slow, short_blocked=blocked))

    def blocked(self, s): return s in self.blocks

    def on_decision(self, t, positions):
        self.current_day = t; self._update(t)

    def on_fills(self, trades, order_kind):
        for r in trades:
            if order_kind == 'PROTECTIVE_STOP':
                self.journal.append(dict(kind='FAST_CONFIRMATION_EXIT_FILL', symbol=r['symbol'],
                    event_us=r['event_us'], signal_us=r['signal_us'], quantity_before=r['quantity_before'],
                    quantity_after=r['quantity_after'], quantity=r['quantity'], fill_price=r['fill_price'],
                    fees=r['fee_USDT_mid'], execution_cost=r['execution_cost']))

    def observe(self, close, market, positions):
        if close % FOUR_HOURS or close // DAY * DAY != self.current_day: return []
        self._update(close)
        stopped = [s for s in self.symbols if self.blocked(s) and positions[s].quantity < 0]
        for s in stopped:
            self.journal.append(dict(kind='OBSERVED_FAST_CONFIRMATION_LOSS', symbol=s, event_us=int(close),
                fast_state=self.fast_lookup.get((close,s)), actual_quantity=str(positions[s].quantity)))
        return stopped
