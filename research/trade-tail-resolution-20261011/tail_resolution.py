"""Finite, deterministic source-resolution diagnosis. No predictive model."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = '306b58c4a52035ac9f374de7c25d40dff22fb658'
SOURCE_PREFIX = 'research/core5-continuous-risk600-20261011/'
DAY_US = 86400000000
sys.path.insert(0, str(ROOT / SOURCE_PREFIX))
from prepare import SYMBOLS, PHASES, SourceReader, digest, git, old_five, save
from join import assemble


def recover():
    full, coverage = assemble(SOURCE)
    t, old, oldsha = old_five()
    panels, clocks = [old], [t]
    sources = [dict(commit='b4756ec8fb59457cfd8db74a79ca6a859f07f331', member_SHA256=oldsha)]
    for phase in list(PHASES)[1:]:
        raw = git('show', SOURCE + ':' + SOURCE_PREFIX + 'phases/' + phase + '/SOURCE_INDEX.json')
        row = json.loads(raw)['artifacts']['FIVE_MIN.npz']
        b = b''.join(SourceReader.part(SOURCE, p) for p in row['parts'])
        assert len(b) == row['bytes'] and digest(b) == row['SHA256']
        with np.load(io.BytesIO(b), allow_pickle=False) as a:
            assert tuple(a['symbol_order']) == SYMBOLS
            panels.append(a['close'].copy())
            clocks.append(a['available_us'].copy())
        sources.append(dict(phase=phase, index_SHA256=digest(raw), panel_SHA256=digest(b)))
    panel, clock = np.concatenate(panels), np.concatenate(clocks)
    assert panel.shape == (699 * 288, 5)
    assert np.all(np.diff(clock) == 300000000)
    np.testing.assert_array_equal(clock[287::288], full['available_us'])
    np.testing.assert_array_equal(panel[287::288], full['close'])
    return full, panel.reshape(699, 288, 5), dict(source_commit=SOURCE, source_panels=sources,
        coverage=coverage, panel_vector_SHA256=digest(panel.tobytes()),
        clock_vector_SHA256=digest(clock.tobytes()), panel_shape=list(panel.shape),
        minute_CSV_scan='REUSED_FIVE_PUBLIC_COLD_RAW_SOURCE_CERTIFICATES',
        original_STATE_open_attempts=0, provider_downloads=0)


def measure_resolution(close, high, low, samples, available_us, symbols):
    close, high, low, samples = [np.asarray(x, dtype=float) for x in (close, high, low, samples)]
    t = np.asarray(available_us, dtype=np.int64)
    if tuple(symbols) != SYMBOLS or close.ndim != 2 or close.shape[1] != 5:
        raise ValueError('Fixed symbol identity/order required')
    n = len(close)
    if n < 2 or high.shape != close.shape or low.shape != close.shape or samples.shape != (n, 288, 5):
        raise ValueError('Complete ordered day panels required')
    if t.shape != (n,) or np.any(t % DAY_US) or not np.all(np.diff(t) == DAY_US):
        raise ValueError('Dense following-UTC-midnight availability required')
    if any(not np.isfinite(a).all() or np.any(a <= 0) for a in (close, high, low, samples)):
        raise ValueError('Actual positive finite prices required')
    if not np.array_equal(samples[:, -1], close):
        raise ValueError('Actual day boundary close mismatch')
    sampled_high, sampled_low = samples.max(1), samples.min(1)
    if np.any(high < sampled_high) or np.any(low > sampled_low):
        raise ValueError('Actual OHLC must contain every sampled close')
    anchor = np.vstack([np.full((1, 5), np.nan), close[:-1]])
    result = dict(available_us=t, symbol_order=np.asarray(symbols), prior_close=anchor)
    for side, extreme, sampled in (('up', high, sampled_high), ('down', low, sampled_low)):
        sign = 1 if side == 'up' else -1
        actual = np.maximum(0, sign * np.log(extreme / anchor))
        coarse = np.maximum(0, sign * np.log(sampled / anchor))
        gap = actual - coarse
        relative = np.full_like(gap, np.nan)
        np.divide(gap, actual, out=relative, where=actual > 0)
        assert np.isnan(gap[0]).all() and np.all(gap[1:] >= 0)
        assert np.all((relative[1:][actual[1:] > 0] >= 0) & (relative[1:][actual[1:] > 0] <= 1))
        result.update({side + '_OHLC': actual, side + '_5m': coarse,
                       side + '_gap': gap, side + '_relative_gap': relative})
    result['common_valid'] = np.isfinite(result['up_gap']).all(1) & np.isfinite(result['down_gap']).all(1)
    assert not result['common_valid'][0] and result['common_valid'][1:].all()
    return result


def gap_summary(gap):
    x = np.asarray(gap, dtype=float) * 10000
    assert x.ndim == 1 and len(x) and np.isfinite(x).all()
    return dict(days=len(x), median_log_price_bp=float(np.median(x)),
                p90_log_price_bp=float(np.quantile(x, .9)), max_log_price_bp=float(x.max()),
                days_gap_gt10_log_price_bp=int(np.sum(x > 10)),
                days_gap_gt50_log_price_bp=int(np.sum(x > 50)))


def summarize(v):
    dates = [datetime.fromtimestamp(int(t) / 1000000 - 86400, timezone.utc).date().isoformat()
             for t in v['available_us']]
    valid = v['common_valid']
    masks = {'all_seen': valid, 'seen_2021': valid & np.array([d.startswith('2021') for d in dates]),
             'seen_2022': valid & np.array([d.startswith('2022') for d in dates])}
    output = {}
    for role, mask in masks.items():
        assert mask.sum() > 0
        block = dict(common_dates=int(mask.sum()), first_feature_day=np.array(dates)[mask][0],
                     last_feature_day=np.array(dates)[mask][-1], sides={})
        for side in ('up', 'down'):
            g, actual, coarse, frac = [v[side + s][mask] for s in ('_gap', '_OHLC', '_5m', '_relative_gap')]
            assets = {}
            for j, name in enumerate(SYMBOLS):
                finite = np.isfinite(frac[:, j])
                assets[name] = {**gap_summary(g[:, j]),
                    'actual_OHLC_zero_days': int(np.sum(actual[:, j] == 0)),
                    'sampled_zero_but_actual_positive_days': int(np.sum((coarse[:, j] == 0) & (actual[:, j] > 0))),
                    'relative_gap_valid_days': int(finite.sum()),
                    'relative_gap_median': float(np.median(frac[finite, j])) if finite.any() else None,
                    'relative_gap_p90': float(np.quantile(frac[finite, j], .9)) if finite.any() else None}
            block['sides'][side] = dict(per_asset=assets, jointdate_max_gap=gap_summary(g.max(1)))
        output[role] = block
    return output


def check_bindings():
    for line in (HERE / 'SOURCE_SHA256.txt').read_text().splitlines():
        sha, path = line.split(maxsplit=1)
        assert digest((ROOT / path).read_bytes()) == sha, path


def run(output):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists()
    assert shutil.disk_usage('/workspace').free >= 16106127360
    check_bindings()
    output.mkdir()
    start = time.monotonic()
    full, samples, source = recover()
    v = measure_resolution(full['close'], full['high'], full['low'], samples, full['available_us'], SYMBOLS)
    np.testing.assert_array_equal(v['up_OHLC'], full['max_log_up'])
    np.testing.assert_array_equal(v['down_OHLC'], full['max_log_down'])
    assert v['common_valid'].sum() == 698
    summary = summarize(v)
    assert summary['seen_2021']['common_dates'] == 364 and summary['seen_2022']['common_dates'] == 334
    np.savez_compressed(output / 'SOURCE_RESOLUTION.npz', **v)
    save(output / 'SUMMARY.json', summary)
    proof = dict(status='PASS_SOURCE_RESOLUTION_MEASUREMENT_ONLY', source=source,
        scientific_source_HEAD=git('rev-parse', 'HEAD').decode().strip(),
        protocol_SHA256=digest((HERE / 'PROTOCOL.json').read_bytes()),
        artifact_SHA256=digest((output / 'SOURCE_RESOLUTION.npz').read_bytes()),
        summary_SHA256=digest((output / 'SUMMARY.json').read_bytes()),
        original_diagnostic_attempts=1, fits=0, future_labels=0, prediction_scores=0, targets=0,
        wallets=0, random_seed='NOT_APPLICABLE_DETERMINISTIC_SOURCE_ARITHMETIC',
        elapsed_seconds=time.monotonic() - start,
        units='LOG_PRICE_BPS_NOT_PNL_BPS',
        scope='698common seen trade-source dates;1minuteOHLC extrema minus288actualend5minuteclose extrema, truepreviousdayclose anchor. No exactwithinminute eventpath, mark/fill/fee/funding/liquidation or predictiveincrement proof.')
    assert proof['elapsed_seconds'] < 120 and sum(p.stat().st_size for p in output.iterdir()) < 1000000
    save(output / 'SOURCE_PROOF.json', proof)
    print(json.dumps(dict(status=proof['status'], common_dates=698, elapsed_seconds=proof['elapsed_seconds'],
                         joint_up=summary['all_seen']['sides']['up']['jointdate_max_gap'],
                         joint_down=summary['all_seen']['sides']['down']['jointdate_max_gap'], fits=0, wallets=0)))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.output)
