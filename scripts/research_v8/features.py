"""Fixed V8 endpoint summary over the unchanged shared 68-feature adapter.

No reads, fitting, feature selection or label-based eligibility occur here.
Each call uses one closed, causally available hour; never a sample-window cube.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from quant.research_fast.dataset import (
    BAR_US, FEATURE_COLUMNS, FEATURES_PER_STREAM, LOCKED, PAST_BARS, START,
    STREAMS, day_us, feature_matrix, tabular_view,
)

WINDOWS = (12, 60, 180, 720)  # 1, 5, 15, 60 minutes of closed 5s bars.
WINDOW_FIELDS = (
    'lag_return', 'lag_flow', 'lag_log_volume', 'ewma_return', 'ewma_flow',
    'flow_slope_per_minute', 'log_volume_slope_per_minute',
    'flow_q10', 'flow_q50', 'flow_q90', 'burst_log_volume',
    'return_rms', 'flow_volatility_interaction', 'flow_volume_interaction',
    'signed_impact_decay', 'observed_return_fraction',
)
BASE_NAMES = tuple(f'{stat}__{name}' for stat in ('last', 'mean', 'popstd')
                   for name in FEATURE_COLUMNS)
ADDED_NAMES = tuple(f'{stream}__{field}__{w*5}s'
                    for stream in STREAMS for w in WINDOWS for field in WINDOW_FIELDS)
CROSS_NAMES = tuple(f'{symbol}__spot_perp_log_price_divergence' for symbol in ('BTCUSDT', 'ETHUSDT'))
CROSS_NAMES += tuple(f'{symbol}__spot_perp_flow_divergence__{w*5}s'
                     for symbol in ('BTCUSDT', 'ETHUSDT') for w in WINDOWS)
CROSS_NAMES += tuple(f'{venue}__BTC_ETH_flow_difference__{w*5}s'
                     for venue in ('spot', 'perp') for w in WINDOWS)
NAMES = BASE_NAMES + ADDED_NAMES + CROSS_NAMES


@dataclass(frozen=True)
class EndpointFeatures:
    decision_us: int
    available_us: int
    names: tuple[str, ...]
    values: np.ndarray


def _ewma(values):
    # Official Polars EWMA, fixed span equal to this registered window.
    return float(pl.Series(values).ewm_mean(span=len(values), adjust=False,
                                          min_samples=len(values))[-1])


def endpoint_features(joint: pl.DataFrame, decision_us: int) -> EndpointFeatures:
    decision_us = int(decision_us)
    if not day_us(START) + 720 * BAR_US <= decision_us < day_us(LOCKED):
        raise ValueError('One causal development hour required; locked access forbidden')
    if decision_us % 60_000_000:
        raise ValueError('Fixed minute decision frequency required')
    expected = np.arange(decision_us - 720 * BAR_US, decision_us, BAR_US, dtype=np.int64)
    # Filter first: future-row perturbations, even future quality failures, cannot
    # affect this input. The existing source reader owns file-level access guards.
    past = joint.filter(pl.col('timestamp').is_between(int(expected[0]), decision_us, closed='left'))
    if len(past) != 720 or not np.array_equal(past['timestamp'].to_numpy(), expected):
        raise ValueError('Exact ordered past720 required; missing/duplicate bars abstain')
    availability = []
    closes = {}
    for stream in STREAMS:
        stamps = past[f'{stream}__available_us'].to_numpy()
        if not np.isfinite(stamps).all() or np.any(stamps < expected + BAR_US) or np.any(stamps > decision_us):
            raise ValueError('Unavailable or future inputs must abstain')
        quality = past[f'{stream}__quality']
        if not quality.is_not_null().all() or not quality.eq(0).all():
            raise ValueError('Invalid past quality must abstain')
        availability.append(int(stamps.max()))
        # Undefined return/interarrival are handled by the original explicit
        # has_* masks. Cross-price features require this exact last closed price.
        close = past[f'{stream}__close'][-1]
        if close is None or not np.isfinite(close) or close <= 0:
            raise ValueError('Missing current cross price must abstain; no price imputation')
        closes[stream] = float(close)
        for field in ('quote_notional', 'base_volume', 'trade_count', 'agg_count'):
            vals = past[f'{stream}__{field}'].to_numpy()
            if not np.isfinite(vals).all() or np.any(vals < 0):
                raise ValueError('Missing or negative past activity must abstain')
    matrix = feature_matrix(past)  # Exactly the frozen original definitions/masks.
    result = list(tabular_view(matrix[-PAST_BARS:]).astype(np.float64))
    field_index = {field: i for i, field in enumerate(FEATURES_PER_STREAM)}
    flows = {}
    for stream_index, stream in enumerate(STREAMS):
        block = matrix[:, stream_index*17:(stream_index+1)*17].astype(np.float64)
        ret, flow, vol, impact, observed = (
            block[:, field_index[name]] for name in (
                'return_5s', 'flow_imbalance', 'log_quote_notional',
                'signed_price_impact', 'has_return',
            )
        )
        for w in WINDOWS:
            r, f, v, p, mask = ret[-w:], flow[-w:], vol[-w:], impact[-w:], observed[-w:]
            rms = float(np.sqrt(np.mean(r*r)))
            ef = _ewma(f)
            # Published NumPy linear polynomial fit, slope per minute (12 bars).
            axis = np.arange(w, dtype=np.float64)
            fslope = float(np.polynomial.polynomial.polyfit(axis, f, 1)[1] * 12)
            vslope = float(np.polynomial.polynomial.polyfit(axis, v, 1)[1] * 12)
            quantiles = np.quantile(f, [.1, .5, .9], method='linear')
            mean_flow = float(f.mean())
            flows[(stream, w)] = mean_flow
            result.extend((float(ret[-w]), float(flow[-w]), float(vol[-w]),
                           _ewma(r), ef, fslope, vslope, *quantiles,
                           float(vol[-12:].mean() - v.mean()), rms,
                           ef*rms, mean_flow*float(v.mean()), _ewma(p), float(mask.mean())))
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        result.append(float(np.log(closes[f'spot_{symbol}']/closes[f'perp_{symbol}'])))
    for symbol in ('BTCUSDT', 'ETHUSDT'):
        for w in WINDOWS:
            result.append(flows[(f'spot_{symbol}', w)] - flows[(f'perp_{symbol}', w)])
    for venue in ('spot', 'perp'):
        for w in WINDOWS:
            result.append(flows[(f'{venue}_BTCUSDT', w)] - flows[(f'{venue}_ETHUSDT', w)])
    values = np.asarray(result, dtype=np.float64)
    if values.shape != (len(NAMES),) or not np.isfinite(values).all():
        raise ValueError('Undefined fixed features must abstain')
    values.setflags(write=False)
    return EndpointFeatures(decision_us, max(availability), NAMES, values)


def write_contract(path: Path):
    source = Path(__file__).resolve()
    frozen = Path(__file__).resolve().parents[2]/'src/quant/research_fast/dataset.py'
    contract = {
        'version': 'FEATURE_CONTRACT_V8_20261002_V1',
        'status': 'FIXED_JOINTLY_BEFORE_ANY_V8_MARKET_FIT',
        'selection_from_OOS': False, 'model_families_share_exact_adapter': True,
        'original_source_sha256': hashlib.sha256(frozen.read_bytes()).hexdigest(),
        'adapter_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'bar_seconds': 5, 'decision_seconds': 60, 'past_bars': 720,
        'windows_bars': list(WINDOWS), 'window_fields_in_order': list(WINDOW_FIELDS),
        'feature_names': list(NAMES), 'feature_count': len(NAMES),
        'base': 'Exact frozen feature_matrix + tabular_view over last256: 204 unnormalized summaries',
        'activity_units': 'Original log1p quote-USDT/base-coin/activity counts; no cross-asset nominal notional sum',
        'return_units': 'Original simple5s return; RMS masked-zero plus explicit observed_return_fraction, not annualized RV',
        'flow_units': 'Original buy-minus-sell divided by total aggressive quote notional; cross-flow differences of these dimensionless means',
        'EWMA': 'Official Polars span=window bars, adjust=False, min_samples=window; initialized at beginning of each exact causal window',
        'lag': 'Return/flow/logquote from row decision-window; the closed row at that past offset, never a forward row',
        'slope': 'Official NumPy polynomial linear fit versus bar index, multiplied by12 to per-minute slope',
        'quantile': 'Official NumPy linear-method q=.1,.5,.9 on past flow imbalance',
        'burst': 'Last12 closed bars mean logquote minus mean logquote of registered window',
        'interactions': 'EWMA flow times masked-zero return RMS; mean flow times mean logquote',
        'signed_impact_decay': 'Official Polars fixed-window EWMA of original signed_price_impact',
        'spot_perp_price_divergence': 'log(last exact spot close / last exact perp close); trade-close information only, not executable basis',
        'missing_policy': 'ABSTAIN with explicit reason on common decision calendar, never delete dates using future label validity. Undefined original return/interarrival retains original masks; invalid activity/price/availability/grid/quality rejects endpoint.',
        'availability': 'All four streams of every past720 row close<=available<=decision; output maximum actual availability; never substitute decision for later receipt',
        'normalization': 'None inside feature adapter. Official StandardScaler fitted only on eligible train/OOF fitting rows by common caller, identical across targets/models.',
        'memory': 'One720x68 temporary input and one478-value endpoint summary; caller must stream/memmap summaries rather than materialize sample-window cube.',
        'eligibility': 'Feature implementation only; candidateNONE and P1NOT_READY. Feature-valid calendar and fit-only label exclusions must be separately recorded.',
    }
    with path.open('x') as writer:
        json.dump(contract, writer, indent=2)
        writer.write('\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--write-contract', type=Path, required=True)
    write_contract(parser.parse_args().write_contract)
