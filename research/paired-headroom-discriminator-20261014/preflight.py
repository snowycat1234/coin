"""Source hashes/AST plus synthetic fixture only. No historical input argument."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PURE_FILES=('paired_buffer.py','run_toy.py')
FORBIDDEN_IMPORTS=('quant','scripts','polars','pandas','requests','urllib','http','socket')
FORBIDDEN_CALLS=('load','read_bytes','read_text','open','execute_fill','apply_funding',
                 'update_marks','advance_day','from_snapshot','schedule','attempt')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pins=json.loads((HERE/'SOURCE_PINS.json').read_text())
    assert sha(HERE/'vendor/headroom_buffer.py')==pins['original_files_SHA256']['headroom_buffer.py']
    original_root=HERE.parent/pins['read_source_root']
    assert sha(original_root/'FROZEN_CODE.json')==pins['frozen_manifest_SHA256']
    for name,expected in pins['original_files_SHA256'].items():
        assert sha(original_root/name)==expected,('original source changed',name)
    for name,expected in pins['executor_dependencies_SHA256'].items():
        assert sha(original_root/'runtime_dependencies'/name)==expected,('executor source changed',name)
    terminal=pins['terminal60_source']
    assert sha(HERE.parent/terminal['path'])==terminal['SHA256']
    manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text())
    for name,expected in manifest['files_SHA256'].items():
        assert sha(HERE/name)==expected,name
    for name in PURE_FILES:
        tree=ast.parse((HERE/name).read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
            if isinstance(node,ast.Call):
                called=ast.unparse(node.func).split('.')[-1]
                assert called not in FORBIDDEN_CALLS,(name,called)
        assert not any(x.split('.')[0] in FORBIDDEN_IMPORTS for x in imports),(name,imports)
    # Candidate execution starts only after source identities and AST checks.
    from run_toy import separated_extrema_toy
    toy=separated_extrema_toy()
    assert toy['original_independent_trigger'] and not toy['paired_trigger']
    print(json.dumps({'status':'PASS_SOURCE_PIN_AST_AND_SYNTHETIC_DISCRIMINATOR',
                      'source_manifest_SHA256':sha(HERE/'SOURCE_MANIFEST.json'),
                      'protocol_SHA256':sha(HERE/'PROTOCOL.json'),
                      'original_buffer_SHA256':sha(HERE/'vendor/headroom_buffer.py'),
                      'files_verified':len(manifest['files_SHA256']),
                      'original_source_and_executor_files_verified':len(pins['original_files_SHA256'])+len(pins['executor_dependencies_SHA256'])+2,
                      'toy':toy,'historical_array_reads':0,'historical_wallets':0,
                      'financial_advances':0,'fits':0,'market_requests':0,
                      'historical_GO':False},indent=2,sort_keys=True))


if __name__=='__main__':main()
