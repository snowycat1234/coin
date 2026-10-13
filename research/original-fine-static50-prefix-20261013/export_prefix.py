"""Read-only exact saved ORIGINAL fine STATIC50 2024 prefix observer.
No simulation imports, network, restores, financial advances, or source downloads.
Core aggregation copied verbatim from reviewed samegross build_report.py.
Run: python export_prefix.py --root /path/to/saved/workspace --output /new/output.json
Writes only the explicitly supplied new output file, never an original input.
"""
from __future__ import annotations
import argparse, hashlib, json
from decimal import Decimal, localcontext
from pathlib import Path
MINUTE, DAY, CAPITAL = 60_000_000, 86_400_000_000, 10000.0
VOL_FORMULA = 'UTC completed-day NAV simple returns, initial NAV 10000; sample std ddof=1 times sqrt(365)'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def safe_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Absolute/traversing observer locator')
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Observer locator escapes root')
    return path

def integer(value, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError('Invalid observer integer: ' + label)
    return value

def pointer_at(recovery: Path) -> dict:
    pointer = read_json(recovery / 'POINTER.json')
    completed = integer(pointer['completed_minutes'], 'completed minutes')
    rows, paths = 0, set()
    for index, chunk in enumerate(pointer['chunks']):
        count = integer(chunk['rows'], 'chunk rows', 1)
        if count > 1440 or chunk['columns'] != 36 or chunk['path'] in paths:
            raise ValueError('Checkpoint minute metadata/geometry differs')
        if index < len(pointer['chunks']) - 1 and count != 1440:
            raise ValueError('Non-final checkpoint day is incomplete')
        safe_path(recovery, chunk['path'])
        paths.add(chunk['path'])
        rows += count
    if rows != completed:
        raise ValueError('Checkpoint minute count differs')
    return pointer

def execution_components(total) -> dict:
    """Label the frozen 4bp+4bp halves of an existing cost; never charge again."""
    half = total * .5 if total is not None else None
    return {'half_spread_cost_USDT': half,
            'slippage_cost_USDT': total - half if total is not None else None}

def daily_stats(day_nav: list[float]) -> dict:
    """Same numerical formula as the frozen runner, no incomplete day endpoint."""
    import numpy as np
    nav = np.r_[CAPITAL, np.asarray(day_nav, dtype=np.float64)]
    if not np.isfinite(nav).all() or np.any(nav <= 0):
        raise ValueError('Nonpositive/nonfinite daily NAV')
    returns = np.diff(nav) / nav[:-1]
    return {'completed_UTC_days': len(day_nav),
            'annualized_daily_vol': float(returns.std(ddof=1) * np.sqrt(365)) if len(returns) > 1 else None,
            'worst_observed_30_complete_days': float(np.min(nav[30:] / nav[:-30] - 1)) if len(nav) > 30 else None,
            'daily_NAV_raw_SHA256': hashlib.sha256(nav[1:].tobytes()).hexdigest(),
            'formula': VOL_FORMULA,
            'incomplete_UTC_day_excluded_from_daily_returns': True}

def stream_prefix(recovery: Path, minutes: int, weights=None, *, numeric=None, start_us=None) -> dict:
    """SHA/float64-verified chunks, one day at a time; no post-minute halt mark.

    All referenced chunks are verified even beyond the selected prefix. Optional
    full fingerprint validation binds all 36 saved numeric columns and close_us.
    """
    import numpy as np
    pointer = pointer_at(recovery)
    minutes = integer(minutes, 'requested prefix')
    if minutes > pointer['completed_minutes']:
        raise ValueError('Requested common prefix exceeds checkpoint')
    if weights is not None:
        weights = np.asarray(weights)
        if (weights.dtype != np.float64 or weights.ndim != 2 or weights.shape[1] != 5
                or not np.isfinite(weights).all() or len(pointer['chunks']) > len(weights)):
            raise ValueError('Frozen target weight geometry differs')
    if numeric is not None:
        if minutes != pointer['completed_minutes'] or type(start_us) is not int:
            raise ValueError('Numeric fingerprint requires the complete saved horizon and clock')
        if len(numeric.get('columns', [])) != 37:
            raise ValueError('Saved numeric fingerprint geometry differs')
        column_hashes = [hashlib.sha256() for _ in range(37)]
    count, peak, drawdown, last = 0, CAPITAL, 0.0, None
    gross_sum, gross_max, gap_sum, net_sum, net_max = 0.0, None, 0.0, 0.0, None
    raw_hash, day_nav = hashlib.sha256(), []
    cumulative = dict.fromkeys(('fees_USDT', 'execution_cost_USDT', 'funding_USDT', 'gross_fill_turnover_USDT'))
    for day, meta in enumerate(pointer['chunks']):
        path = safe_path(recovery, meta['path'])
        if sha(path) != meta['SHA256']:
            raise ValueError('Saved minute chunk SHA differs')
        with np.load(path, allow_pickle=False) as archive:
            if archive.files != ['minute_chunk']:
                raise ValueError('Checkpoint minute archive schema differs')
            chunk = archive['minute_chunk']
        if chunk.dtype != np.float64 or chunk.shape != (meta['rows'], 36):
            raise ValueError('Saved minute chunk float64 geometry differs')
        if numeric is not None:
            for column in range(36):
                column_hashes[column].update(chunk[:, column].tobytes())
            clocks = start_us + np.arange(day * 1440 + 1, day * 1440 + len(chunk) + 1, dtype=np.int64) * MINUTE
            column_hashes[36].update(clocks.tobytes())
        used = chunk[:max(0, min(len(chunk), minutes - count))]
        if not len(used):
            continue
        if (not np.isfinite(used[:, 0]).all() or np.any(used[:, 0] <= 0)
                or not np.isfinite(used[:, 5:9]).all() or not np.isfinite(used[:, 29:36]).all()
                or np.any(used[:, 34] < 0)):
            raise ValueError('Invalid minute NAV/cost/weights or negative gross exposure')
        raw_hash.update(used.tobytes(order='C'))
        for nav in used[:, 0]:
            last = float(nav)
            peak = max(peak, last)
            drawdown = max(drawdown, 1.0 - last / peak)
        gross_sum += float(used[:, 34].sum())
        maximum = float(used[:, 34].max())
        gross_max = maximum if gross_max is None else max(gross_max, maximum)
        net_sum += float(used[:, 35].sum())
        maximum = float(np.abs(used[:, 35]).max())
        net_max = maximum if net_max is None else max(net_max, maximum)
        if weights is not None:
            gap_sum += float(np.abs(used[:, 29:34] - weights[day]).sum())
        if len(used) == 1440:
            day_nav.append(float(used[-1, 0]))
        for column, key in enumerate(cumulative, start=5):
            cumulative[key] = float(used[-1, column])
        count += len(used)
    if count != minutes:
        raise ValueError('Truncated saved common prefix')
    if numeric is not None:
        names = ('nav', 'free_cash', 'isolated_balance', 'gross_notional', 'net_signed_notional',
                 'cumulative_fees', 'cumulative_execution_costs', 'cumulative_funding', 'cumulative_turnover')
        if tuple(row.get('name') for row in numeric['columns'][:9]) != names or numeric['columns'][-1].get('name') != 'close_us':
            raise ValueError('Saved numeric column order differs')
        for index, row in enumerate(numeric['columns']):
            dtype = '<i8' if index == 36 else '<f8'
            if row.get('rows') != minutes or row.get('dtype') != dtype or row.get('raw_SHA256') != column_hashes[index].hexdigest():
                raise ValueError('All saved numeric minute bits differ: ' + str(row.get('name')))
    cumulative.update(execution_components(cumulative['execution_cost_USDT']))
    return {'common_completed_minutes': count, 'last_completed_minute_NAV_USDT': last,
            'last_completed_minute_marked_PnL_USDT': last - CAPITAL if last is not None else None,
            'max_drawdown_of_completed_minute_prefix': drawdown if count else None,
            'mean_minute_close_gross_weight_of_prefix': gross_sum / count if count else None,
            'max_minute_close_gross_weight_of_prefix': gross_max,
            'mean_actual_signed_net_of_prefix': net_sum / count if count else None,
            'max_actual_abs_signed_net_of_prefix': net_max,
            'mean_l1_target_weight_gap_of_prefix': gap_sum / count if count and weights is not None else None,
            'minute_prefix_raw_SHA256': raw_hash.hexdigest(),
            'chunks_sha_and_geometry_verified': len(pointer['chunks']),
            'all_saved_numeric_bits_verified': numeric is not None,
            'daily_statistics': daily_stats(day_nav),
            'saved_cumulative_at_last_completed_minute': cumulative,
            'excludes_halt_mark_after_last_completed_minute': True, 'financial_advances': 0}

def export(root: Path) -> dict:
    import numpy as np
    base_rel = 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL'
    base = root / base_rel
    binding = read_json(base / 'BINDING.json')
    result = read_json(base / 'RESULT.json')
    numeric = read_json(base / 'MINUTE_NUMERIC.json')
    pointer = pointer_at(base / 'recovery')
    expected = {'case_id':'Y2024_STATIC50_FINE_ORIGINAL','year':2024,'arm':'STATIC50','mode':'ORIGINAL','capital_USDT':10000,
        'calendar':[1704067200000000,1735689600000000],
        'source_index_SHA256':'0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69',
        'target_archive_SHA256':'4f3b615b524de3220df3c10595ba2a7723f6e62dcff59b31ed82cb9476a9b5d5',
        'target_array_SHA256':'c70b9a79c9005543cf866ea5e5be065f12b816537bf4747562c200498db9a394'}
    for k,v in expected.items():
        if binding[k] != v or pointer['binding'][k] != v: raise ValueError('Wrong baseline identity: '+k)
    pins = {'RESULT.json':'7d44047a38b272fbfda3270856c6ec88fa808957b7a9cba36bacff9931560d7d',
        'BINDING.json':'07e738f8a59ca0be141e7cc7e06a7563161d34a6254a851d057dd964ba7f24c5',
        'ACCOUNT.json':'dc1e8d1ff753c08fd14449f631e8b97de2103cc557a0c61a18f55690ddb5cb38',
        'MINUTE_NUMERIC.json':'ce9aa43ef48cf81c630d52fb47a12741a4941b5c530cbb4e1d9df2ec55fb9960',
        'recovery/POINTER.json':'9f213ea1ad76ede0434645bed03151278875d1c4754e73213a20e7b01b384052'}
    for rel,digest in pins.items():
        if sha(base/rel) != digest: raise ValueError('Wrong baseline bytes: '+rel)
    assert pointer['completed_minutes'] == result['completed_minutes'] == 461448
    plan = read_json(root / 'coin_quantity_resolution_20261013/CASE_BINDINGS.json')
    case = next(c for c in plan['cases'] if c['case_id']=='Y2024_STATIC50')
    source = root / case['source_index_local_locator']
    target = root / case['target_archive_local_locator']
    assert sha(source) == expected['source_index_SHA256']
    assert sha(target) == expected['target_archive_SHA256']
    with np.load(target,allow_pickle=False) as z: weights = z['STATIC50']
    assert hashlib.sha256(weights.tobytes()).hexdigest()==expected['target_array_SHA256']
    metrics = stream_prefix(base/'recovery',461448,weights,numeric=numeric,start_us=binding['calendar'][0])
    final_meta = pointer['chunks'][-1]
    with np.load(base/'recovery'/final_meta['path'],allow_pickle=False) as z: last=z['minute_chunk'][-1]
    end = binding['calendar'][0] + 461448 * MINUTE
    ledger = read_json(base/'ACCOUNT.json')
    trades = [t for t in ledger['trades'] if t['event_us'] <= end]
    fund = [t for t in ledger['funding'] if t['event_us'] <= end]
    with localcontext() as context:
        context.prec = 80
        def dec(t,k):
            if 'decimal_strings' in t: return Decimal(t['decimal_strings'][k])
            if (k=='signed_funding_USDT' and t['signed_funding_USDT']==0.0 and
                    t['quantity']==0.0 and t.get('owned') is False and
                    t.get('status')=='NO_POSITION_NO_PAST_MARK'): return Decimal(0)
            raise ValueError('Exact ledger Decimal string absent: '+k)
        exact_costs = {
            'fees_USDT':str(sum((dec(t,'fee_USDT_mid') for t in trades),Decimal(0))),
            'execution_cost_USDT':str(sum((dec(t,'execution_cost') for t in trades),Decimal(0))),
            'funding_USDT':str(sum((dec(t,'signed_funding_USDT') for t in fund),Decimal(0))),
            'gross_fill_turnover_USDT':str(sum((abs(dec(t,'position_delta'))*dec(t,'fill_price') for t in trades),Decimal(0)))}
    assert len(trades)==len(ledger['trades']) and len(fund)==len(ledger['funding'])
    symbols = case['symbols']
    endpoint = {numeric['columns'][i]['name']:float(last[i]) for i in range(36)}
    metrics['last_completed_minute_marked_return'] = metrics['last_completed_minute_marked_PnL_USDT']/CAPITAL
    metrics['prefix_paid_cash_PnL_USDT'] = None
    metrics['prefix_paid_flat'] = False
    frozen = read_json(root/'coin_quantity_resolution_20261013/FROZEN_CODE.json')
    code_hashes={}
    for rel in ('fine_account.py','run_cases.py','FINE_PROFILE.json'):
        path=root/'coin_quantity_resolution_20261013'/rel
        assert sha(path)==frozen['files_SHA256'][rel]
        code_hashes['coin_quantity_resolution_20261013/'+rel]=sha(path)
    for rel,field in (('coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py','account_SHA256'),
                      ('coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py','scheduler_SHA256')):
        assert sha(root/rel)==binding[field]
        code_hashes[rel]=binding[field]
    for k,v in exact_costs.items():
        assert float(Decimal(v))==metrics['saved_cumulative_at_last_completed_minute'][k]
    chunk_manifest=json.dumps(pointer['chunks'],sort_keys=True,separators=(',',':')).encode()
    output = {'schema':'original_fine_static50_2024_saved_prefix_export_v1',
        'status':'PASS_321_CHUNKS_SHA_SHAPE_AND_ALL_37_SAVED_COLUMN_BITS',
        'identity':expected,'binding':binding,
        'window':{'calendar_start_us':binding['calendar'][0], 'calendar_end_exclusive_us':binding['calendar'][1],
            'first_completed_minute_close_us':binding['calendar'][0]+MINUTE,
            'last_completed_minute_close_us':end,
            'first_completed_minute_close_UTC':'2024-01-01T00:01:00Z',
            'last_completed_minute_close_UTC':'2024-11-16T10:48:00Z',
            'close_clock_rule':'start_us + (row_index + 1)*60000000',
            'completed_minute_count':461448, 'complete_UTC_days':320,'last_partial_day_rows':648,
            'sampling':'minute closes in (2024-01-01T00:00:00Z,2024-11-16T10:48:00Z]; initial NAV 10000 included only as drawdown/daily-return anchor',
            'halt_mark_excluded_us':result['stop_us'], 'halt_mark_excluded_UTC':'2024-11-16T10:49:00Z'},
        'numeric_semantics':{'minute_storage':'IEEE754 float64 little endian <f8 saved exact checkpoint bits',
            'prefix_NAV_Decimal':None, 'prefix_PnL_Decimal':None,
            'prefix_decimal_NAV_available':False,
            'NAV_prefix_float_hex':float(last[0]).hex(),
            'PnL_prefix_float_hex':metrics['last_completed_minute_marked_PnL_USDT'].hex(),
            'aggregate_algorithm':'verbatim reviewed stream_prefix: per-row running DD with initial NAV 10000; float64 chunk sums followed by Python float day accumulation; no decimal precision claim for NAV or exposure aggregates',
            'ledger_cost_decimal_semantics':'exact finite Decimal string sums at precision 80; turnover=sum(abs(position_delta)*fill_price), matching source gross_fill_turnover; filtered event_us<=prefix_end; 5 unowned zero-position funding records contribute exact zero; no prefix Decimal NAV is derived'},
        'metrics':metrics,'endpoint_saved_float64_columns':endpoint,
        'endpoint_saved_float64_hex':{k:v.hex() for k,v in endpoint.items()},
        'ledger_prefix_exact_decimal_costs':exact_costs,
        'ledger_prefix_funding_zero_without_decimal_string_events':sum('decimal_strings' not in t for t in fund),
        'ledger_prefix_trade_legs':len(trades),'ledger_prefix_funding_events':len(fund),
        'input_hashes':{base_rel+'/'+p:h for p,h in pins.items()},
        'source_target_code_hashes':{case['source_index_local_locator']:sha(source),case['target_archive_local_locator']:sha(target),**code_hashes},
        'all_saved_column_fingerprints':numeric['columns'],
        'chunks_manifest_canonical_SHA256':hashlib.sha256(chunk_manifest).hexdigest(),
        'chunks_manifest_file':'CHUNKS.json','last_chunk':final_meta,
        'observer_origin':{'file':'coin_follow_samegross_postrun_20261013/build_report.py',
            'SHA256':'92625e522c2c9374706a916ba3aae129565b2891d130f3c9e8ccc567d0e4e390',
            'published_commit':'c63a936b7422f7dbf33f6234acebfb02a3b1f3c6',
            'published_path':'research/static50-follow-samegross-20261013/postrun/build_report.py'},
        'halt_snapshot_not_prefix':{'marked_PnL_USDT':result['marked_PnL_USDT'],
            'independent_decimal_NAV_bridge':result['independent_decimal_NAV_bridge'],
            'snapshot_SHA256':pointer['snapshot_SHA256'],'snapshot_path':pointer['snapshot_path']},
        'financial_advances':0,'cold_restores':0,'raw_market_source_downloads':0,
        'full_year_paid_result':None,'not_annual_result':True}
    prior=read_json(root/'coin_follow_samegross_postrun_20261013/RESULTS_COMPACT.json')
    def visit(obj):
        if isinstance(obj,dict):
            if obj.get('case_id')=='Y2024_STATIC50_FINE_ORIGINAL' and 'completed_minute_prefix_metrics' in obj:
                return obj['completed_minute_prefix_metrics']
            for val in obj.values():
                x=visit(val)
                if x is not None:return x
        elif isinstance(obj,list):
            for val in obj:
                x=visit(val)
                if x is not None:return x
        return None
    old=visit(prior)
    assert old is not None
    assert all(metrics[k]==v for k,v in old.items())
    output['crosscheck_existing_reviewed_follow_report_exact_match']=True
    return output

if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('--root',type=Path,required=True)
    args.add_argument('--output',type=Path,required=True)
    args=args.parse_args()
    output=export(args.root)
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(output,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    pointer=read_json(args.root/'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/recovery/POINTER.json')
    with (args.output.parent/'CHUNKS.json').open('x',encoding='utf-8') as f:
        json.dump(pointer['chunks'],f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({'output':str(args.output),'SHA256':sha(args.output),'metrics':output['metrics']}))
