import pytest
from .locked_gate import require_release
from .train import atomic

def test_locked_read_requires_explicit_one_run_release(tmp_path):
    with pytest.raises(RuntimeError,match='refused'):require_release(tmp_path,'abc')
    atomic(tmp_path/'LOCKED_READ_AUTHORIZATION.json',dict(status='AUTHORIZED_ONE_LOCKED_EXPERIMENT',protocol_sha256='abc',formal_result_limit=1,
        range=['2026-03-01','2026-08-31']))
    assert require_release(tmp_path,'abc')['formal_result_limit']==1
    with pytest.raises(AssertionError):require_release(tmp_path,'other')
