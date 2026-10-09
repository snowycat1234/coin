"""Bounded SOL source/units and CS warmup checks; no model or wallet run."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

DAY_MS = 86_400_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds')


def rows(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 1
        return list(csv.DictReader(io.StringIO(archive.read(archive.namelist()[0]).decode())))


def archive_proof(path, expected, url):
    checksum = Path(str(path) + '.CHECKSUM').read_text().split()[0]
    assert sha(path) == expected == checksum
    return dict(url=url, bytes=path.stat().st_size, SHA256=expected, official_checksum_verified=True, ZIP_CRC_verified=True)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('quality-root', 'evidence-root', 'native-root', 'original-portfolio', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    root, evidence = args.quality_root, args.evidence_root
    members = json.loads((root / 'MEMBERS.json').read_text())['files']
    mapping = dict(SOL_FEATURES='source_tables_not_model_inputs/daily_features/SOLUSDT.parquet',
                   SOL_DAILY='source_tables_not_model_inputs/economics/SOLUSDT_daily.parquet',
                   SOL_FUNDING_EVENTS='source_tables_not_model_inputs/economics/SOLUSDT_funding_events.parquet')
    table_proofs = {}
    for name, member in mapping.items():
        path = root / (name + '.parquet')
        assert sha(path) == members[member]['SHA256']
        table_proofs[name] = dict(member=member, bytes=path.stat().st_size, SHA256=sha(path))
    features = pq.read_table(root / 'SOL_FEATURES.parquet', columns=['dt', 'symbol', 'funding', 'premium', 'complete_funding', 'complete_premium'], use_threads=False).to_pylist()
    funding_events = pq.read_table(root / 'SOL_FUNDING_EVENTS.parquet', columns=['calc_time_ms', 'last_funding_rate', 'funding_interval_hours'], use_threads=False).to_pylist()
    assert sha(evidence / 'CORE5_PRE_MAY2024.npz') == 'f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c'
    with np.load(evidence / 'CORE5_PRE_MAY2024.npz', allow_pickle=False) as z:
        base = {k: z[k].copy() for k in ('x', 'close', 'symbol_order', 'feature_order', 'raw_observation_us', 'completed_day_available_us')}
    asset = list(base['symbol_order']).index('SOLUSDT')
    archives = dict(funding=archive_proof(root / 'SOLUSDT-fundingRate-2022-11.zip',
        '73fbada102584d8e19cb9594f04471f589ff37404b0cf64c0bd7cb4ac4d4a157',
        'https://data.binance.vision/data/futures/um/monthly/fundingRate/SOLUSDT/SOLUSDT-fundingRate-2022-11.zip'),
        premium=archive_proof(root / 'SOLUSDT-premium-1d-2022-11.zip',
        'ef4252b8a7bd9f476818bf9d0adcc4b4389e7cebead1d85bf1660fcf2b8e9431',
        'https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/SOLUSDT/1d/SOLUSDT-1d-2022-11.zip'))
    raw_fund, raw_premium = rows(root / 'SOLUSDT-fundingRate-2022-11.zip'), rows(root / 'SOLUSDT-premium-1d-2022-11.zip')
    prior = json.loads((root / 'PRIOR_RECEIPTS.json').read_text())['objects']
    receipt = next(x for x in prior if x['symbol'] == 'SOLUSDT' and x['family'] == 'fundingRate' and x['month'] == '2022-11')
    assert receipt['sha256'] == archives['funding']['SHA256']
    assert len(raw_fund) == receipt['numerical_rows'] == 165
    cached = {r['calc_time_ms']: r for r in funding_events}
    assert len({r['calc_time'] for r in raw_fund}) == len(raw_fund)
    for r in raw_fund:
        saved = cached[int(r['calc_time'])]
        assert saved['last_funding_rate'] == float(r['last_funding_rate'])
        assert saved['funding_interval_hours'] == float(r['funding_interval_hours'])
    observations = []
    for field, dates in [('funding', ('2022-11-09', '2022-11-10', '2022-11-11')),
                         ('premium', ('2022-11-08', '2022-11-09'))]:
        for date in dates:
            day_ms = int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp() * 1000)
            saved = next(r for r in features if str(r['dt'])[:10] == date)
            feature_row = int(np.flatnonzero(base['raw_observation_us'] == day_ms * 1000)[0])
            column = list(base['feature_order']).index(field)
            if field == 'funding':
                selected = [r for r in raw_fund if day_ms <= int(r['calc_time']) < day_ms + DAY_MS]
                value = sum((Decimal(r['last_funding_rate']) for r in selected), Decimal(0))
                details = [dict(actual_calc_time_ms=int(r['calc_time']), actual_UTC=utc(int(r['calc_time'])),
                    nominal_interval_hours=int(r['funding_interval_hours']), rate_fraction=r['last_funding_rate']) for r in selected]
            else:
                selected = next(r for r in raw_premium if int(r['open_time']) == day_ms)
                assert int(selected['close_time']) == day_ms + DAY_MS - 1
                assert Decimal(selected['low']) <= Decimal(selected['close']) <= Decimal(selected['high'])
                value = Decimal(selected['close'])
                details = dict(open_time_ms=int(selected['open_time']), close_time_ms=int(selected['close_time']),
                    open=selected['open'], high=selected['high'], low=selected['low'], close=selected['close'],
                    note='Independent small official 1d archive; original producer used minute aggregation.')
            assert saved['complete_' + field]
            assert abs(saved[field] - float(value)) < 6e-17
            actual = float(base['x'][feature_row, asset, column])
            assert actual == float(np.float32(value))
            assert int(base['completed_day_available_us'][feature_row]) == (day_ms + DAY_MS) * 1000
            observations.append(dict(field=field, observation_day_UTC=date,
                decision_available_UTC=utc(day_ms + DAY_MS), raw_exact_decimal=str(value),
                percent_equivalent=str(value * 100), source_table_float64=saved[field],
                model_input_float32=actual, float32_minus_raw=actual - float(value), raw_records=details))
    # An independent complete daily-close archive checks every November premium close.
    for r in raw_premium:
        date = utc(int(r['open_time']))[:10]
        saved = next(x for x in features if str(x['dt'])[:10] == date)
        assert saved['premium'] == float(r['close'])
    # Resolve the first five CS rows using already cached pre-May feature prices.
    assert sha(evidence / 'DEV_FEATURES.npz') == '800e39e53170fc87a279322b61f0f7f7b7a7812759267c58b1d4db948ab3aa8f'
    with np.load(evidence / 'DEV_FEATURES.npz', allow_pickle=False) as z:
        dev_close, dev_clock = z['close'].copy(), z['completed_day_available_us'].copy()
    assert sha(evidence / 'H1_VALIDATE.npz') == 'c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc'
    with np.load(evidence / 'H1_VALIDATE.npz', allow_pickle=False) as z:
        decisions, expected, past_returns = z['decision_us'].copy(), z['expert_targets'][:, 4].copy(), z['past_returns30'].copy()
    signal = args.native_root / 'scripts/research/public_cross_section_momentum.py'
    assert sha(signal) == '7d6f1794c0ade6e2c2d951a325e4e68ca45be0e87c84c68f05061442fad8a38f'
    assert sha(args.original_portfolio) == 'e4e02b0204e2861bb44eb78c8069b13a09edf6ca9390f3c86490d6e6f8a5e68b'
    sys.path[:0] = [str(args.native_root), str(args.native_root / 'src')]
    load(args.original_portfolio, 'modules.transformer_v2.portfolio')
    from scripts.research.public_cross_section_momentum import public_targets, ANCHOR_US, DAY_US
    complete_close = np.concatenate((base['close'], dev_close))
    complete_clock = np.concatenate((base['completed_day_available_us'], dev_clock))
    actual_targets, diagnostic = public_targets(complete_close, complete_clock, decisions,
                                               tuple(base['symbol_order']), tuple(base['symbol_order']))
    max_error = float(np.max(np.abs(actual_targets - expected)))
    assert max_error < 1e-12, max_error
    ranks = np.asarray(diagnostic['rank_us'])
    required_first = int(ranks[0] - 30 * DAY_US)
    fragment_first = int(decisions[0] - 30 * DAY_US)
    earlier_missing = np.arange(required_first, fragment_first, DAY_US)
    assert len(earlier_missing) == 2
    first_rank_indices = np.searchsorted(complete_clock, np.arange(required_first, ranks[0] + DAY_US, DAY_US))
    rank_history = complete_close[first_rank_indices]
    assert rank_history.shape == (31, 5) and np.isfinite(rank_history).all()
    assert np.array_equal(ranks[:5], np.full(5, ranks[0]))
    result = dict(status='PASS_OFFICIAL_RAW_SOL_PARITY_AND_FULL_CS_WARMUP',
        feature_transfer_commit='d901f130993b6f00ad6479dcc6a04b77627192b8',
        daily_feature_source_SHA256=table_proofs['SOL_FEATURES']['SHA256'], table_proofs=table_proofs,
        official_raw_archive_proofs=archives, original_funding_receipt=receipt,
        funding_raw_events_exact_matches=165, premium_daily_closes_exact_matches=30,
        observations=observations,
        unit_evidence=dict(funding='dimensionless per-settlement rate fraction; -0.02000000 is -2%; daily feature is unannualized arithmetic sum',
            premium='dimensionless premium-index fraction; end-of-day close, not funding rate or USDT price',
            dated_funding_announcement='https://www.binance.com/en/support/announcement/detail/e8be17e1e544418490e86723d84759f0',
            premium_formula_and_funding_amount='https://www.binance.com/en/support/faq/detail/360033525031'),
        CS_warmup=dict(status='ALL61_MATCH_WITH_EXISTING_CACHED_COMPLETED_CLOSE_HISTORY',
            maximum_target_error=max_error, first_five_decisions_UTC=[utc(int(t)//1000) for t in decisions[:5]],
            their_prior_weekly_rank_UTC=utc(int(ranks[0])//1000), required_first_close_UTC=utc(required_first//1000),
            fragment_first_close_UTC=utc(fragment_first//1000),
            missing_fragment_close_dates_UTC=[utc(int(t)//1000) for t in earlier_missing],
            complete_history31by5=True, missing_prices_recovered_from='already hash-verified pre-May feature-only close matrix; no padding or market download'),
        classification='AUTHENTIC_OFFICIAL_EXTREME_OBSERVATIONS_NOT_PLACEHOLDERS_OR_PIPELINE_UNIT_TIMESTAMP_ERRORS',
        limits=['Public archive identity and derivation are verified, not exchange account settlement audit or order-book reconstruction.',
                'Premium 1d archive is independent cross-frequency evidence; original minute object checksum is absent from this small transfer.',
                'No input transform, active normalization, training or economic wallet is changed.'])
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
