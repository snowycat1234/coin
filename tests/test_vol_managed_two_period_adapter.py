"""UNRUN: one new D035 metadata/subset/period/endpoint routing case, no finance."""
from copy import deepcopy
import numpy as np
import polars as pl
import pytest
from scripts.investment import vol_managed_two_period_adapter as adapter

def test_two_fixed_vm_metadata_routes_and_exclusive_endpoint(monkeypatch):
    def forbidden_market_read(*args, **kwargs):
        raise AssertionError('This new synthetic route case must not read market arrays')
    monkeypatch.setattr(pl, 'read_parquet', forbidden_market_read)
    monkeypatch.setattr(pl, 'read_ipc', forbidden_market_read)
    old = adapter.parent.old
    before = (old.START, old.LOCKED, old.STRATEGIES, old.comparison_plan, old.verify_sources,
        old.research, adapter.parent.bulk.common, adapter.parent.v2.causal_vol_multiplier,
        adapter.parent.native.BEGIN_US, adapter.parent.native.END_US)
    for identifier, profile in adapter.PROFILES.items():
        inherited = adapter.parent_metadata(identifier); spec = deepcopy(inherited)
        for key in ('reused_reference_report','reused_reference_report_sha256','reused_target_inputs'):
            spec.pop(key, None)
        spec.update(strategy_ids=[adapter.STRATEGY], planned_ledgers=1,
            maximum_new_owned_bytes=140_000_000, maximum_wall_seconds=1800,
            namespace_parent_protocol=dict(path=profile['protocol'], sha256=profile['protocol_sha256']),
            source_scope=profile['source_scope'], source_calendar=profile['source_calendar'].copy(),
            source_days_per_symbol=profile['source_days'], reused_minute_input=adapter.input_reference(profile))
        spec['strategy_rules'] = deepcopy(adapter.VM_RULES)
        spec['costs'].update(spread_bps=[8], nominal_roundtrip_bps=[36])
        ns = adapter.context(spec); strategies, windows, planned = ns['comparison_plan'](spec)
        fold, lower, start, end = windows[0]
        assert fold == identifier and strategies == (adapter.STRATEGY,) and planned == 1
        assert (start-lower)//old.DAY_US == 31 and (end-start)//old.DAY_US == profile['days']
        assert ns['START'] == old.START and ns['LOCKED'] == old.LOCKED
        assert ns['source_scope'](spec)[2] == profile['source_days']
        aggregate = ns['period_aggregate']([], strategies)
        assert len(aggregate) == 1 and aggregate[0]['spread_bps'] == 8
        assert ns['verify_source_calendar'].__globals__['comparison_plan'] is ns['comparison_plan']
        assert ns['verify_sources'].__globals__['verify_source_calendar'] is ns['verify_source_calendar']
        assert ns['research'].__globals__['comparison_plan'] is ns['comparison_plan']
        assert ns['research'].__globals__['bulk_fixed_targets'] is adapter.parent.bulk
        assert adapter.parent.bulk.common.causal_vol_multiplier is adapter.parent.v2.causal_vol_multiplier
        assert ns['research'].__globals__['reused_minute_input'] is old.reused_minute_input
        changes = [c['change'] for f in ns['PERIOD_DERIVATION']['functions'] for c in f['changes']]
        assert len(changes) == 5 and len([name for name in changes if name != 'D035_METADATA_DERIVATION_ONLY']) == 4
        assert profile['derivative_rows'] == (profile['days']+31)*1440*2
        # A terminal execution/mark close may equal exclusive period end. The
        # unchanged signal view removes it without deleting execution input.
        minute = old.MINUTE_US; calendar = np.array([end-2*minute, end-minute], dtype=np.int64)
        assert np.array_equal(ns['benchmarks'].calendar_array(calendar), calendar)
        raw = pl.DataFrame(dict(symbol=['BTCUSDT','ETHUSDT']*3,
            close_us=np.repeat([end-2*minute,end-minute,end],2),
            available_us=np.repeat([end-2*minute,end-minute,end],2), close=[100.]*6))
        signals = ns['signal_close_view'](raw, calendar)
        assert signals.height == 4 and signals['close_us'].max() == end-minute
        assert raw.height == 6 and raw['close_us'].max() == end
        assert start+(profile['days']*1440-1)*minute == end-minute
        for key, value in [('strategy_ids',['CASH',adapter.STRATEGY]), ('planned_ledgers',3), ('strategy_rules',inherited['strategy_rules']),
            ('costs',{**spec['costs'],'spread_bps':[2,4,8],'nominal_roundtrip_bps':[30,32,36]}),
            ('reused_minute_input',{**spec['reused_minute_input'],'path':spec['reused_minute_input']['path'].replace('.parquet','.arrow')}),
            ('source_days_per_symbol',profile['days']+31),
            ('folds',[{**spec['folds'][0],'period_end_exclusive':'2026-03-02'}])]:
            # CONT122's source day count happens to equal its derivative span.
            if key == 'source_days_per_symbol' and value == profile['source_days']: continue
            with pytest.raises(ValueError): adapter.context({**spec,key:value})
    assert before == (old.START, old.LOCKED, old.STRATEGIES, old.comparison_plan, old.verify_sources,
        old.research, adapter.parent.bulk.common, adapter.parent.v2.causal_vol_multiplier,
        adapter.parent.native.BEGIN_US, adapter.parent.native.END_US)
    with pytest.raises(ValueError):
        adapter.parent.v2.calendar_array(np.array([adapter.parent.native.END_US], dtype=np.int64))
