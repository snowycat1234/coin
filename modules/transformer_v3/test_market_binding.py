import json
import pytest
from .market_binding import prepare_binding,verify_binding,market_paths,digest_file
from modules.transformer_v2.train import sha

def test_native_market_manifest_binds_bytes_and_detects_mutation_after_cached_verify(tmp_path):
    work=tmp_path/'work';state=tmp_path/'state';window=dict(id='w',start=1754006400000000,end=1754092800000000)
    paths=market_paths(work,window,['BTCUSDT'])
    for p in paths:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original source bytes')
    manifest=work/'reports/DATASET_MANIFEST.json';manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(dict(artifacts=[dict(relative_path=str(p.relative_to(work)),sha256=digest_file(p)) for p in paths])))
    path=prepare_binding(state,window,['BTCUSDT'],work,expected_manifest_sha256=sha(manifest))
    verify_binding(path,sha(path));paths[-1].write_bytes(b'mutated source bytes!')
    with pytest.raises(ValueError,match='source changed'):verify_binding(path,sha(path))

def test_absent_inactive_month_cannot_be_silently_added_after_freeze(tmp_path):
    work=tmp_path/'work';state=tmp_path/'state';window=dict(id='w',start=1754006400000000,end=1754092800000000)
    paths=market_paths(work,window,['BTCUSDT']);present=paths[:-1]
    for p in present:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'x')
    manifest=work/'reports/DATASET_MANIFEST.json';manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(dict(artifacts=[dict(relative_path=str(p.relative_to(work)),sha256=digest_file(p)) for p in present])))
    path=prepare_binding(state,window,['BTCUSDT'],work,expected_manifest_sha256=sha(manifest))
    paths[-1].parent.mkdir(parents=True,exist_ok=True);paths[-1].write_bytes(b'x')
    with pytest.raises(ValueError,match='availability changed'):verify_binding(path,sha(path))
