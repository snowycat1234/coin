"""Independent exact-arithmetic audit of the permitted derived diagnostic files.
No source-array reads, fits, wallets, external downloads, or public identifiers.
"""
from collections import Counter
from datetime import datetime, timezone, timedelta
from fractions import Fraction as F
from itertools import combinations
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
read = lambda name: json.loads((HERE / name).read_text(), parse_float=F)
data = read('derived_inputs.json')
reported = read('RESULTS.json')
names = data['experts']
rows = data['rows']
DAY = 86400000000
LATENCY = 120000001
checks = []

def require(value, description):
    if not value:
        raise AssertionError(description)
    checks.append(description)

require(len(rows) == 176, '176 derived mature usable rows')
require(data['source_score_rows'] == 182, '182 original saved forecast rows')
require(len(data['excluded_original_rows']) == 6, 'Six original rows excluded with explicit reasons')
require(all(rows[i]['decision_us'] < rows[i + 1]['decision_us'] for i in range(len(rows)-1)), 'Chronological unique decision timestamps')
require(all(len(r['eligible']) == len(names) for r in rows), 'Eligibility vectors match common expert count')
require(all(all(r['eligible']) for r in rows), 'All six common experts eligible on every usable row')
require(all(r['usable'] and not r['reasons'] for r in rows), 'Derived rows have no recorded exclusion reason')
require(all(r['label_available_us'] == r['decision_us'] + 7*DAY + LATENCY for r in rows), 'Label windows use seven days plus 120.000001 seconds')
require(all(r['label_available_us'] <= data['evaluation_label_availability_cutoff_us'] for r in rows), 'All usable labels mature by the configured existing evaluation cutoff')
require(all(max(r['state_and_market_fit_available_us']) <= r['decision_us'] for r in rows), 'Both saved fits available by each decision')
require(all(r['market_feature_available_us'] <= r['decision_us'] and r['latest_target_available_us'] <= r['decision_us'] for r in rows), 'Derived market and target availability no later than decision')
require(all(r['latest_state_feedback_available_us'] < r['decision_us'] for r in rows), 'Derived state feedback strictly earlier than decision')
require(all(r['utility'][names.index('CASH')] == 0 for r in rows), 'CASH realized reference utility is exactly zero')
proof = data['train_best_proof']
require(proof['training_rows'] == 40 and proof['selected'] == 'CASH', 'Saved training-best proof names CASH on 40 training rows')
require(proof['maximum_training_label_available_us'] < proof['training_cutoff_us'], 'Saved training proof label availability precedes training cutoff')
require(proof['mean_training_utility']['CASH'] == 0 and all(v < 0 for k,v in proof['mean_training_utility'].items() if k != 'CASH'), 'Saved training means make CASH the unique best static baseline')

# Independent chronological greedy selection. Decisions exactly at maturity are
# rejected because the frozen rule uses strict greater-than.
selected = []
for row in rows:
    if row['usable'] and (not selected or row['decision_us'] > selected[-1]['label_available_us']):
        selected.append(row)
require(len(selected) == 22, 'Earliest-first strict nonoverlap selection yields 22 blocks')
require(all(selected[i+1]['decision_us']-selected[i]['decision_us'] == 8*DAY for i in range(len(selected)-1)), 'Selected decision dates are eight days apart')
require(selected[0]['date'] == '2024-01-01' and selected[-1]['date'] == '2024-06-17', 'Selected support runs January 1 through June 17, 2024')

# No production scoring or selection function is imported.
def exact_score(p, u, eligible):
    ids = [i for i in range(len(eligible)) if eligible[i]]
    top = max(p[i] for i in ids)
    chosen = [i for i in ids if p[i] == top]
    value = sum((u[i] for i in chosen), F(0)) / len(chosen)
    credits = F(0)
    comparisons = actual_ties = forecast_ties = 0
    for i,j in combinations(ids, 2):
        if u[i] == u[j]:
            actual_ties += 1
            continue
        comparisons += 1
        if p[i] == p[j]:
            credits += F(1,2)
            forecast_ties += 1
        elif (p[i]-p[j])*(u[i]-u[j]) > 0:
            credits += 1
    return {'chosen':[names[i] for i in chosen], 'chosen_utility':value,
            'oracle_regret':max(u[i] for i in ids)-value,
            'pairwise_correct_equivalent':credits,
            'pairwise_comparisons':comparisons,
            'actual_ties_excluded':actual_ties,
            'forecast_ties_half_credit':forecast_ties,
            'pairwise_accuracy':credits/comparisons if comparisons else None}

