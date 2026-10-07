import pytest
import hashlib,json,subprocess
from pathlib import Path
from scripts.research.run_public_momentum import verify_legacy_sources

def test_legacy_allowlist_cannot_accept_economic_or_liquidation_changes():
    old={'meta':'old','funding':'same'};current={'meta':'new','funding':'same'}
    compatibility={'meta':{'old':'old','current':'new'}}
    assert verify_legacy_sources(old,current,compatibility,0)==['meta']
    with pytest.raises(ValueError,match='zero-liquidation'):verify_legacy_sources(old,current,compatibility,1)
    with pytest.raises(ValueError,match='Unreviewed'):verify_legacy_sources(old,dict(current,funding='changed'),compatibility,0)
    with pytest.raises(ValueError,match='set changed'):verify_legacy_sources(old,dict(current,extra='added'),compatibility,0)

def test_real_protocol_compatibility_hashes_match_raw_old_and_current_bytes():
    root=Path(__file__).resolve().parents[1]
    p=json.loads((root/'protocols/PUBLIC_CROSS_SECTION_MOMENTUM_20261008.json').read_text())
    for name,pair in p['legacy_source_compatibility'].items():
        for key in ('old','current'):assert len(pair[key])==64 and set(pair[key])<=set('0123456789abcdef')
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(root),'show','d8c47a1:'+name])).hexdigest()==pair['old']
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pair['current']
