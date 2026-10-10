import json
from pathlib import Path
import numpy as np
import torch
from modules.temporal_scaler_refit.stage import frozen_state
from modules.temporal_scaler_refit.data import inputs
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_two_expert.checkpoint import model_identity,_rng_state
from modules.temporal_episode_weighting_v2.stage import tree_identity
s=Path('../coin_single_state');out=s/'training-request-diagnostic';out.mkdir();torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
m,o,sc,saved,t=frozen_state(s,s/'early2021',s/'scaler-refit');train,_,data,_=inputs(s,s/'early2021');before=(model_identity(m),tree_identity(o.state_dict()),tree_identity(_rng_state()));m.eval();records=[];arrays={}
with torch.no_grad():
 for k,e in enumerate(train):
  p=predict_episode(m,e).numpy();active=len(p)-1;assert p.shape==(len(e.contexts),6) and np.isfinite(p).all();arrays[f'requests_{k}']=p;arrays[f'decision_us_{k}']=e.windows.decision_us
  records.append({'wallet_id':e.wallet_id,'start_us':e.start_us,'end_us':e.end_us,'active_intervals':active,'request_mean_active':p[:active].mean(0).tolist(),'short_request_min_max_active':[float(p[:active,5].min()),float(p[:active,5].max())],'short_eligible_active':int(e.eligible[:active,5].sum()),'model_identity':model_identity(m)})
assert before==(model_identity(m),tree_identity(o.state_dict()),tree_identity(_rng_state()));np.savez_compressed(out/'REQUESTS.npz',**arrays);result={'status':'SIX_TRAINING_REQUESTS_ONLY','wallets':records,'optimizer_updates':0,'wallet_replays':0,'inferences':6,'no_new_evaluation':True,'model_Adam_RNG_unchanged':True};(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
