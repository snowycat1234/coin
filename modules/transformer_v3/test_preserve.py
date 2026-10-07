import pytest
from .preserve import seal,verify

def test_protected_snapshot_detects_mutation_and_deduplicates(tmp_path):
    p=tmp_path/'evidence';p.write_text('original')
    entries=seal([p,p]);assert len(entries)==1;verify(entries)
    p.write_text('mutated')
    with pytest.raises(ValueError,match='changed'):verify(entries)
