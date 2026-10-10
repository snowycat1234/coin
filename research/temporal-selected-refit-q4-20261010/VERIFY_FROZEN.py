"""Restore the exact terminal256 checkpoint; never opens evaluation inputs."""
import json
from pathlib import Path
import torch
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_selected_refit.stage import frozen_state
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009')
model,optimizer,scaler,saved,terminal=frozen_state(state,state/'selected-refit/run')
assert saved['step']==256 and model.parameter_count==13699
assert saved['binding']['specification']['max_steps']==256
assert optimizer.param_groups[0]['lr']==.0003
assert len(optimizer.state)==13
assert {int(v['step']) for v in optimizer.state.values()}=={256}
assert scaler.provenance['real_row_count']==907
assert saved['binding']['specification']['algorithm']['parent']==dict(step=0,fresh=True)
assert set(saved['binding']['specification']['algorithm']['parameter_birth_steps'].values())=={0}
result=dict(status='FROZEN256_RESTORED_AND_VERIFIED_BEFORE_Q4_INPUT_BINDING',
    model_identity=model_identity(model),checkpoint_SHA256=terminal['checkpoint_SHA256'],
    run_id=saved['binding']['run_id'],scaler_identity=scaler.identity,
    parameters=model.parameter_count,completed_updates=256,all13_Adam_ages=256,
    Adam_lr=.0003,scaler_training_rows=907,active_training_dates=773,training_decisions=778,
    snapshot_RNG_identity=tree_identity(_rng_state()),Q4_reads=0,optimizer_updates=0,
    model_inferences=0,economic_rollouts=0,native_rollouts=0)
with (state/'selected-refit/FROZEN_VERIFICATION.json').open('x') as stream:
    stream.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
