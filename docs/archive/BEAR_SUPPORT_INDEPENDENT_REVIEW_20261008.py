"""Read saved source/support evidence independently; no fits or wallet replay."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
DAY = 86_400_000_000
LOCKED = 1_772_323_200_000_000
FEATURES = ['mom20', 'mom60', 'mom200', 'dist50', 'dist200', 'vol30', 'range', 'vol_z']


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def equal_values(left, right):
    return left.eq(right) | (left.isna() & right.isna())


def weekly_feedback(decisions, maturity, labels, anchor):
    """Definition-only reconstruction from fixed mature calendar slots."""
    result = np.full((len(decisions), 12), np.nan)
    slots = np.flatnonzero((decisions - anchor) % (7 * DAY) == 0)
    for row, decision in enumerate(decisions):
        known = slots[maturity[slots] <= decision]
        if len(known) < 12:
            continue
        recent = known[-12:]
        if not np.all(np.diff(decisions[recent]) == 7 * DAY) or not np.isfinite(labels[recent]).all():
            continue
        result[row] = np.concatenate([labels[known[-n:]].mean(0) for n in (1, 4, 12)])
    return result


def main():
    began=time.monotonic()
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', type=Path, default=ROOT/'reports/BEAR_SUPPORT_REPAIR_20261008.json')
    ap.add_argument('--protocol', type=Path, default=ROOT/'protocols/BEAR_SUPPORT_OBSERVED_REPAIR_20261008.json')
    ap.add_argument('--old-state', type=Path, default=Path('/home/ubuntu/coin/execution-state/joint-information-20261008-v1'))
    ap.add_argument('--manifest', type=Path, default=Path('/home/ubuntu/coin/coin_collector_v3_fixed/work/reports/DATASET_MANIFEST.json'))
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    r, protocol = load(args.result), load(args.protocol)
    assert digest(args.result) == '3e2dd4739561454cf7b6a49d3844d7c0360054c7e68696166558cc1c93c89870'
    prior = load(args.old_state/'RESULTS.json')
    state = Path(r['derived_refs'][0]['daily_path']).parent.resolve()
    output = args.output or state/'REVIEW.json'
    assert state.parent == Path('/home/ubuntu/coin/execution-state') and output.resolve().parent == state
    assert not output.exists(), 'Preserve an existing independent review'
    assert digest(args.protocol) == r['protocol_sha256']
    assert prior['protocol_sha256'] == protocol['parent_protocol_sha256']
    assert digest(args.manifest) == r['parent_dataset_sha256'] == protocol['parent_dataset_sha256']
    assert r['new_fits'] == r['new_wallets'] == 0 and r['locked_consumed'] is False
    assert r['qualification'] == 'NONE_CASH'
    work = args.manifest.parent.parent
    admitted = {str(work/x['relative_path']): x['sha256'] for x in load(args.manifest)['artifacts']}

    def old_table(path):
        path = Path(path)
        assert digest(path) == admitted[str(path)]
        return pl.read_parquet(path).to_pandas()

    def bound_table(ref, kind):
        path = Path(ref[kind+'_path'])
        assert path.parent.resolve() == state and digest(path) == ref[kind+'_sha256']
        return pl.read_parquet(path).to_pandas()

    # Verify archived identities; minute-by-minute provenance remains in the repair receipt.
    entries = {(e['symbol'], e['family'], e['day']): e for e in protocol['entries']}
    assert len(entries) == len(r['receipts']) == 26
    partial = [x for x in r['archive_coverage'] if x['missing_minutes']]
    for receipt in r['receipts']:
        date = f"{receipt['year']:04d}-{receipt['month']:02d}-{receipt['day']:02d}"
        key = (receipt['symbol'], receipt['family'], date)
        assert key in entries and receipt['url'] == entries[key]['url']
        path = Path(receipt['path']); actual_sha = digest(path)
        checksum = Path(str(path)+'.CHECKSUM').read_text().split()
        assert len(checksum) == 2 and checksum[1].lstrip('*') == path.name
        assert actual_sha == checksum[0].lower() == receipt['sha256']
    assert len(partial) == 5 and all(x['family'] == 'markPriceKlines' for x in partial)
    assert sorted(x['missing_minutes'] for x in partial) == [1, 5, 5, 6, 10]

    added_count = r['source_rows_added']; assert added_count == 30240
    with np.load(args.old_state/'PAST_INTENTS.npz', allow_pickle=False) as old_intents:
        decisions = old_intents['decision_us'].copy()
    assert np.all(np.diff(decisions) == DAY) and decisions[-1] < LOCKED
    cutoff = pd.Timestamp(int(decisions[-1])-DAY, unit='us', tz='UTC')
    late = decisions >= prior['protocol']['windows'][0]['start']
    old_market, new_market, missing_before, missing_after = [], [], 0, 0
    feature_deltas=[]
    old_refs = {ref['symbol']: ref for ref in prior['input_refs']}
    changes = {ref['symbol']: ref for ref in r['daily_changes']}
    for ref in r['derived_refs']:
        symbol = ref['symbol']; old_ref = old_refs[symbol]
        for kind in ('daily', 'past'):
            assert digest(old_ref[kind+'_path']) == old_ref[kind+'_sha256']
        old_daily = old_table(old_ref['daily_path'])
        assert pd.Timestamp(old_daily.dt.max()).value//1000 < LOCKED
        old_daily = old_daily.loc[old_daily.dt <= cutoff].set_index('dt')
        new_daily = bound_table(ref, 'daily').set_index('dt')
        old_daily.index = pd.DatetimeIndex(old_daily.index).as_unit('us')
        new_daily.index = pd.DatetimeIndex(new_daily.index).as_unit('us')
        assert old_daily.index.equals(new_daily.index) and set(old_daily.columns) == set(new_daily.columns)
        changed = ~equal_values(old_daily, new_daily[old_daily.columns]).all(axis=1)
        actual_dates = [str(date.date()) for date in old_daily.index[changed]]
        assert actual_dates == changes[symbol]['changed_daily_dates']
        permitted = {pd.Timestamp(e['day'], tz='UTC') for e in protocol['entries'] if e['symbol'] == symbol}
        permitted |= {day-pd.Timedelta(days=1) for day in list(permitted)}
        assert set(old_daily.index[changed]) <= permitted
        a, b = int((~old_daily.funding_interval_complete).sum()), int((~new_daily.funding_interval_complete).sum())
        assert (a, b) == (changes[symbol]['funding_incomplete_before'], changes[symbol]['funding_incomplete_after'])
        missing_before += a; missing_after += b
        for item in partial:
            if item['symbol'] == symbol:
                row = new_daily.loc[pd.Timestamp(item['day'], tz='UTC')]
                assert not bool(row.complete_mark) and pd.isna(row.mark)
        old_past = pl.read_parquet(old_ref['past_path'], columns=['decision_available_at','close','sma_signal',*FEATURES]).filter(pl.col('decision_available_at').dt.epoch('us') <= int(decisions[-1]))
        new_past = pl.read_parquet(ref['past_path'])
        for frame in (old_past, new_past):
            assert np.array_equal(frame['decision_available_at'].dt.epoch('us').to_numpy(), decisions)
        old_values, new_values = old_past.select(['close', 'sma_signal']+FEATURES).to_numpy(), new_past.select(['close', 'sma_signal']+FEATURES).to_numpy()
        # Source inputs for every scored rolling window must remain EXACT.
        # Initial audit failed a feature1e-12 check: corrected earlier history
        # changes pandas rolling accumulators by at most1.725e-12, not sources.
        start=pd.Timestamp(prior['protocol']['windows'][0]['start']-201*DAY,unit='us',tz='UTC')
        primitive=['close','high','low','quote_volume','complete_kline']
        assert equal_values(old_daily.loc[start:,primitive],new_daily.loc[start:,primitive]).all().all()
        delta=float(np.nanmax(np.abs(old_values[late]-new_values[late])))
        feature_deltas.append(dict(symbol=symbol,max_abs_delta=delta))
        assert np.allclose(old_values[late], new_values[late], atol=1e-10, rtol=0, equal_nan=True)
        old_market.append(np.isfinite(old_values[:, 2:]).all(1))
        new_market.append(np.isfinite(new_values[:, 2:]).all(1))
    assert (missing_before, missing_after) == (11, 0)
    old_market = np.stack(old_market).all(0); new_market = np.stack(new_market).all(0)

    # Reconstruct feedback/common and temporal sample support; never regenerate labels.
    anchor = prior['protocol']['anchor_us']; expected_maturity = decisions+7*DAY+120_000_001
    summary = []
    for ref in r['panel_refs']:
        assert digest(ref['path']) == ref['sha256']
        scale = ref['funding_scale']
        with np.load(ref['path'], allow_pickle=False) as panel, np.load(args.old_state/f'REFERENCE_PANEL_{scale}.npz', allow_pickle=False) as before:
            assert np.array_equal(panel['decision_us'], decisions) and np.array_equal(before['decision_us'], decisions)
            assert np.array_equal(panel['label_available_us'], expected_maturity)
            assert np.array_equal(before['label_available_us'], expected_maturity)
            assert np.allclose(panel['labels'][late], before['labels'][late], atol=1e-12, rtol=0, equal_nan=True)
            new_feedback = weekly_feedback(decisions, expected_maturity, panel['labels'], anchor)
            old_feedback = weekly_feedback(decisions, expected_maturity, before['labels'], anchor)
            assert np.allclose(new_feedback, panel['feedback'], atol=1e-12, rtol=0, equal_nan=True)
            assert np.allclose(old_feedback, before['feedback'], atol=1e-12, rtol=0, equal_nan=True)
            old_common = old_market & np.isfinite(old_feedback).all(1)
            assert np.array_equal(old_common, before['common'])
            old_complete = old_common & np.isfinite(before['labels']).all(1)
            common = new_market & np.isfinite(new_feedback).all(1) & np.isfinite(panel['labels']).all(1)
            assert np.array_equal(common, panel['common']) and np.all(panel['labels'][:, 3] == 0)
            counts = []
            for window in prior['protocol']['windows']:
                allowed = (decisions < window['start']) & (expected_maturity < window['start']-7*DAY)
                counts.append(dict(window=window['id'], before=int((old_complete & allowed).sum()), after=int((common & allowed).sum())))
            bear = (decisions >= 1_640_995_200_000_000) & (expected_maturity < 1_672_531_200_000_000)
            slots = (decisions-anchor) % (7*DAY) == 0
            days, weeks = int((bear & common).sum()), int((bear & common & slots).sum())
            assert (days, weeks) == (157, 22) and not (bear & old_complete).any()
            recorded = next(item for item in r['coverage'] if item['scale'] == scale)
            assert counts == recorded['train_counts'] and days == recorded['bear_daily_rows_after'] and weeks == recorded['bear_nonoverlap_week_blocks_after']
            summary.append(dict(scale=scale, train_counts=counts, bear_mature_days=days, bear_fixed_weeks=weeks))
    review = dict(status='PASS_WITH_LIMITATIONS', elapsed_seconds=time.monotonic()-began, review_source_sha256=digest(__file__), result_sha256=digest(args.result), protocol_sha256=digest(args.protocol),
                  official_archives=26, partial_mark_days_preserved=partial, source_rows_added=added_count,
                  funding_incomplete_before=missing_before, funding_incomplete_after=missing_after, support=summary,
                  old_inputs_unchanged=True, old_scored_feature_window_primitive_inputs_exact=True,
                  old_scored_feature_max_deltas=feature_deltas,feature_roundoff_tolerance=1e-10,
                  old_2024_2025_reference_labels_unchanged_at_1e_12=True,
                  new_fits=0, new_wallets=0, locked_consumed=False, qualification='NONE_CASH',
                  scope='Saved source/feature/reference-panel audit only; no new return evidence or label/wallet regeneration',
                  limitations=['Minute-row provenance/counts use frozen repair receipts; ZIP CSVs/monthly patches not independently reconstructed.',
                               'First independent feature1e-12 assertion failed at1.725e-12 rolling-roundoff; input windows exact, features checked1e-10; financial label1e-12 gate unchanged.',
                               'Official daily mark data still has five incomplete days; no interpolation or minute-risk certification.',
                               'Labels are checked against frozen saved panels, not independently regenerated from a wallet.',
                               'Recovered 2022 support is seen development, with overlapping daily labels; no profitability or investment qualification.',
                               'Funding units and publication assumptions remain conditional; no native Bybit certification.'])
    with output.open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(review, allow_nan=False))


if __name__ == '__main__':
    main()
