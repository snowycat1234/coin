import importlib,json,os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from modules.collector_research.validation import runtime

def test_windows_does_not_authorize_scientific_execution(monkeypatch):
    monkeypatch.setattr(runtime.platform,'system',lambda:'Windows')
    with pytest.raises(RuntimeError,match='requires Linux'):runtime.kernel_guard()

def test_server_flag_cannot_disable_wsl_limits(monkeypatch):
    monkeypatch.setenv('WSL_DISTRO_NAME','hpc_linux')
    monkeypatch.setitem(runtime.CONFIG,'resource_policy','server')
    with pytest.raises(RuntimeError,match='cannot bypass local WSL'):runtime.kernel_guard()

def configured(tmp_path):
    args=SimpleNamespace(collector_root=Path(__file__).resolve().parents[1],collector_work=tmp_path/'work',
        source_run=tmp_path/'original',run_dir=tmp_path/'validation',resource_policy='server',workers=1,
        minimum_days=30,publish_source_report=False,audit_device='cpu')
    (tmp_path/'work').mkdir(exist_ok=True)
    runtime.configure(args)

def test_gap_splits_data_and_short_windows_are_explicit(tmp_path):
    configured(tmp_path)
    from modules.collector_research.validation.audit import segments
    days=np.arange(100,dtype=np.int64)*runtime.DAY;good=np.ones(100,bool);good[41]=False
    selected,short=segments(days,good)
    assert selected==[(0,41*runtime.DAY,41),(42*runtime.DAY,100*runtime.DAY,58)] and not short
    selected,short=segments(days[:10],good[:10])
    assert selected==[] and short==[(0,10*runtime.DAY,10)]

def test_data_adapter_omits_only_actual_missing_minutes(tmp_path):
    configured(tmp_path)
    from modules.collector_research.validation.data import split_observed_minutes
    times=np.arange(10,dtype=np.int64)*runtime.MINUTE;observed=np.delete(times,[4,5])
    values=dict(times=observed,open=np.ones(8),close=np.ones(8),quote_volume=np.ones(8),mark=np.ones(8))
    blocks=list(split_observed_minutes(times,{'A':values}))
    assert np.array_equal(np.concatenate([b['times'] for b in blocks]),times)
    assert [int(t) for b in blocks if not b['market'] for t in b['times']]==[4*runtime.MINUTE,5*runtime.MINUTE]

def test_tampered_frozen_targets_refused(tmp_path):
    configured(tmp_path)
    from modules.collector_research.validation.data import target_series
    p=tmp_path/'fold1_TEST_targets.npz'
    np.savez(p,decision_us=np.array([1704153600000000],dtype=np.int64),weights=np.array([[.1]]),symbol_order=np.array(['A']))
    runtime.atomic(tmp_path/'TARGETS_MANIFEST.json',dict(files=[dict(name=p.name,sha256=runtime.sha(p))]))
    assert target_series(tmp_path,'TEST',['A'])[1][0,0]==.1
    p.write_bytes(p.read_bytes()+b'tampered')
    with pytest.raises(ValueError,match='artifact changed'):target_series(tmp_path,'TEST',['A'])
