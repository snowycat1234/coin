from types import SimpleNamespace
import pytest
from .development_exposure import prepare
from .train import atomic

def test_exposure_controls_require_the_frozen_candidate_before_reading_data(tmp_path):
    args=SimpleNamespace(state=tmp_path)
    with pytest.raises(FileNotFoundError):prepare(args)
    assert not (tmp_path/'development-exposure').exists()
    atomic(tmp_path/'LOCKED_CANDIDATE_FREEZE.json',dict(locked_read=True,protocol_sha256='invalid'))
    with pytest.raises(AssertionError):prepare(args)
    assert not (tmp_path/'development-exposure').exists()
