"""D047 TLS-compatible official raw code transport; reuse exact V1 source body.
No registry append, numeric kernel call, custom proxy or certificate bypass.
"""
import ast,base64,hashlib,json,subprocess
from pathlib import Path

ROOT=Path('/mnt/d/codex/coin')
BASE='docs/archive/TURTLE_RULES_OFFICIAL_SOURCE_FETCH_20261003_V1.py'
BASE_SHA='ad17b3e350342870aaa18ea2b3aa13cec15b6f9f00b2751961d9d242a07e4190'
PRE_SHA='6dfe5938faa53debeb0b4b3878d9f5a9deadf4c789d7a9b4b49121523e00e70d'
TRANSPORT='docs/archive/TURTLE_RULES_OFFICIAL_SOURCE_TRANSPORT_20261003_V2.ps1'
TRANSPORT_SHA='df904e17d8ee50ddc47f43deb411a9b8919c0c3b8ff035f165a2dfcc038052ad'
WINDOWS_RECEIPTS=[]

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def windows_fetch(url,maximum_bytes):
    spec=json.loads((ROOT/'third_party/jesse_example_turtle_rules/DOWNLOAD_PREBIND_20261003_V2.json').read_bytes())
    selected=[item for item in spec['source_files'] if item['url']==url and item['maximum_bytes']==maximum_bytes]
    assert len(selected)==1 and digest(ROOT/TRANSPORT)==TRANSPORT_SHA
    name='Turtle' if selected[0]['local_name']=='turtle_rules_original.py' else 'ATR'
    reply=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-File','D:/codex/coin/'+TRANSPORT,'-SourceName',name],timeout=60)
    assert len(reply)<=131072
    receipt=json.loads(reply.decode('utf-8-sig'));raw=base64.b64decode(receipt.pop('body_base64'),validate=True)
    assert receipt['url']==url and receipt['status_code']==200 and 0<len(raw)<=maximum_bytes and receipt['bytes']==len(raw)
    assert receipt['sha256']==hashlib.sha256(raw).hexdigest()
    WINDOWS_RECEIPTS.append(receipt)
    return raw

assert digest(ROOT/BASE)==BASE_SHA
tree=ast.parse((ROOT/BASE).read_bytes())
replacements={
    'DOWNLOAD_PREBIND_20261003_V1.json':'DOWNLOAD_PREBIND_20261003_V2.json',
    '9698ec8417378ace850eb334fa1d96a2e5e177f6475722cef921ac9b2929667c':PRE_SHA,
    'docs/archive/TURTLE_RULES_OFFICIAL_SOURCE_FETCH_20261003_V1.py':'docs/archive/TURTLE_RULES_OFFICIAL_SOURCE_FETCH_20261003_V2.py',
    'd047-turtle-official-source-20261003-v1':'d047-turtle-official-source-20261003-v2',
    'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V1.json':'reports/fast_research/TURTLE_RULES_OFFICIAL_SOURCE_PROVENANCE_20261003_V2.json',
}
counts={key:0 for key in replacements}
for node in ast.walk(tree):
    if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in replacements:
        counts[node.value]+=1;node.value=replacements[node.value]
assert all(value==1 for value in counts.values())
calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Subscript)
    and isinstance(node.func.value,ast.Name) and node.func.value.id=='ns' and isinstance(node.func.slice,ast.Constant) and node.func.slice.value=='fetch']
assert len(calls)==1;calls[0].func=ast.Name(id='windows_fetch',ctx=ast.Load())
report=[node for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='report' for target in node.targets)]
assert len(report)==1
report[0].value.keywords.append(ast.keyword(arg='native_fetch_receipts',value=ast.Name(id='WINDOWS_RECEIPTS',ctx=ast.Load())))
namespace=dict(__name__='__main__',__file__=__file__,windows_fetch=windows_fetch,WINDOWS_RECEIPTS=WINDOWS_RECEIPTS)
exec(compile(ast.fix_missing_locations(tree),str(ROOT/BASE),'exec'),namespace)
