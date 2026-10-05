"""Small shared XGBoost direction adapter, with one common causal calendar.

No account implementation, per-symbol fits, fitted normalizer or search here.
Daily features are observed at exclusive completed-day close; the 5d label is
a trade-open proxy. Funding is economic sensitivity, not an unconfirmed input.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from scripts.investment.public_sma_perpetual import signed_risk_weights

DAY = 86_400_000_000
CLASSES = ('SHORT', 'CASH', 'LONG')
MODEL = dict(n_estimators=120, max_depth=3, learning_rate=.05,
    min_child_weight=20, subsample=1., colsample_bytree=1., reg_lambda=10.,
    objective='multi:softprob', num_class=3, tree_method='hist', device='cpu',
    n_jobs=2, random_state=20261005, eval_metric='mlogloss')
BASE_FEATURES = ['return_1d', 'return_5d', 'return_20d', 'vol_30d',
    'atr14_simple_relative', 'ma20_distance', 'ma200_distance', 'trend_20_200',
    'volume_change', 'volume_anomaly', 'BTC_return_1d', 'BTC_return_20d',
    'ETH_return_1d', 'ETH_return_20d', 'market_breadth']

def feature_table(bars, symbols):
    """No future expressions or learned transforms in this path."""
    if set(bars['symbol'].unique()) != set(symbols):
        raise ValueError('Feature universe must match ordered account symbols')
    pieces = []
    for symbol in symbols:
        b = bars.filter(pl.col('symbol') == symbol).sort('close_us')
        if not np.all(np.diff(b['close_us'].to_numpy()) == DAY) or not np.all(
                b['available_us'].to_numpy() == b['close_us'].to_numpy()):
            raise ValueError('Complete causal daily bars; no gap imputation')
        b = b.with_columns(
            (pl.col('close')/pl.col('close').shift(1)-1).alias('return_1d'),
            (pl.col('close')/pl.col('close').shift(5)-1).alias('return_5d'),
            (pl.col('close')/pl.col('close').shift(20)-1).alias('return_20d'),
            pl.col('close').rolling_mean(20).alias('ma20'),
            pl.col('close').rolling_mean(200).alias('ma200'),
            pl.max_horizontal(pl.col('high')-pl.col('low'),
                (pl.col('high')-pl.col('close').shift(1)).abs(),
                (pl.col('low')-pl.col('close').shift(1)).abs()).alias('true_range'),
            (pl.col('volume')/pl.col('volume').shift(1).clip(1e-12, None)-1).alias('volume_change'),
            (pl.col('volume')/pl.col('volume').rolling_mean(20).clip(1e-12, None)-1).alias('volume_anomaly'))
        b = b.with_columns(pl.col('return_1d').rolling_std(30).alias('vol_30d'),
            (pl.col('true_range').rolling_mean(14)/pl.col('close')).alias('atr14_simple_relative'),
            (pl.col('close')/pl.col('ma20')-1).alias('ma20_distance'),
            (pl.col('close')/pl.col('ma200')-1).alias('ma200_distance'),
            (pl.col('ma20')/pl.col('ma200')-1).alias('trend_20_200'))
        pieces.append(b)
    frame = pl.concat(pieces)
    breadth = frame.group_by('close_us').agg((pl.col('return_20d') > 0).mean().alias('market_breadth'))
    frame = frame.join(breadth, on='close_us', how='left', validate='m:1')
    for symbol, prefix in [('BTCUSDT', 'BTC'), ('ETHUSDT', 'ETH')]:
        cross = frame.filter(pl.col('symbol') == symbol).select('close_us',
            pl.col('return_1d').alias(prefix+'_return_1d'),
            pl.col('return_20d').alias(prefix+'_return_20d'))
        frame = frame.join(cross, on='close_us', how='left', validate='m:1')
    for symbol in symbols:
        frame = frame.with_columns((pl.col('symbol') == symbol).cast(pl.Float32).alias('symbol_'+symbol))
    features = [*BASE_FEATURES, *['symbol_'+s for s in symbols]]
    return frame.sort(['close_us', 'symbol']).with_columns(
        [pl.col(f).cast(pl.Float32) for f in features]), features

def label_table(features, bars, *, horizon_days=5, roundtrip_bps=27., threshold_bps=10.):
    """Raw signed open-to-open return vs cost+edge band, never double cost.

    Entry is the trade open at decision time, not executable certification.
    Actual account latency, changing positions, funding and forced exits are
    accounted separately. Last horizon is missing, not fabricated CASH.
    """
    forward = bars.select('symbol', pl.col('open_us').alias('close_us'),
        pl.col('open').alias('entry_proxy'))
    exits = bars.select('symbol', (pl.col('open_us')-horizon_days*DAY).alias('close_us'),
        pl.col('open').alias('exit_proxy'))
    labeled = features.join(forward, on=['symbol', 'close_us'], how='left', validate='1:1').join(
        exits, on=['symbol', 'close_us'], how='left', validate='1:1').with_columns(
        (pl.col('exit_proxy')/pl.col('entry_proxy')-1).alias('future_price_return'),
        (pl.col('close_us')+horizon_days*DAY+1).alias('label_available_us'))
    band = (roundtrip_bps+threshold_bps)/10000
    return labeled.with_columns(pl.when(pl.col('future_price_return').is_null()).then(None)
        .when(pl.col('future_price_return') > band).then(2)
        .when(pl.col('future_price_return') < -band).then(0).otherwise(1).cast(pl.Int32).alias('label'))

def targets(predictions, bars, decisions, mode, symbols, *, regimes=None):
    if mode not in ('LONG_SHORT', 'LONG_ONLY', 'SHORT_ONLY', 'CASH'):
        raise ValueError('Explicit direction policy')
    lookup = {(r['close_us'], r['symbol']): r['prediction']-1
              for r in predictions.iter_rows(named=True)}
    closes = {s:bars.filter(pl.col('symbol') == s).sort('close_us') for s in symbols}
    rows, risks = [], []
    for t in decisions:
        raw, histories = [], []
        for s in symbols:
            direction = lookup[(int(t), s)]
            if regimes is not None:
                from scripts.investment.market_regime import allowed
                if not allowed(regimes[int(t)],direction): direction=0
            if mode == 'CASH' or mode == 'LONG_ONLY' and direction < 0 or mode == 'SHORT_ONLY' and direction > 0:
                direction = 0
            b = closes[s].filter((pl.col('close_us') <= t) & (pl.col('available_us') <= t)).tail(31)
            if b.height != 31 or not np.all(np.diff(b['close_us'].to_numpy()) == DAY):
                raise ValueError('Ordered covariance requires thirty complete past daily returns')
            v = b['close'].to_numpy()
            histories.append(v[1:]/v[:-1]-1)
            raw.append(direction*.6/len(symbols))
        weights, risk = signed_risk_weights(raw, np.column_stack(histories))
        risks.append(dict(available_us=int(t), **risk))
        for i, s in enumerate(symbols):
            row=dict(available_us=int(t), symbol=s, raw_signed_target=raw[i],
                target_weight=float(weights[i]), mode=mode)
            if regimes is not None: row['regime']=regimes[int(t)]
            rows.append(row)
    return pl.DataFrame(rows), dict(strategy_id='COIN_SHARED_XGB_3CLASS_5D_1D',
        classes=list(CLASSES), mode=mode, risk=risks, symbols=list(symbols),
        probability_rule='ARGMAX_NO_POST_SCORE_THRESHOLD_SEARCH',
        funding_rates_used_for_signal=False)
