from .assist_development import safe_to_launch
from .train import atomic

def test_assistance_never_takes_an_active_case_or_reaches_primary_buffer(tmp_path):
    task=dict(id='fixed/distant/tail');atomic(tmp_path/'economic-progress.json',dict(completed=10))
    assert safe_to_launch(tmp_path,task,600)
    base=tmp_path/'native'/task['id'];(base/'attempt-1').mkdir(parents=True)
    assert not safe_to_launch(tmp_path,task,600)
    other=dict(id='another/tail');atomic(tmp_path/'economic-progress.json',dict(completed=568))
    assert not safe_to_launch(tmp_path,other,600)
