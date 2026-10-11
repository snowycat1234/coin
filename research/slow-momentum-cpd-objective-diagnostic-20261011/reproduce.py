"""Replay public saved-policy arithmetic only; no external model binary needed."""
import argparse
import json
from pathlib import Path

from modules.slow_momentum_cpd.cost_feasibility import POLICIES, read_saved, sha, write_json
from modules.slow_momentum_cpd.objective_diagnostic import (
    EXPERIMENT, read_vol_from_source, turnover_attribution,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
saved = json.loads((EXPERIMENT / 'results/RESULT.json').read_text())
source = EXPERIMENT.parents[1] / 'modules/slow_momentum_cpd/objective_diagnostic.py'
if sha(source.read_bytes()) != saved['executing_source_sha256']:
    raise ValueError('Executed diagnostic source identity differs')
count = 0
for block, expected in zip(read_saved(2048), saved['blocks'], strict=True):
    if block['start'] != expected['start']:
        raise ValueError('Development block identity differs')
    vol = read_vol_from_source(block)
    for index, name in enumerate(POLICIES):
        actual = turnover_attribution(block['positions'][:, :, index], vol,
                                      block['eligible'], block['returns'])
        if actual != expected['policies'][name]:
            raise ValueError('Saved arithmetic replay differs: ' + block['start'] + '/' + name)
        count += 1
value = dict(status='EXACT_SAVED_ARITHMETIC_REPLAY_PASS',
             block_policy_metric_sets_verified=count, expected_metric_sets=24,
             saved_result_sha256=sha((EXPERIMENT / 'results/RESULT.json').read_bytes()),
             executing_source_sha256=sha(source.read_bytes()),
             replay_wrapper_sha256=sha(Path(__file__).read_bytes()),
             external_model_files_required=0, new_model_inferences=0,
             training_updates=0, wallets=0, new_policy_validation_queries=0,
             scope='Same published code and savedCSV arithmetic; not an independent native wallet audit')
write_json(args.output, value)
print(json.dumps(value))
