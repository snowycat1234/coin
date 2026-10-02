import hashlib
import json
import subprocess
import sys
from pathlib import Path
root=Path('/mnt/d/codex/coin')
sys.path.insert(0,str(root))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda path: hashlib.sha256((root/path).read_bytes()).hexdigest()
protocol=json.loads((root/'protocols/FEATURE_CONTRACT_V8.json').read_text())
e=dict.fromkeys(FIELDS)
e.update(experiment_id='v8-fixed-features-synthetic-20261002-v1',event_id='v8-fixed-features-synthetic-20261002-v1:START',event_type='OPERATIONAL_START',
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_manifest_hash=sha('tests/test_v8_features.py'),data_manifest_scope='invented synthetic fixture/test byte snapshot; no market data',
 protocol_hash=sha('protocols/FEATURE_CONTRACT_V8.json'),feature_set=protocol['feature_names'],labels='NONE',model_family='NONE',hyperparameters={},seed=None,
 thresholds='NO_FEATURE_SELECTION_OR_TRADING_THRESHOLDS',cost_assumptions='NOT_EVALUATED',all_folds=[],success_failure='RUNNING',
 reason_for_next_experiment='Validate the jointly fixed V8 feature information set before outcome access; no model selection',result_influenced_later_choice=False,
 source_hashes={p:sha(p) for p in ['scripts/research_v8/features.py','tests/test_v8_features.py','src/quant/research_fast/dataset.py']},
 environment_hash=sha('environments/v8/uv.lock'),locked_consumed=False,models_fit=0,
 exact_command="bash scripts/with_task_progress.sh --title 'V8 固定共同特征合成因果验收' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -m pytest tests/test_v8_features.py -q --basetemp=/home/xflops/coin-state/test-v8-fixed-features-20261002-v1 -o cache_dir=/home/xflops/coin-state/test-v8-fixed-features-20261002-v1-cache --junitxml=reports/fast_research/V8_FIXED_FEATURE_TESTS_20261002_V1.xml")
record=append_event(root/'reports/experiment_registry.jsonl',e)
with (root/'reports/fast_research/V8_FIXED_FEATURE_START_20261002_V1.json').open('x') as writer:
 json.dump(record,writer,indent=2);writer.write('\n')
print(json.dumps({'record_sha256':record['record_sha256'],'status':record['success_failure']}))
