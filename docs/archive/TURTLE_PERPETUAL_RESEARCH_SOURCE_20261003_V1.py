"""D047 Turtle hook/state bridge over the accepted perpetual financial loop.

One fixed 4h public strategy, four conditional cost/unit accounts. Finance,
minute mark/funding ordering and output metrics remain original functions.
Stops are delayed completed-minute observations, never ideal intrabar fills.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl

from quant.paths import ROOT, STATE
from scripts.investment import perpetual_directional as base
from scripts.investment import perpetual_303_research as parent
from scripts.investment import public_long_development_adapter as private
from scripts.investment import turtle_perpetual_bridge as strategy
from scripts.research_v8.registry import append_event as original_append_event

FOUR_HOURS = 14_400_000_000
CONTRACT = 'D047_FIXED303D_TURTLE4H_CALLBACK_CONDITIONAL_V1'
STATUS = 'COMPLETE_D047_FIXED303D_TURTLE4H_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
STRATEGY_ID = 'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'
MODES = ('LONG_SHORT',)
RULES = dict(base.RULES, modes=list(MODES), signal='PINNED_PUBLIC_TURTLERULES_ACTUAL_HOOK_STATE',
    timeframe_minutes=240, signal_warmup_completed_4h_bars=240,
    entry_period=20, exit_period=10, ATR_period=20, ATR_stop_multiple=2,
    maximum_pyramiding_levels=4, pyramiding_threshold_ATR=.5,
    channel_includes_current_completed_bar=True,
    partial_callback='ONCE_FIRST_POSITIVE_EXECUTION_PER_LOGICAL_ADD_THEN_UPDATE_PROTECTION_QTY',
    stop='ALREADY_ARMED_STOP_OBSERVED_AFTER_COMPLETE_MINUTE_THEN_NEXT_ELIGIBLE_OPEN_PLUS1US',
    stop_unfilled='PRESERVE_PENDING_AND_HALT_NE_AFTER_FIVE_ATTEMPTS_NOT_FREE_CLOSE',
    sizing='ORIGINAL_ATR_WALLET_UNIT_THEN_COINS_PAST_SIGNED_COVARIANCE_AND_SHARED_CAPS',
    planned_selectors=4, planned_trading_account_simulations=4,
    planned_constant_cash_baselines=0, native_Jesse_intrabar_replicated=False,
    classification='SEEN_DEVELOPMENT_SCREENING_WITH_CONDITIONAL_FUNDING_UNITS')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compact_append_event(path, event):
    """Keep every event; refer to the frozen full source map without repeating it."""
    value = dict(event)
    value['source_hashes'] = {'protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json': value['protocol_hash']}
    return original_append_event(path, value)


def prepare_signal_context(window):
    """Strict fixed UTC aggregation; no candle or missing-minute imputation."""
    context = {}
    for symbol in base.SYMBOLS:
        market = window['market'][symbol]
        minute = pl.DataFrame(dict(open_us=window['times'], open=market['open'],
            close=market['close'], high=market['high'], low=market['low'], volume=market['volume']))
        bars = (minute.with_columns((pl.col('open_us') // FOUR_HOURS * FOUR_HOURS).alias('bucket'))
            .group_by('bucket', maintain_order=True).agg(pl.col('open').first(), pl.col('close').last(),
                pl.col('high').max(), pl.col('low').min(), pl.col('volume').sum(), pl.len().alias('rows'))
            .sort('bucket'))
        base.need(bars['rows'].eq(240).all(), 'Every 4h signal candle owns exactly240 observed minute rows')
        score = bars.select(pl.col('bucket').alias('open_us'), 'open', 'close', 'high', 'low', 'volume')
        warm = window['warmup_4h'].filter(pl.col('symbol') == symbol).select(score.columns).sort('open_us')
        base.need(warm.height >= 240 and warm['open_us'][-1] + FOUR_HOURS == window['start'],
            'Complete official perpetual4h pre-score history, never interpolated daily/Spot candles')
        whole = pl.concat([warm, score], how='vertical').sort('open_us')
        stamps = whole['open_us'].to_numpy().astype(np.int64) + FOUR_HOURS
        base.need(np.all(np.diff(stamps) == FOUR_HOURS), 'Contiguous fixed4h causal history')
        values = whole.select('open', 'close', 'high', 'low', 'volume').to_numpy()
        base.need(np.isfinite(values).all() and np.all(values[:, :4] > 0) and np.all(values[:, 4] >= 0),
            'Observed finite OHLCV only')
        daily = window['daily'].filter(pl.col('symbol') == symbol).sort('close_us')
        context[symbol] = dict(stamps=stamps, available=stamps.copy(),
            candles=np.column_stack((whole['open_us'].to_numpy()/1000, values)),
            daily_stamps=daily['close_us'].to_numpy(), daily_available=daily['available_us'].to_numpy(),
            daily_close=daily['close'].to_numpy())
    return context


def decision(bridge, histories, stamp):
    candles, availability, returns, daily_ends = {}, {}, [], []
    for symbol in base.SYMBOLS:
        c = histories[symbol]
        i = int(np.searchsorted(c['stamps'], stamp, side='right') - 1)
        base.need(i >= 239 and c['stamps'][i] == stamp, 'Exactly240 completed4h observations before decision')
        candles[symbol] = c['candles'][i-239:i+1]
        availability[symbol] = c['available'][i-239:i+1]
        d = int(np.searchsorted(c['daily_stamps'], stamp, side='right') - 1)
        base.need(d >= 30 and np.all(c['daily_available'][d-30:d+1] <= stamp),
            'Thirty actual past daily returns available; no future covariance')
        close = c['daily_close'][d-30:d+1]
        returns.append(np.diff(close)/close[:-1]); daily_ends.append(int(c['daily_stamps'][d]))
    base.need(len(set(daily_ends)) == 1, 'Common risk observation cutoff')
    bridge.on_bar_close(int(stamp), candles, np.column_stack(returns), daily_ends[0],
        availability_us_by_symbol=availability)


def _nested(node, name, replacement, changes):
    matches = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n.name == name]
    base.need(len(matches) == 1, 'One pinned nested callback '+name)
    old = private.native._digest(matches[0]); matches[0].body = ast.parse(replacement).body
    changes.append(dict(change='D047_EVENT_BRIDGE_'+name, matches=1,
        old_AST_sha256=old, new_AST_sha256=private.native._digest(matches[0])))


ATTEMPT_BODY = """
nonlocal first_entry,completion,stop
event=int(open_us)+1
mids={s:D(str(window['market'][s]['open'][index])) for s in SYMBOLS}
capacity={s:D(str(window['market'][s]['quote_volume'][index-1]))*D('.001')/mids[s]
          if index else ZERO for s in SYMBOLS}
