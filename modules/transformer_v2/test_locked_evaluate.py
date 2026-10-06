import numpy as np
from .locked_evaluate import baseline_weights
import pytest
from .locked_evaluate import permit_pre_account_engineering_repair
from .train import atomic,sha

def test_exposure_control_uses_each_past_target_budget_and_missing_mask():
    sma=np.array([[1.,-1.,1.,-1.,np.nan],[1.,1.,-1.,-1.,np.nan]])
    active=np.isfinite(sma);gross=np.array([.12,.4])
    hold=baseline_weights('BASE_HOLD',sma,active,gross)
    assert np.allclose(np.abs(hold).sum(1),gross) and (hold[:,4]==0).all()
    signed=baseline_weights('BASE_SMA200_SIGNED',sma,active,gross)
    assert np.allclose(np.abs(signed).sum(1),gross) and np.allclose(signed.sum(1),0.)
    assert np.isfinite(signed).all() and abs(signed).max()<=.3
    assert not baseline_weights('BASE_CASH',sma,active,gross).any()
    # Changing a later observed budget must not change an earlier decision.
    changed=baseline_weights('BASE_HOLD',sma,active,np.array([.12,.6]))
    assert np.array_equal(hold[0],changed[0])

def test_engineering_repair_refuses_any_account_outcome(tmp_path):
    atomic(tmp_path/'LOCKED_FORMAL_RUN.json',dict(source_sha256='old'))
    atomic(tmp_path/'LOCKED_FORMAL_FAILURE.json',dict(economic_results_read=False))
    proof=tmp_path/'proof.json';atomic(proof,dict(reason='ENGINEERING_PRE_ACCOUNT_ONLY',economic_results_read=False,model_ranking_read=False,
        failure_sha256=sha(tmp_path/'LOCKED_FORMAL_FAILURE.json'),previous_formal_marker_sha256=sha(tmp_path/'LOCKED_FORMAL_RUN.json')))
    atomic(tmp_path/'LOCKED_NATIVE_PROGRESS_RESULTS.json',dict(cases=[dict(net=1)]))
    with pytest.raises(AssertionError):permit_pre_account_engineering_repair(tmp_path,proof)
    assert (tmp_path/'LOCKED_FORMAL_RUN.json').exists()

def test_proven_pre_account_repair_preserves_first_attempt(tmp_path):
    atomic(tmp_path/'LOCKED_FORMAL_RUN.json',dict(source_sha256='old'))
    atomic(tmp_path/'LOCKED_FORMAL_FAILURE.json',dict(economic_results_read=False))
    proof=tmp_path/'proof.json';atomic(proof,dict(reason='ENGINEERING_PRE_ACCOUNT_ONLY',economic_results_read=False,model_ranking_read=False,
        failure_sha256=sha(tmp_path/'LOCKED_FORMAL_FAILURE.json'),previous_formal_marker_sha256=sha(tmp_path/'LOCKED_FORMAL_RUN.json')))
    permit_pre_account_engineering_repair(tmp_path,proof)
    assert (tmp_path/'LOCKED_FORMAL_PRE_ACCOUNT_ATTEMPT.json').exists() and (tmp_path/'LOCKED_FORMAL_PRE_ACCOUNT_FAILURE.json').exists()
