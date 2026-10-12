"""New-year adapter checks, reusing prior financial/snapshot golden tests."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));spec=importlib.util.spec_from_file_location('cs2023_native',HERE/'native_run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_full2023_targets_are_exact_preexisting_rows_not_refitted():
    d,w,state,sha=m.saved_targets();assert len(d)==365 and d[0]==m.native.utc('2023-01-01') and d[-1]+m.DAY==m.native.utc('2024-01-01')
    with np.load(m.ROOT/'research/cs-continuous-economics-20261012/reference-result/TARGETS.npz',allow_pickle=False) as a:
        ids=np.searchsorted(a['decision_us'],d)
        for arm in m.ARMS:np.testing.assert_array_equal(w[arm],a[arm][ids]);assert np.abs(w[arm]).sum(1).max()<=.6+1e-12
    assert (state!='UNKNOWN').all()
def test_window_rejects_wrong_year_or_symbol_identity_before_account(tmp_path):
    base=dict(status='PASS_EXACT_FULL_2023_TRADE_MARK_FUND_SOURCE',calendar=[m.native.utc('2023-01-01'),m.native.utc('2024-01-01')],days=365,symbol_order=list(m.SYMBOLS));bad=dict(base,calendar=[m.native.utc('2022-01-01'),m.native.utc('2023-01-01')]);(tmp_path/'SOURCE_INDEX.json').write_text(json.dumps(bad))
    with pytest.raises(AssertionError):m.window(tmp_path)
    bad=dict(base,symbol_order=list(reversed(m.SYMBOLS)));(tmp_path/'SOURCE_INDEX.json').write_text(json.dumps(bad))
    with pytest.raises(AssertionError):m.window(tmp_path)
