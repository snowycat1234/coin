"""Once-only fixed2025 evaluation of both publicly frozen terminal models."""
from pathlib import Path
import argparse,json,csv
import numpy as np,torch
from modules.temporal_balanced_history.inputs import training,from_arrays
from modules.temporal_neutral_short.model import initialize
from modules.temporal_short_expansion.checkpoint import _validate_model_state,_validate_saved_optimizer,_validate_rng
from modules.temporal_short_expansion.adapter import compress,expand
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_july_transfer.evaluate import cost
from modules.temporal_two_expert.checkpoint import model_identity,_rng_state
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_two_expert.inputs import digest
from modules.temporal_two_expert.exact import sha

def run(state,output,publication):
 S=Path(state);R=S/'data-expansion';fit=S/'balanced-history';pub=json.loads(Path(publication).read_text());assert pub['status']=='BOTH_FIXED256_PUBLIC_VERIFIED';out=Path(output);out.mkdir(exist_ok=False)
 (out/'STARTED.json').write_text(json.dumps({'arms':['NATURAL','BALANCED'],'new_wallets':2,'fixed_2025_annual':True,'no_fits':True}));train,p,scaler,_=training(S);plan=json.loads((fit/'PLAN.json').read_text());assert scaler.identity==plan['scaler_identity'];assert [e.identity for e in train]==plan['episode_identities']
 expected={'features2025/FEATURES.npz': '81550b0443d2c725cdce7950ecc46e676dd12d5aa76185f4bd8d97e4e003ef06', 'features2025/EXPERTS.npz': 'e6c783bb0b6927218afa426c6535485e3336955ecfdcbd17fefba22432b6cf4e', 'economics2025/ECONOMICS.npz': '0ad850e9ca4549fe1442aeceaa3de5d3abbfb8c0c1e7a3d4c0f812d0ffb8fb4d'}
 for name,h in expected.items():assert sha(R/name)==h,'Published2025inputidentitychanged'
 f=np.load(R/'features2025/FEATURES.npz');a=np.load(R/'features2025/EXPERTS.npz');b=np.load(R/'economics2025/ECONOMICS.npz');d=a['decision_us'];np.testing.assert_array_equal(d,b['decision_us']);source=digest({n:sha(R/n) for n in ['features2025/FEATURES.npz','features2025/EXPERTS.npz','economics2025/ECONOMICS.npz']});e=from_arrays('SEEN_2025_FORWARD',d,b['prices'],b['funding_coeff'],a['expert_targets'],a['expert_eligible'],a['past_returns30'],f,p,source,role='SEEN_VALIDATION');results={}
 for arm in ['NATURAL','BALANCED']:
  folder=fit/arm;t=json.loads((folder/'TERMINAL.json').read_text());ptr=t['checkpoint'];assert t['step']==256 and t['status']=='FIXED256_COMPLETE';assert sha(folder/ptr['path'])==ptr['SHA256']==pub['arms'][arm]['checkpoint_SHA256'];assert t['model_identity']==pub['arms'][arm]['model_identity']
  x=torch.load(folder/ptr['path'],map_location='cpu',weights_only=True);m,_=initialize(scaler);opt=torch.optim.Adam(m.parameters(),lr=.0003,betas=(.9,.999),eps=1e-8,weight_decay=0.,foreach=False);_validate_model_state(m,x['model'],x['model_identity']);_validate_saved_optimizer(m,opt,x['optimizer'],256,{n:0 for n,_ in m.named_parameters()});_validate_rng(x['rng']);m.load_state_dict(x['model']);opt.load_state_dict(x['optimizer']);m.eval();assert model_identity(m)==t['model_identity'];before=(model_identity(m),tree_identity(opt.state_dict()),tree_identity(_rng_state()))
  with torch.no_grad():request=predict_episode(m,e,feature_batch_size=32).numpy();targets,mapped=p.mapped_path(compress(request),e.internal.contexts);r=charged_terminal_path(torch.tensor(targets,dtype=torch.float64),e.prices,e.funding_coeff,plan=BoundaryPlan.full_fill_diagnostic(len(d)))
  assert before==(model_identity(m),tree_identity(opt.state_dict()),tree_identity(_rng_state()));np.testing.assert_allclose(request.sum(1),1,atol=1e-12,rtol=0);assert not request[:,2:4].any() and not request[~e.eligible].any();nav=r['nav'].numpy();qty=r['quantity'].numpy();held=r['boundary_held_quantity'].numpy();budget=expand(np.stack([v['budget'] for v in mapped]));rows=[];carry=np.zeros(5);err=0.;totals=np.zeros(5)
  for i,timestamp in enumerate(d):
   price=e.prices[i];nxt=e.prices[min(i+1,len(d)-1)];opening=np.array(cost(qty[i]-carry,price));redu=np.array(cost(held[i]-qty[i],nxt));fp=-float(qty[i]@e.funding_coeff[i]) if i<len(d)-1 else 0.;pp=float(qty[i]@(nxt-price));totals+=np.r_[pp,fp,opening+redu];expected=nav[i]+pp+fp-(opening+redu).sum();err=max(err,abs(expected-nav[i+1]));den=nav[i]-opening.sum();gross=float((abs(qty[i])*price).sum()/den);net=float(qty[i]@price/den);assert gross<=.600000001 and np.all(abs(qty[i])*price<=.3*den+1e-8)
   rows.append({'decision_us':int(timestamp),'start_nav':float(nav[i]),'end_nav':float(nav[i+1]),'price_PnL':pp,'funding_PnL':fp,'fees':float((opening+redu)[0]),'spread':float((opening+redu)[1]),'slippage':float((opening+redu)[2]),'actual_gross':gross,'actual_net':net,'requested_SHORT':float(request[i,5]),'applied_SHORT':float(budget[i,5]),'paid_terminal':i==len(d)-1});carry=held[i]
  assert err<1e-8 and not qty[-1].any() and not held[-1].any();np.testing.assert_allclose(totals[1:], [float(r[k]) for k in ['funding','fees','spread','slippage']],atol=1e-9,rtol=1e-12);assert abs(totals[0]+totals[1]-totals[2:].sum()-(nav[-1]-10000))<1e-8
  with (out/(arm+'_DAILY.csv')).open('w') as fcsv:w=csv.DictWriter(fcsv,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  np.savez_compressed(out/(arm+'_PATH.npz'),decision_us=d,request=request,targets=targets,budget=budget,nav=nav,quantity=qty,boundary_held_quantity=held)
  result={'net_PnL':float(nav[-1]-10000),'cumulative_return':float(nav[-1]/10000-1),'maximum_daily_drawdown':float(np.max(1-nav/np.maximum.accumulate(nav))),'mean_actual_gross':float(np.mean([v['actual_gross'] for v in rows[:-1]])),'mean_actual_net':float(np.mean([v['actual_net'] for v in rows[:-1]])),'mean_requested_SHORT':float(request[:-1,5].mean()),'mean_applied_SHORT':float(budget[:-1,5].mean()),'price_PnL':float(totals[0]),'funding_PnL':float(totals[1]),'fees':float(totals[2]),'spread':float(totals[3]),'slippage':float(totals[4]),'maximum_independent_PnL_error':err,'risk_events':len(r['risk_events']),'model_identity':model_identity(m),'model_Adam_RNG_unchanged':True};results[arm]=result;print(arm,json.dumps(result),flush=True);(out/(arm+'_RESULT.json')).write_text(json.dumps(result,indent=2)+'\n')
 (out/'RESULTS.json').write_text(json.dumps({'status':'COMPLETE_TWO_FROZEN_MODELS_DAILY_ONLY','period':'2025Jan1-Dec31 paid close','capital_each':10000,'active_intervals':364,'results':results,'model_inferences':2,'wallets':2,'optimizer_steps':0,'scaler_updates':0,'source_identity':source,'seen_development_forward_validation':True,'native_minute_replay':False,'live_APR':'NOT_RELIABLY_ESTIMABLE'},indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--out',required=True);p.add_argument('--publication',required=True);x=p.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True);run(x.state,x.out,x.publication)