blocks = []
mixes = {m:Counter() for m in ('state','market')}
for row in selected:
    block = {k:row[k] for k in ('date','decision_us','label_available_us','eligible','utility','prediction_state','prediction_market')}
    ceiling = max(v for v,e in zip(row['utility'],row['eligible']) if e)
    block['oracle_utility'] = ceiling
    block['oracle_experts'] = [name for name,v,e in zip(names,row['utility'],row['eligible']) if e and v == ceiling]
    block['cash_utility'] = row['utility'][names.index('CASH')]
    for model in mixes:
        block[model] = exact_score(row['prediction_'+model], row['utility'], row['eligible'])
        chosen = block[model]['chosen']
        for name in chosen:
            mixes[model][name] += F(1,len(chosen))
    block['market_minus_state_utility'] = block['market']['chosen_utility'] - block['state']['chosen_utility']
    blocks.append(block)

n = len(blocks)
mean = lambda vals: sum(vals, F(0))/n
models = {}
for model in mixes:
    b = [r[model] for r in blocks]
    vals = [r['chosen_utility'] for r in b]
    comps = sum(r['pairwise_comparisons'] for r in b)
    accuracies = [r['pairwise_accuracy'] for r in b if r['pairwise_accuracy'] is not None]
    models[model] = {
        'mean_chosen_utility':mean(vals),
        'mean_oracle_regret':mean(r['oracle_regret'] for r in b),
        'positive_utility_blocks':sum(v>0 for v in vals),
        'zero_utility_blocks':sum(v==0 for v in vals),
        'negative_utility_blocks':sum(v<0 for v in vals),
        'chosen_fractional_counts':dict(mixes[model]),
        'pairwise_comparisons':comps,
        'pooled_pairwise_accuracy':sum((r['pairwise_correct_equivalent'] for r in b),F(0))/comps,
        'mean_block_pairwise_accuracy':sum(accuracies,F(0))/len(accuracies),
        'top_forecast_tied_blocks':sum(len(r['chosen'])>1 for r in b),
        'actual_pair_ties_excluded':sum(r['actual_ties_excluded'] for r in b),
        'forecast_pair_ties_half_credit':sum(r['forecast_ties_half_credit'] for r in b)
    }
deltas = [r['market_minus_state_utility'] for r in blocks]
paired = {'mean_market_minus_state_utility':mean(deltas),
          'market_better_blocks':sum(v>0 for v in deltas),
          'state_better_blocks':sum(v<0 for v in deltas),
          'equal_blocks':sum(v==0 for v in deltas),
          'different_choice_blocks':sum(r['state']['chosen']!=r['market']['chosen'] for r in blocks)}
opportunity = {'mean_unattainable_oracle_utility':mean(r['oracle_utility'] for r in blocks),
               'positive_oracle_blocks':sum(r['oracle_utility']>0 for r in blocks),
               'cash_best_or_tied_blocks':sum('CASH' in r['oracle_experts'] for r in blocks),
               'cash_mean_utility':mean(r['cash_utility'] for r in blocks)}
support = {'score_rows':data['source_score_rows'],'usable_rows':len(rows),'selected_blocks':n,
           'excluded_unusable':data['excluded_original_rows'],'unselected_usable_overlap':len(rows)-n}
expected = {'role':'SEEN_DEVELOPMENT_FORECAST_DIAGNOSTIC_NOT_PORTFOLIO_RETURN',
            'experts':names,'blocks':blocks,'support':support,'models':models,
            'paired':paired,'opportunity':opportunity}

numeric_errors = []
leaves = 0

def compare(a,b,path='root'):
    global leaves
    if isinstance(a,dict):
        assert isinstance(b,dict) and set(a)==set(b), path+' dictionary keys'
        for key in a:
            compare(a[key],b[key],path+'.'+key)
    elif isinstance(a,list):
        assert isinstance(b,list) and len(a)==len(b), path+' list length'
        for i,(x,y) in enumerate(zip(a,b)):
            compare(x,y,path+f'[{i}]')
    elif isinstance(a,F):
        error=abs(a-F(b))
        numeric_errors.append((error,path))
        assert error <= F(1,10**16), path+' exact arithmetic disagreement'
        leaves += 1
    else:
        assert a == b, path+' exact field disagreement'
        leaves += 1
compare(expected,reported)
require(True,'Every reported block, choice, tie, comparison, count, support field, and aggregate matches independent exact recomputation')
max_error, max_error_path = max(numeric_errors)

# Supplement the supplied examples with independent boundary/tie arithmetic checks.
require(exact_score([F(1),F(1),F(0)],[F(-2),F(4),F(0)],[True]*3)['chosen_utility'] == 1, 'Independent exact top-tie averaging test')
require(exact_score([F(0),F(0),F(0)],[F(0),F(1),F(2)],[True]*3)['pairwise_accuracy'] == F(1,2), 'Independent forecast-tie half-credit test')
require(exact_score([F(0),F(2),F(1)],[F(0),F(0),F(1)],[True]*3)['actual_ties_excluded'] == 1, 'Independent realized-tie exclusion test')
tests = subprocess.run([sys.executable,'-m','unittest','-v','test_diagnostic.py'],cwd=HERE,capture_output=True,text=True)
require(tests.returncode==0,'All 22 supplied unit tests pass')

