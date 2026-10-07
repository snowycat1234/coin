import pytest
from scripts.research.run_public_momentum import verify_legacy_sources

def test_legacy_allowlist_cannot_accept_economic_or_liquidation_changes():
    old={'meta':'old','funding':'same'};current={'meta':'new','funding':'same'}
    compatibility={'meta':{'old':'old','current':'new'}}
    assert verify_legacy_sources(old,current,compatibility,0)==['meta']
    with pytest.raises(ValueError,match='zero-liquidation'):verify_legacy_sources(old,current,compatibility,1)
    with pytest.raises(ValueError,match='Unreviewed'):verify_legacy_sources(old,dict(current,funding='changed'),compatibility,0)
    with pytest.raises(ValueError,match='set changed'):verify_legacy_sources(old,dict(current,extra='added'),compatibility,0)
