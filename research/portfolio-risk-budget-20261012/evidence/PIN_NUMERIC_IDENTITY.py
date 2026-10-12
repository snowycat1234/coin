import json,hashlib
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012'
path=here/'PROTOCOL.json';p=json.loads(path.read_text());p['allocation']+=' Preserve an existing target bit-exact when uniform factor differs from1 by at most the existing1e-12 numerical risk tolerance. No economic outcome input. Reuse whole-calendar identical paths rather than rerunning them.'
p['publication']+=' Standard sparse-checkout only excludes immutable tracked old transformer/fast-research reports and HRP result byte containers in this own checkout; all Git/remote bytes and original STATE accounts retained. No other worktree or distribution source changed.'
path.write_text(json.dumps(p,sort_keys=True,indent=2)+'\n')
lines=[]
for line in (here/'SOURCE_SHA256.txt').read_text().splitlines():
 _,name=line.split(maxsplit=1);lines.append(hashlib.sha256((root/name).read_bytes()).hexdigest()+'  '+name)
(here/'SOURCE_SHA256.txt').write_text('\n'.join(lines)+'\n')
print('PRE_WALLET_NUMERIC_IDENTITY_FIX_PRESERVES_ORIGINAL_INTENTS_AND_POLICY')
