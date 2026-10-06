import json,subprocess,os
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
old_name='reports/GITHUB_FROZEN_EXPERT_LIBRARY_SOURCE_BINDING_20261006_V1.json'
new_name='reports/GITHUB_FROZEN_EXPERT_LIBRARY_SOURCE_BINDING_20261006_V2.json'
old=json.loads((ROOT/old_name).read_bytes())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==old['parent_commit']
changed={p:dict(previous=h,current=sha(ROOT/p)) for p,h in old['source_hashes'].items() if h!=sha(ROOT/p)}
assert set(changed)=={'docs/SHORT_SELECTION.md','docs/RESEARCH_DECISION_LOG.md','docs/RESEARCH_STATUS.md'}
paths=list(dict.fromkeys(old['selected_module_paths']+[new_name,'docs/archive/FROZEN_EXPERT_FINAL_DECISION_BINDER_SOURCE_20261006_V1.py']))
out=dict(old,selected_module_paths=paths,source_hashes={p:sha(ROOT/p) for p in paths if p!=new_name},
    correction_scope='Final append of observed oracle winner structure after initial close scan. Only three summary/decision documents changed; all financial evidence, accounting and original closure preserved, no account replay or new resource scan.',
    final_decision_document_changes=changed,initial_binding_sha256=sha(ROOT/old_name))
with (ROOT/new_name).open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False);f.write('\n')
(ROOT/'.cache/stage_selected_frozen_experts.ps1').write_text("$ErrorActionPreference = 'Stop'\n$paths = @(\n"+',\n'.join("'"+p+"'" for p in paths)+"\n)\n& git.exe -C 'D:/codex/coin' add -- $paths\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n")
print(json.dumps(dict(status='FINAL_OBSERVED_EXPERT_DECISION_BOUND_NO_ECONOMIC_REPLAY',task_id=os.environ['COIN_TASK_ID'],selected=len(paths))))
