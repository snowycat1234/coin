import copy,json
from pathlib import Path
import numpy as np
import pytest
from . import data
from modules.temporal_added_history_july.protocol import ROOT

def test_cached_inputs_match_original_prescore():
    state=Path(__file__).resolve().parents[3]/'coin_single_state'
    e,_,_,b,_=data.inputs(state)
    original=json.loads((ROOT/'research/temporal-added-history-july-20261010/PRESCORE.json').read_text())
    assert b==original['input_binding']
    assert e.windows.values.shape==(63,64,5,24)
    assert np.all(e.target_available_us <= e.windows.decision_us[:,None])
    assert np.all(e.expert_input_available_us <= e.windows.decision_us[:,None])

def test_cache_mutation_rejected(tmp_path,monkeypatch):
    import shutil
    copied=tmp_path/'results';shutil.copytree(data.OLD,copied)
    with (copied/'CURRENT_CONTEXT.npz').open('ab') as f:f.write(b'changed')
    # Avoid changing frozen public paths: substitute only the test's temp folder.
    monkeypatch.setattr(data,'OLD',copied)
    monkeypatch.setattr(data,'ROOT',tmp_path)
    real=data.commit_bytes
    monkeypatch.setattr(data,'commit_bytes',lambda c,n: real(c,'research/temporal-july-frozen-transfer-20261010/'+n))
    with pytest.raises(AssertionError):data.inputs(tmp_path)