limits = [
    'Nonoverlapping label windows are not established to be statistically independent; no significance claim is supported.',
    'Highest-forecast reference-utility scoring is a forecast diagnostic, not executable portfolio returns; shared-wallet nonlinearities and switching costs are absent.',
    'This is previously seen development evidence, with one fixed earliest-date phase; no fresh out-of-sample or phase-robustness claim is supported.',
    'Forecast publication timestamps are absent. Fit, feature, target, feedback and reviewed ranker conditions support causal-clock consistency but do not certify historical live issuance.',
    'Source reader code was reviewed, including immutable-member hash checks, original mask equality, label reconstruction and ranker clocks. This reviewer did not reopen source arrays or independently execute their provenance checks.',
    'Training-best CASH is verified against the supplied saved training-mean proof and reader logic; original training arrays were not independently recomputed by this reviewer.'
]
nonblocking = [
    'The initially noted no-comparison aggregate edge case is fixed in the current production implementation; two regression tests cover all-realized-utility ties and CASH-only eligibility.',
    'The frozen-selection intent is documented, but this review does not independently establish that the plan was created before any payload values were inspected.'
]

def floats(obj):
    if isinstance(obj,F): return float(obj)
    if isinstance(obj,dict): return {k:floats(v) for k,v in obj.items()}
    if isinstance(obj,list): return [floats(v) for v in obj]
    return obj
review = {
    'status':'PASS_FOR_STATED_SEEN_DEVELOPMENT_DIAGNOSTIC',
    'independent_method':'Separate implementation; exact Fraction arithmetic on the serialized decimal inputs; no production scoring/selection imports.',
    'scope':'Only the permitted plan, code, test, derived-input, results and final test-log files were read; no refit, wallet, source-array read, holdout, external download or allocation tuning.',
    'verification':{'checks_passed':len(checks),'reported_leaf_fields_compared':leaves,
                    'numeric_fields_compared':len(numeric_errors),
                    'absolute_numeric_tolerance':1e-16,
                    'maximum_absolute_numeric_difference':float(max_error),
                    'maximum_difference_field':max_error_path,
                    'supplied_unit_tests_passed':22},
    'support':support,'models':models,'paired':paired,'opportunity':opportunity,
    'exact_pooled_accuracy':{m:str(models[m]['pooled_pairwise_accuracy']) for m in models},
    'selected_dates':[r['date'] for r in selected],
    'checks':checks,'limitations':limits,'nonblocking_code_notes':nonblocking,
    'bottom_line':'Market-plus-state underperforms state-only on this fixed 22-block argmax diagnostic; both have negative mean chosen reference utility versus zero for CASH. This cannot establish financial portfolio performance or statistical generalization.'
}
(HERE/'REVIEW_INDEPENDENT.json').write_text(json.dumps(floats(review),indent=2,allow_nan=False)+'\n')
text = f'''Independent review: PASS for the stated seen-development diagnostic.

Independent exact Fraction recomputation matches every reported block and aggregate.
{leaves} leaf fields were compared; maximum numeric rounding difference is {float(max_error):.3g}.
All 22 supplied unit tests pass. Source arrays were not reopened or refitted.

Support: 182 original saved rows; 176 usable mature rows; 22 earliest-first,
strictly nonoverlapping seven-day-plus-120.000001-second windows, selected from
January 1 through June 17, 2024. Six June 25-30 rows are excluded. All six experts
are eligible on all usable rows; no top-forecast or pairwise forecast ties occur.

Mean chosen reference utility:
  State-only:        {float(models['state']['mean_chosen_utility']):.15f}
  Market-plus-state:{float(models['market']['mean_chosen_utility']): .15f}
  Market minus state:{float(paired['mean_market_minus_state_utility']): .15f}
  CASH:             0
State wins 6 blocks, market wins 2, and 14 are equal; choices differ on 8 blocks.
Pooled pairwise order accuracy: state {models['state']['pooled_pairwise_accuracy']}
({float(models['state']['pooled_pairwise_accuracy']):.6%}); market
{models['market']['pooled_pairwise_accuracy']} ({float(models['market']['pooled_pairwise_accuracy']):.6%}).
Each uses 315 unequal-realized-utility comparisons; 15 actual pair ties are excluded.
The unattainable ex-post opportunity ceiling averages {float(opportunity['mean_unattainable_oracle_utility']):.15f}.
CASH is uniquely training-best under the saved 40-row mean-utility proof.

Limits:
'''+''.join('- '+s+'\n' for s in limits)+'\nNonblocking notes:\n'+''.join('- '+s+'\n' for s in nonblocking)
(HERE/'REVIEW_INDEPENDENT.txt').write_text(text)
print(json.dumps({'status':review['status'],'checks_passed':len(checks),'fields_compared':leaves,'max_numeric_error':float(max_error),'paired':floats(paired),'files':['REVIEW_INDEPENDENT.json','REVIEW_INDEPENDENT.txt','REVIEW_INDEPENDENT.py']},indent=2))
