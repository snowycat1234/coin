"""Read-only reconstruction of saved isolated SHORT liquidation episodes.

No strategy fit, counterfactual wallet, new market download or locked data read.
Use the existing lossless ledger codec; original account bytes remain untouched.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

DAY = 86_400_000_000
EXPECTED = '8e034c498ac50847b5130408d8f17a0d95b6975711023b37de0f9b0eca46bc3f'
ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc(clock):
    return datetime.fromtimestamp(clock / 1e6, timezone.utc).isoformat()


def save(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def inspect(row):
    import polars as pl
    from modules.transformer_v3.storage import xor_decode

    case_path = Path(row['result_path'])
    assert sha(case_path) == row['result_sha256']
    case = json.loads(case_path.read_text())
    used = {str(case_path): sha(case_path)}

    def artifact(name, as_json=False):
        entry = case['artifacts'][name]
        path = Path(entry['path'])
        assert sha(path) == entry['sha256'], name
        used[str(path)] = entry['sha256']
        if not as_json:
            return path
        raw = gzip.decompress(path.read_bytes())
        assert hashlib.sha256(raw).hexdigest() == entry['uncompressed_sha256']
        return json.loads(raw)

    liquidations = artifact('liquidations.json', True)
    assert len(liquidations) == 1 and liquidations[0]['symbol'] == 'XRPUSDT'
    witness = liquidations[0]
    symbol, clock = witness['symbol'], witness['event_us']
    all_trades = artifact('trades.json', True)
    trades = sorted((x for x in all_trades if x['symbol'] == symbol), key=lambda x: x['event_us'])
    before = [x for x in trades if x['event_us'] < clock]
    episode_start = max(x['event_us'] for x in before if x['quantity_before'] == 0 and x['quantity_after'] < 0)
    episode = [x for x in before if x['event_us'] >= episode_start]
    assert all(x['quantity_after'] < 0 for x in episode)
    takeover = next(x for x in trades if x['fill_id'] == witness['id'])

    # Independent Decimal cash/inventory reconstruction from actual fill deltas.
    # Funding debits free cash first; verified ledger margin also catches depletion.
    with localcontext() as ctx:
        ctx.prec = 40
        q = sum((Decimal(x['decimal_strings']['position_delta']) for x in before), Decimal(0))
        collateral = sum((Decimal(x['decimal_strings']['isolated_balance_delta']) for x in before), Decimal(0))
        entry = Decimal(before[-1]['decimal_strings']['entry_price_after'])
        assert q == Decimal(witness['quantity']) and entry == Decimal(witness['entry_price'])
        assert abs(collateral - Decimal(witness['isolated_margin_lost'])) < Decimal('1e-30')
        expected_bankruptcy = entry + collateral / abs(q)
        assert abs(expected_bankruptcy - Decimal(witness['bankruptcy_price'])) < Decimal('1e-30')
        assert Decimal(takeover['decimal_strings']['realized_PnL']) == -collateral
        assert Decimal(takeover['decimal_strings']['quantity_after']) == 0
        equity_at_mark = collateral + q * (Decimal(witness['mark_price']) - entry)

    path = artifact('minute_nav_inventory.parquet')
    encoding = case['artifacts']['minute_nav_inventory.parquet']
    frame = pl.read_parquet(path).filter(pl.col('close_us').is_between(episode_start, clock))
    reference = encoding.get('xor_market_reference')
    assert reference, 'Use the registered lossless codec, never interpret encoded integers as money'
    assert sha(reference['path']) == reference['sha256']
    used[reference['path']] = reference['sha256']
    ref = pl.read_parquet(reference['path']).filter(pl.col('close_us').is_in(frame['close_us'].implode()))
    assert frame['close_us'].equals(ref['close_us'])
    frame = xor_decode(frame, ref)
    fields = ['close_us', 'nav', 'free_cash', 'gross_weight', 'net_signed_weight']
    fields += [symbol + x for x in ('_quantity', '_isolated_balance', '_isolated_equity', '_signed_weight')]

    def snapshot(record):
        result = {k: record[k] for k in fields}
        result.update(utc=utc(record['close_us']), mark=ref.filter(pl.col('close_us') == record['close_us'])[symbol][0])
        margin = record[symbol + '_isolated_balance']
        result['isolated_equity_over_collateral'] = record[symbol + '_isolated_equity'] / margin if margin else None
        return result

    previous = frame.filter(pl.col('close_us') < clock).tail(1).row(0, named=True)
    assert previous[symbol + '_quantity'] == float(q)
    assert abs(previous[symbol + '_isolated_balance'] - float(collateral)) <= 1e-8
    with localcontext() as ctx:
        ctx.prec = 40
        prior_mark = Decimal(str(ref.filter(pl.col('close_us') == previous['close_us'])[symbol][0]))
        independent_equity = collateral + q * (prior_mark - entry)
    assert abs(float(independent_equity) - previous[symbol + '_isolated_equity']) <= 1e-8
    after = frame.filter(pl.col('close_us') == clock).row(0, named=True)
    assert after[symbol + '_quantity'] == after[symbol + '_isolated_balance'] == 0
    assert ref.filter(pl.col('close_us') == clock)[symbol][0] == float(witness['mark_price'])

    # Descriptive lead times only, not a threshold search or counterfactual PnL.
    crossings = []
    for fraction in (.5, .25, .1):
        hit = frame.filter((pl.col(symbol + '_quantity') < 0) & (pl.col(symbol + '_isolated_equity') <= fraction * pl.col(symbol + '_isolated_balance')))
        if hit.height:
            record = snapshot(hit.row(0, named=True))
            crossings.append(dict(fraction=fraction, hours_before_liquidation=(clock-record['close_us'])/3.6e9, observation=record))

    targets = pl.read_parquet(artifact('targets.parquet')).filter((pl.col('symbol') == symbol) & pl.col('available_us').is_between(episode_start - DAY, clock + 7*DAY))
    recent = targets.filter(pl.col('available_us').is_between(clock-14*DAY, clock+7*DAY)).to_dicts()
    for x in recent:
        x['utc'] = utc(x['available_us'])
    episode_targets = targets.filter(pl.col('available_us') <= clock)
    rejected = [x for x in artifact('rejections.json', True) if x['symbol'] == symbol and episode_start <= x['event_us'] <= clock]
    breaches = artifact('breaches.json', True)
    latest_target = episode_targets.tail(1).row(0, named=True)
    daily = frame.filter((pl.col('close_us') % DAY == 0) & (pl.col('close_us') >= clock-14*DAY))
    relevant = episode[-10:] + [x for x in trades if x['event_us'] >= clock][:5]
    fill_keys = ('event_us', 'signal_us', 'fill_id', 'leg', 'side', 'quantity_before', 'quantity_after', 'entry_price_after', 'realized_PnL', 'fee_amount', 'execution_cost', 'liquidation_takeover')
    keep = lambda x: {k: x[k] for k in fill_keys if k in x}
    return dict(id=case['task']['id'], family=row['family'], funding_scale=row['funding_scale'], witness=witness,
        actual_episode_start_us=episode_start, actual_episode_start_utc=utc(episode_start), liquidation_utc=utc(clock),
        short_episode_days=(clock-episode_start)/DAY, episode_fills=len(episode), episode_reductions=sum(x['leg']=='CLOSE' for x in episode),
        latest_target=latest_target, nonnegative_targets_before_liquidation=episode_targets.filter(pl.col('target_weight')>=0).height,
        episode_target_min=episode_targets['target_weight'].min(), episode_target_max=episode_targets['target_weight'].max(),
        targets_near_liquidation=recent, recent_fills=[keep(x) for x in relevant],
        rejection_status_counts=dict(Counter(x['status'] for x in rejected)), rejection_reason_counts=dict(Counter(str(x.get('reason')) for x in rejected)),
        last_rejections=rejected[-12:], account_breaches=len(breaches),
        decimal_reconstruction=dict(quantity=str(q), collateral=str(collateral), entry_price=str(entry), expected_bankruptcy_price=str(expected_bankruptcy),
            isolated_equity_at_liquidation_mark=str(equity_at_mark), last_minute_equity_error=abs(float(independent_equity)-previous[symbol+'_isolated_equity'])),
        pre_liquidation=snapshot(previous), post_liquidation=snapshot(after), descriptive_equity_crossings=crossings,
        last_daily_observations=[snapshot(x) for x in daily.iter_rows(named=True)], source_hashes=used,
        mechanism='PERSISTENT_SHORT_WITHOUT_PRELIQUIDATION_PROTECTION' if latest_target['target_weight'] < 0 else 'EXIT_OR_OTHER_PATH_REQUIRES_REVIEW')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', type=Path, default=ROOT/'reports/FIXED_TREND_EXTENSION_20261008.json')
    ap.add_argument('--state', type=Path, required=True)
    args = ap.parse_args()
    began = time.monotonic()
    assert os.uname().sysname == 'Linux' and sha(args.result) == EXPECTED
    assert args.state.resolve().parent == Path('/home/ubuntu/coin/execution-state')
    group = Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip() != 'max' and int((group/'memory.max').read_text()) <= 8_000_000_000
    assert (group/'memory.swap.max').read_text().strip() == '0'
    args.state.mkdir(exist_ok=False)
    report = json.loads(args.result.read_text())
    selected = [x for x in report['cases'] if x['liquidations']]
    assert len(selected) == 4
    cases = []
    for i, row in enumerate(selected, 1):
        cases.append(inspect(row))
        save(args.state/f'CASE_{i}.json', cases[-1])
        print(f'[FORENSIC {i}/4] {cases[-1]["id"]} {cases[-1]["mechanism"]}', flush=True)
    result = dict(status='COMPLETE_READ_ONLY_LIQUIDATION_RECONSTRUCTION', parent_result_sha256=sha(args.result),
        source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip(), inspector_sha256=sha(__file__),
        cases=cases, new_wallets=0, new_fits=0, market_downloads=0, locked_consumed=False, qualification='NONE_CASH',
        elapsed_seconds=time.monotonic()-began, RAM_limit_bytes=int((group/'memory.max').read_text()),
        limitations=['Seen-development forensic, not new independent investment evidence.',
            'Descriptive collateral crossings are not selected stop parameters or counterfactual performance.',
            'Minute mark liquidation and MMR=.005 are conditional research assumptions; not certified native Bybit rules.',
            'Financial and signal kernels unchanged; no claim that a protective exit would improve net returns.'])
    save(args.state/'RESULTS.json', result)
    print(json.dumps(dict(status=result['status'], cases=len(cases), elapsed_seconds=result['elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    main()
