import json, math, statistics
from pathlib import Path
from itertools import combinations
P=Path(__file__).resolve().parent
D=json.loads((P/'derived_inputs.json').read_text())
R=json.loads((P/'RESULTS.json').read_text())
checks=0
def eq(a,b):
 global checks
 checks+=1
 if isinstance(a,float): assert math.isclose(a,b,rel_tol=1e-13,abs_tol=1e-15),(a,b)
 else: assert a==b,(a,b)
names=D['experts']; rows=D['rows']; cash=names.index('CASH'); day=86400000000
assert len(rows)==176
assert [r['decision_us'] for r in rows]==sorted(set(r['decision_us'] for r in rows))
for r in rows:
 t=r['decision_us']; assert r['label_available_us']==t+7*day+120000001
 assert r['label_available_us']<=D['evaluation_label_availability_cutoff_us']
 assert r['eligible'][cash] and r['utility'][cash]==0
 assert all(x<=t for x in r['state_and_market_fit_available_us'])
 assert r['market_feature_available_us']<=t and r['latest_target_available_us']<=t
 assert r['latest_state_feedback_available_us']<t
 for k,yes in enumerate(r['eligible']):
  if yes: assert all(math.isfinite(r[f][k]) for f in ('utility','prediction_state','prediction_market'))
selected=[]
for r in rows:
 if r['usable'] and (not selected or r['decision_us']>selected[-1]['label_available_us']): selected.append(r)
eq(len(selected),22);eq([r['date'] for r in selected],[r['date'] for r in R['blocks']])
metrics={}; values={}; choices={}; ceilings=[]
for m in ('state','market'):
 vals=[]; regrets=[]; nums=[]; dens=[]; ties=[]; fties=[]; tiedtop=[]; counts={}; chs=[]
 for r,b in zip(selected,R['blocks']):
  ids=[i for i,e in enumerate(r['eligible']) if e]; y=r['utility']; p=r['prediction_'+m]
  winners=[i for i in ids if not any(p[j]>p[i] for j in ids)]
  chosen=[names[i] for i in winners]; actual=statistics.mean(y[i] for i in winners); ceiling=max(y[i] for i in ids)
  num=0.; den=0; tie=0; ftie=0
  for i,j in combinations(ids,2):
   if y[i]==y[j]:tie+=1;continue
   den+=1
   if p[i]==p[j]:num+=.5;ftie+=1
   elif (p[i]-p[j])*(y[i]-y[j])>0:num+=1
  block={'chosen':chosen,'chosen_utility':actual,'oracle_regret':ceiling-actual,'pairwise_correct_equivalent':num,'pairwise_comparisons':den,'actual_ties_excluded':tie,'forecast_ties_half_credit':ftie,'pairwise_accuracy':num/den if den else None}
  for k,v in block.items():eq(v,b[m][k])
  eq(ceiling,b['oracle_utility']);eq([names[i] for i in ids if y[i]==ceiling],b['oracle_experts'])
  vals.append(actual);regrets.append(ceiling-actual);nums.append(num);dens.append(den);ties.append(tie);fties.append(ftie);tiedtop.append(len(winners)>1);chs.append(chosen)
  for w in chosen:counts[w]=counts.get(w,0)+1/len(chosen)
 metrics[m]={'mean_chosen_utility':statistics.mean(vals),'mean_oracle_regret':statistics.mean(regrets),'positive_utility_blocks':sum(x>0 for x in vals),'zero_utility_blocks':vals.count(0),'negative_utility_blocks':sum(x<0 for x in vals),'chosen_fractional_counts':counts,'pairwise_comparisons':sum(dens),'pooled_pairwise_accuracy':sum(nums)/sum(dens),'mean_block_pairwise_accuracy':statistics.mean(x/y for x,y in zip(nums,dens) if y),'top_forecast_tied_blocks':sum(tiedtop),'actual_pair_ties_excluded':sum(ties),'forecast_pair_ties_half_credit':sum(fties)}
 for k,v in metrics[m].items():eq(v,R['models'][m][k])
 values[m]=vals;choices[m]=chs
v=[m-s for m,s in zip(values['market'],values['state'])]
paired={'mean_market_minus_state_utility':statistics.mean(v),'market_better_blocks':sum(x>0 for x in v),'state_better_blocks':sum(x<0 for x in v),'equal_blocks':v.count(0),'different_choice_blocks':sum(s!=m for s,m in zip(choices['state'],choices['market']))}
for k,x in paired.items():eq(x,R['paired'][k])
ceilings=[max(y for y,e in zip(r['utility'],r['eligible']) if e) for r in selected]
op={'mean_unattainable_oracle_utility':statistics.mean(ceilings),'positive_oracle_blocks':sum(x>0 for x in ceilings),'cash_best_or_tied_blocks':ceilings.count(0),'cash_mean_utility':0.0}
for k,x in op.items():eq(x,R['opportunity'][k])
eq(R['support']['excluded_unusable'],D['excluded_original_rows']);eq(R['support']['score_rows'],182);eq(R['support']['usable_rows'],176);eq(R['support']['unselected_usable_overlap'],154)
proof=D['train_best_proof'];assert max(proof['mean_training_utility'],key=proof['mean_training_utility'].get)=='CASH';assert proof['maximum_training_label_available_us']<proof['training_cutoff_us']
report={'status':'PASS independent derived-input arithmetic and recorded-clock audit','comparisons':checks,'selected_dates':[r['date'] for r in selected],'all_rows_six_experts_eligible':all(all(r['eligible']) for r in rows),'models':metrics,'paired':paired,'opportunity':op,'scope_limitations':['No original NPZ opened; derived input provenance, exclusions, ranker clocks and utility reconstruction are inspected source assertions, not independently verified raw data.','Saved per-row forecast publication timestamps absent; recorded fit/features/targets/feedback clocks support availability but do not certify live issuance.','Argmax reference utility diagnostic, not original soft-budget shared-wallet executed portfolio.','Utility is log1p seven-day net reference return less 0.5 daily reference MDD; oracle is ex-post unattainable ceiling.','All actual rows eligible and untied forecast maxima; edge-case tie/mask correctness is source-inspected, not naturally exercised.']}
(P/'INDEPENDENT_CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
