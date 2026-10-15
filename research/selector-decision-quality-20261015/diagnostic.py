"""Frozen forecast decision-quality diagnostic; never fits or runs a wallet."""
import argparse,json,math
from itertools import combinations
from collections import Counter


def selected_rows(rows):
    previous_end=-1; selected=[]
    for row in rows:
        if row['decision_us'] > previous_end and row['usable']:
            selected.append(row); previous_end=row['label_available_us']
    return selected


def score(prediction, utility, eligible, names):
    ids=[i for i,v in enumerate(eligible) if v]
    if not ids: raise ValueError('No eligible experts')
    if any(not math.isfinite(prediction[i]) or not math.isfinite(utility[i]) for i in ids):
        raise ValueError('Eligible values must be finite')
    maximum=max(prediction[i] for i in ids)
    chosen=[i for i in ids if prediction[i]==maximum]
    actual=math.fsum(utility[i] for i in chosen)/len(chosen)
    correct=0.; comparisons=0; actual_ties=0; forecast_ties=0
    for i,j in combinations(ids,2):
        if utility[i]==utility[j]: actual_ties+=1; continue
        comparisons+=1
        if prediction[i]==prediction[j]: correct+=.5; forecast_ties+=1
        elif (prediction[i]>prediction[j])==(utility[i]>utility[j]): correct+=1
    ceiling=max(utility[i] for i in ids)
    return {'chosen':[names[i] for i in chosen], 'chosen_utility':actual,
            'oracle_regret':ceiling-actual,'pairwise_correct_equivalent':correct,
            'pairwise_comparisons':comparisons,'actual_ties_excluded':actual_ties,
            'forecast_ties_half_credit':forecast_ties,
            'pairwise_accuracy':correct/comparisons if comparisons else None}


def analyze(data):
    rows=data['rows']; names=data['experts']
    if any(rows[i]['decision_us']>=rows[i+1]['decision_us'] for i in range(len(rows)-1)): raise ValueError('Chronological unique rows required')
    if any(r['label_available_us']<=r['decision_us'] for r in rows): raise ValueError('Future label maturity required')
    for row in rows:
        d=row['decision_us']
        if row['label_available_us'] != d+7*86400000000+120000001:
            raise ValueError('Original seven-day label maturity contract required')
        if row['label_available_us']>data['evaluation_label_availability_cutoff_us']:
            raise ValueError('Label unavailable at registered evaluation endpoint')
        if any(v>d for v in row['state_and_market_fit_available_us']):
            raise ValueError('Prediction precedes saved fit availability')
        if row['market_feature_available_us']>d or row['latest_target_available_us']>d or row['latest_state_feedback_available_us']>=d:
            raise ValueError('Future input or nonpast feedback')
        if len(row['eligible'])!=len(names) or not row['eligible'][names.index('CASH')]:
            raise ValueError('Explicit expert masks with eligible CASH required')
    chosen=selected_rows(rows); blocks=[]; mixes={m:Counter() for m in ['state','market']}
    for row in chosen:
        b={k:row[k] for k in ['date','decision_us','label_available_us','eligible','utility','prediction_state','prediction_market']}
        ids=[i for i,v in enumerate(row['eligible']) if v]
        b['oracle_utility']=max(row['utility'][i] for i in ids)
        b['oracle_experts']=[names[i] for i in ids if row['utility'][i]==b['oracle_utility']]
        b['cash_utility']=row['utility'][names.index('CASH')]
        for m in mixes:
            b[m]=score(row['prediction_'+m],row['utility'],row['eligible'],names)
            for name in b[m]['chosen']:mixes[m][name]+=1/len(b[m]['chosen'])
        b['market_minus_state_utility']=b['market']['chosen_utility']-b['state']['chosen_utility']
        blocks.append(b)
    if not blocks: raise ValueError('No supported blocks')
    n=len(blocks); out={'role':'SEEN_DEVELOPMENT_FORECAST_DIAGNOSTIC_NOT_PORTFOLIO_RETURN','experts':names,'blocks':blocks,'support':{'score_rows':data.get('source_score_rows',len(rows)),'usable_rows':sum(r['usable'] for r in rows),'selected_blocks':n,'excluded_unusable':data.get('excluded_original_rows',[])+[{'date':r['date'],'reasons':r['reasons']} for r in rows if not r['usable']],'unselected_usable_overlap':sum(r['usable'] for r in rows)-n},'models':{}}
    for m in mixes:
        vals=[b[m]['chosen_utility'] for b in blocks];pairs=sum(b[m]['pairwise_comparisons'] for b in blocks)
        out['models'][m]={'mean_chosen_utility':math.fsum(vals)/n,'mean_oracle_regret':math.fsum(b[m]['oracle_regret'] for b in blocks)/n,'positive_utility_blocks':sum(v>0 for v in vals),'zero_utility_blocks':sum(v==0 for v in vals),'negative_utility_blocks':sum(v<0 for v in vals),'chosen_fractional_counts':dict(mixes[m]),'pairwise_comparisons':pairs,'pooled_pairwise_accuracy':math.fsum(b[m]['pairwise_correct_equivalent'] for b in blocks)/pairs if pairs else None,'mean_block_pairwise_accuracy':math.fsum(b[m]['pairwise_accuracy'] for b in blocks if b[m]['pairwise_accuracy'] is not None)/sum(b[m]['pairwise_accuracy'] is not None for b in blocks) if any(b[m]['pairwise_accuracy'] is not None for b in blocks) else None,'top_forecast_tied_blocks':sum(len(b[m]['chosen'])>1 for b in blocks),'actual_pair_ties_excluded':sum(b[m]['actual_ties_excluded'] for b in blocks),'forecast_pair_ties_half_credit':sum(b[m]['forecast_ties_half_credit'] for b in blocks)}
    deltas=[b['market_minus_state_utility'] for b in blocks]
    out['paired']={'mean_market_minus_state_utility':math.fsum(deltas)/n,'market_better_blocks':sum(v>0 for v in deltas),'state_better_blocks':sum(v<0 for v in deltas),'equal_blocks':sum(v==0 for v in deltas),'different_choice_blocks':sum(b['state']['chosen']!=b['market']['chosen'] for b in blocks)}
    out['opportunity']={'mean_unattainable_oracle_utility':math.fsum(b['oracle_utility'] for b in blocks)/n,'positive_oracle_blocks':sum(b['oracle_utility']>0 for b in blocks),'cash_best_or_tied_blocks':sum('CASH' in b['oracle_experts'] for b in blocks),'cash_mean_utility':math.fsum(b['cash_utility'] for b in blocks)/n}
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('inputs');ap.add_argument('output');a=ap.parse_args()
    result=analyze(json.load(open(a.inputs)));open(a.output,'w').write(json.dumps(result,indent=2,allow_nan=False)+'\n')
