import pytest
from . import pipeline
from .train import atomic

def test_public_locked_omits_large_artifacts_and_unrelated_private_fields(tmp_path):
    result=dict(status='NOT_EVALUABLE_INCOMPLETE_LOCKED_CALENDAR',protocol_sha256='hash',cases=[],errors=[],private_field='must_not_publish',checkpoints=['huge'])
    atomic(tmp_path/'TRANSFORMER_V2_LOCKED_RESULTS.json',result)
    compact=pipeline.public_locked(result,tmp_path)
    assert 'private_field' not in compact and 'checkpoints' not in compact and compact['rows']==[]
    assert compact['source_full_results_sha256'] and compact['investment_state']=='NONE/CASH'

def test_publication_refuses_dirty_checkout_before_any_copy(tmp_path,monkeypatch):
    monkeypatch.setattr(pipeline,'git',lambda *args:' M unrelated_work.py')
    with pytest.raises(AssertionError,match='dirty checkout'):pipeline.publish(tmp_path,tmp_path/'state')
    assert not (tmp_path/'reports').exists()
