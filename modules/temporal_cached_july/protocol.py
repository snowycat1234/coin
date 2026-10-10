"""Additional cache adapter identity gate; all original economic gates retained."""
import json
from pathlib import Path
from modules.temporal_added_history_july import protocol as original
from modules.temporal_added_history_july.protocol import CLASSIFICATION, MODELS, ORDER, SCALER, ROOT
from modules.temporal_two_expert.exact import sha
DEST=ROOT/'research/temporal-cached-july-20261010'
protocol=original.protocol

def sources():
    return {**original.sources(),**{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'modules/temporal_cached_july').glob('*.py'))}}

def public_gate(publication):
    original_ready,public=original.public_gate(publication)
    path=DEST/'PRESCORE.json'
    assert any(row['path']==str(path.relative_to(ROOT)) and row['SHA256']==sha(path) for row in public['files'])
    ready=json.loads(path.read_text())
    assert ready['sources']==sources() and ready['protocol']==original_ready['protocol']
    assert ready['models']==original_ready['models'] and ready['input_binding']==original_ready['input_binding']
    return ready,public
