import hashlib,json
from pathlib import Path
import pytest
from modules.transformer_v3.wallet import registered_protocol


def test_new_research_protocol_cannot_borrow_old_identity(tmp_path):
    p=tmp_path/'protocol.json';p.write_text(json.dumps({'data_manifest_sha256':'a'*64}))
    with pytest.raises(ValueError,match='do not match'):
        registered_protocol([{'protocol_sha256':'b'*64}],p)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert registered_protocol([{'protocol_sha256':digest}],p)['data_manifest_sha256']=='a'*64
    p.write_text(json.dumps({'data_manifest_sha256':'c'*64}))
    with pytest.raises(ValueError,match='do not match'):
        registered_protocol([{'protocol_sha256':digest}],p)


def test_default_v3_protocol_still_bound_to_original_path():
    p=Path(__file__).resolve().parents[1]/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    expected=json.loads(p.read_text());digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert registered_protocol([{'protocol_sha256':digest}])==expected