due=bridge.due_orders(int(open_us),mids)
due=sorted(due,key=lambda o:(not o['reduce_only'],SYMBOLS.index(o['symbol']),o['id']))
for order in due:
    s=order['symbol'];before=len(account.trades)
    receipt=account.execute_fill(s,order['side'],order['quantity'],event,order['signal_us'],
        order['id']+':'+str(order['attempts']),execution_mid_price=mids[s],
        quote_available_us=int(open_us),available_quantity=capacity[s],reduce_only=order['reduce_only'])
    used=sum((D(r['decimal_strings']['quantity']) for r in account.trades[before:]),ZERO)
    capacity[s]=max(ZERO,capacity[s]-used)
    bridge.on_fill(order['id'],receipt)
    bridge.note_attempt(order['id'],event,receipt)
    if used>0 and order['kind']=='RISK_REDUCTION':
        matching=[r for r in reversed(breaches) if r['signal_us']==order['signal_us']]
        if matching and 'first_reduction_fill_us' not in matching[0]:
            matching[0].update(first_reduction_fill_us=event,reduction_latency_us=event-order['signal_us'])
    if account.trades[before:] and first_entry is None:first_entry=event
    if receipt['status']!='FILLED':
        rejections.append(dict(symbol=s,event_us=event,order_id=order['id'],kind=order['kind'],
            **{k:v for k,v in receipt.items() if k!='fills'}))
    observe(event,'AFTER_TURTLE_'+order['kind'])
    if account.status in HALTS:
        completion='NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED';stop=event;return
    if bridge.halt_reason:
        completion=bridge.halt_reason;stop=event;return
"""


def adapted_simulate():
    receipt = []
    def transform(node, changes):
        patch = lambda before, after, label: private.native._replace(node, changes, label, before, after)
        prep = """decisions=np.arange(start,end,DAY,dtype=np.int64)
targets,meta=strategy.fixed_targets(window['daily'],decisions,mode)
need(targets.height==2*len(decisions),'Complete same daily target calendar')
weights={int(t):dict(zip(SYMBOLS,targets.filter(pl.col('available_us')==t)
        .sort('symbol')['target_weight'].to_list(),strict=True)) for t in decisions}
