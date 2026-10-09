"""Actual 2023 context binding failures; no account advancement or model load."""
import json,sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parents[1]/'research/recover-frozen-runner-20261009'
sys.path.insert(0,str(HERE))
import evaluate_transfer63 as transfer


def packet(tmp_path,change=None):
    source=HERE/'prequential2023/FOLD_20230703/CANONICAL_CONTEXTS63.npz'
    with np.load(source,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    if change:change(a)
    path=tmp_path/'CANONICAL_CONTEXTS63.npz';np.savez_compressed(path,**a)
    contract=tmp_path/'ADAPTER_CONTRACT.json';contract.write_text(json.dumps(dict(canonical_context_SHA256=transfer.base.frozen.sha(path))))
    return path,contract


def test_real_july_context_keeps_original_slots(tmp_path):
    _,contract=packet(tmp_path);c=transfer.contexts(contract)
    assert c['expert_targets'].shape==(63,6,5)
    assert not c['expert_eligible'][:,[2,3]].any()
    assert not c['expert_targets'][:,[2,3]].any()


def test_changed_covariance_bytes_fail_binding(tmp_path):
    path,contract=packet(tmp_path)
    with np.load(path,allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    a['past_returns30'][0,0,0]+=1;np.savez_compressed(path,**a)
    with pytest.raises(ValueError,match='context differs'):transfer.contexts(contract)


def test_reordered_context_names_fail_even_with_new_hash(tmp_path):
    _,contract=packet(tmp_path,lambda a:a.update(expert_order=a['expert_order'][::-1]))
    with pytest.raises(ValueError,match='slot names'):transfer.contexts(contract)


def test_wrong_declared_fold_is_not_calendar_fallback(tmp_path):
    contract=tmp_path/'ADAPTER_CONTRACT.json';contract.write_text(json.dumps(dict(fold='FOLD_20230703',calendar=transfer.FOLDS['FOLD_20231002'])))
    with pytest.raises(ValueError,match='no fallback'):transfer.readiness(tmp_path,contract)