daily_prices={s:dict(zip(window['daily'].filter(pl.col('symbol')==s)['close_us'].to_list(),
    window['daily'].filter(pl.col('symbol')==s)['close'].to_list(),strict=True)) for s in SYMBOLS}"""
        node = patch(prep, 'histories=prepare_signal_context(window)', 'CAUSAL4H_CONTEXT_NO_PREGENERATED_POSITION_STATE')
        node = patch('account=USDTLinearPerpetualAccount(config)',
            'account=USDTLinearPerpetualAccount(config)\nbridge=strategy.TurtlePerpetualBridge(account)', 'ONE_SHARED_ORIGINAL_ACCOUNT_WITH_STRATEGY_BRIDGE')
        _nested(node, 'schedule', 'bridge.force_targets(target,int(signal),kind)', changes)
        _nested(node, 'attempt', ATTEMPT_BODY, changes)
        node = patch("if any(o['kind']=='RISK_REDUCTION' for o in pending.values()):return",
            "if any(o and o['kind'] in ('RISK_REDUCTION','STOP','EXIT','TERMINAL') for o in bridge.summary_orders().values()):return",
            'DONT_REPLACE_ACTIVE_REDUCE_ONLY_STOP_WITH_ALPHA_OR_CAP')
        daily = """if t in weights and not terminal:
    nav=account.nav()
    desired={s:D(str(weights[t][s]))*D('.99')*nav/D(str(daily_prices[s][t])) for s in SYMBOLS}
    if account.status=='ACTIVE':schedule(desired,t,'DAILY_TARGET')"""
        node = patch(daily, "if t%FOUR_HOURS==0 and not terminal:\n    decision(bridge,histories,t)",
            'ACTUAL_CALLBACK_STATE_AT_CLOSED4H_DECISION')
        node = patch("risk_schedule(close)\nnav=account.nav()", "risk_schedule(close)\nif not terminal:\n    bridge.observe_stop(close,{s:dict(open_us=t,available_us=close,high=window['market'][s]['high'][i],low=window['market'][s]['low'][i]) for s in SYMBOLS})\nnav=account.nav()",
            'OBSERVE_KNOWN_MINUTE_STOP_WITHOUT_INTRABAR_BACKFILL')
        node = private.literal(node, changes, 'REPORT_ACTUAL_PENDING_ORDER_STATE',
            "{s:{**r,'target':str(r['target'])} for s,r in pending.items()}", 'bridge.summary_orders()', 1)
        for name, expression in [('targets', 'bridge.targets_frame()'), ('target_meta', 'bridge.meta()')]:
            fields = [n for n in ast.walk(node) if isinstance(n, ast.keyword) and n.arg == name]
            base.need(len(fields) == 1 and isinstance(fields[0].value, ast.Name)
                and fields[0].value.id == ('targets' if name == 'targets' else 'meta'),
                'One exact output keyword '+name)
            fields[0].value = ast.parse(expression, mode='eval').body
            changes.append(dict(change='SAVE_ACTUAL_EVENT_STATE_'+name, matches=1))
        return node
    env = private.namespace(base, ['simulate'], dict(strategy=strategy, FOUR_HOURS=FOUR_HOURS,
        prepare_signal_context=prepare_signal_context, decision=decision), receipt, transform)
    return env['simulate'], receipt


def load_window(manifest, window, warmup):
    """Private reader adds actual OHLCV, then exact accepted warmup files."""
    derivation = []
    def transform(node, changes):
        node = private.native._replace(node, changes, 'OBSERVED_MINUTE_OHLCV_FOR4H_AND_STOP',
            "selected=traded.select('open','close','quote_volume').to_numpy()",
            "selected=traded.select('open','close','quote_volume','high','low','volume').to_numpy()")
        return private.native._replace(node, changes, 'PASS_REAL_HIGH_LOW_VOLUME_NOT_PROXY_VALUES',
            "market[symbol]=dict(open=selected[:,0],close=selected[:,1],quote_volume=selected[:,2],mark=mark_values)",
            "market[symbol]=dict(open=selected[:,0],close=selected[:,1],quote_volume=selected[:,2],mark=mark_values,high=selected[:,3],low=selected[:,4],volume=selected[:,5])")
    reader = private.namespace(base, ['load_window'], dict(sha=sha), derivation, transform)['load_window']
    result = reader(manifest, window)
    frames = []
    for item in warmup['files']:
        path = Path(item['normalized_path'])
        base.need(path.is_relative_to(STATE) and not path.is_symlink()
            and path.stat().st_size == item['normalized_bytes'] and sha(path) == item['normalized_sha256'],
            'Accepted4h warmup exact normalized bytes')
        frames.append(pl.read_parquet(path))
        result['input_proofs'].append(dict(id=item['source_id'], path=str(path),
            sha256=item['normalized_sha256'], bytes=item['normalized_bytes'], role='OFFICIAL_4H_WARMUP_ONLY'))
    result['warmup_4h'] = pl.concat(frames).sort(['symbol', 'open_us'])
    result['reader_derivation'] = derivation
    return result


def context(spec):
    base.need(spec['contract_id'] == CONTRACT and spec['rules'] == RULES
        and spec['period_ids'] == ['303D'] and spec['cost_scenarios'] == base.COSTS
        and spec['unit_scenarios'] == base.UNITS, 'Exactly one predeclared four-condition Turtle challenge')
    simulation, derivation = adapted_simulate()
    warmup = base.relative_proof(spec['warmup_acceptance'])
    base.need(warmup['status'] == 'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY'
        and warmup['source_only'] is True, 'Source-only warmup cannot grant investment qualification')
    def reader(manifest, window):
        return load_window(manifest, window, warmup)
    def transform(node, changes):
        node = private.literal(node, changes, 'ONE303_PERIOD_CLI', "['122D','90D','BOTH']", "['303D','BOTH']", 1)
        node = private.literal(node, changes, 'ONE303_PERIOD_METADATA', "['122D','90D']", "['303D']", 1)
        node = private.literal(node, changes, 'FOUR_ACTUAL_TURTLE_ACCOUNTS', 'len(selected)*12', 'len(selected)*4', 1)
        counts = [n for n in ast.walk(node) if isinstance(n, ast.keyword) and n.arg == 'planned_constant_cash_baselines']
        base.need(len(counts) == 1, 'One original cash count keyword')
        counts[0].value = ast.Constant(0)
        changes.append(dict(change='NO_NEW_CASH_REPLAY', matches=1))
        node = private.native._replace(node, changes, 'LABEL_DISTINCT_PUBLIC_STRATEGY',
            "result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))",
            "saved['summary']['strategy_id']=STRATEGY_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,selector_mode=mode,strategy_id=STRATEGY_ID,cost_id=cost['id'],unit_id=unit['id'],**saved))")
        node = private.literal(node, changes, 'HONEST_TURTLE_EVENT_METADATA',
            "'ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED'", "'ORIGINAL_TURTLE4H_HOOKS_CALLBACKS_DELAYED_STOP'", 1)
        node = private.literal(node, changes, 'FIXED_CHALLENGER_BEFORE_NEW_PNL',
            "'Same product and capital four-direction comparison'",
            "'One fixed public Turtle4h callback challenger to saved SMA and HOLD controls; no search'", 1)
        return private.native._replace(node, changes, 'PRESERVE_EXACT_EVENT_BRIDGE_DERIVATION',
            "write(run/'RUN_BINDING.json',binding)", "binding['event_bridge_derivation']=PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
    # Private LOCK is verified separately by a streaming hash; never in a Git/registry source map.
    base.need(sha(ROOT/'state/dataset_lock.json') == '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d',
        'Private lock unchanged, body never parsed')
    base.need('state/dataset_lock.json' not in spec['frozen_sources'], 'Private lock excluded from exported maps')
    env = private.namespace(base, ['main'], dict(__file__=__file__, CONTRACT=CONTRACT, STATUS=STATUS,
        MANIFEST_STATUS=parent.MANIFEST_STATUS, RULES=RULES, strategy=SimpleNamespace(MODES=MODES),
        sha=sha, append_event=compact_append_event, relative_proof=parent.relative_proof, load_window=reader, simulate=simulation,
        PRIVATE_DERIVATION=derivation, STRATEGY_ID=STRATEGY_ID), derivation, transform)
    return dict(main=env['main'], simulate=simulation, derivation=derivation)


def main():
    parser = argparse.ArgumentParser(add_help=False); parser.add_argument('--protocol', type=Path, required=True)
    args, _ = parser.parse_known_args()
    context(base.small(args.protocol))['main']()


if __name__ == '__main__':
    main()
