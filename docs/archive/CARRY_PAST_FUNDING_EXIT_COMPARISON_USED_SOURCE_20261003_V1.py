"""Static D032 draft: saved-summary comparison and explicitly authorized attribution.

No account, NAV, source QA, fee formula or signal is recomputed. The only old
Parquet columns read, after future root freeze/authorization and actual audit0,
are event_us/symbol/ownership_qualified/signed_funding_USDT for attribution.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
MASTER='protocols/CARRY_PAST_FUNDING_EXIT_D032_20261003_V1.json'
AUDIT='reports/fast_research/CARRY_PAST_FUNDING_EXIT_TWO_PERIOD_DECIMAL_AUDIT_20261003_V1.json'
NEW_STATUS='COMPLETE_D032_PAST_FUNDING_EXIT_CONDITIONAL_SCREENING_NOT_LONG_TERM_APR'
AUDIT_STATUS='PASS_D032_TWO_PERIOD_DECIMAL_CONDITIONAL_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'
GATE_REASON='PAST_OWNED_FUNDING_7D_LAG1_NONPOSITIVE_PERMANENT_CASH'
CONTROL_PINS={
 '122D':('CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json','71a910d1da8ae9a5ca68411693f14b6f82b43ed992ac33ee50a6dcf321a6b651',
         'CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json','3274d27bcc5b2a9809030ce30d16a25a9a47b97a06a142d968489aeff9bb30e6',175680,122,732,32),
 '90D':('CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json','dd42d50cff88f1d04a952cbe92f01af2bcb3413c6ad30b0371f625972f9f3a71',
        'CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json','95dbe4da78b7c0114321756ae9e289f094fc2b1a5066f14c54f6c65b995feed4',129600,90,540,24)}
GATE_RULES=dict(minimum_hold_us=691_200_000_000,decision_clock='DAILY_UTC_CLOSED_DAY_00_00',
    decision_observation_offset_us=1,observed_window='[D-8DAY,D-1DAY)',window_start_strictly_after_entry=True,
    threshold_signed_owned_cash_USDT=0.,condition='SUM_LE_ZERO',publication_assumption='UNCERTIFIED_ONE_UTC_DAY_LAG',
    decision_arithmetic='MATH_FSUM_OF_ACTUAL_CREDITED_FLOAT64_LEDGER_CASH_EXACT_LE_ZERO_NO_BAND',
    input='ACTUALLY_OWNED_SIGNED_FUNDING_CASH_ACCOUNT_SUM_BOTH_SYMBOLS',
    action='NEXT_STRICTLY_LATER_CLOSED_MINUTE_ALL_FLAT_PERMANENT_CASH',
    priority='ALREADY_PENDING_FULL_EXIT_FIRST_EXISTING_DUE_TRIM_DISPATCH_UNCHANGED',
    no_reentry=True,no_extra_capital=True,no_HPO=True)
CRITERIA=dict(both_net_delta_gt_USDT=1e-7,all_observation_DD_increment_lte=1e-10,major_positive_coupon_foregone_share_gt=0.5,
              pause_rounding_sensitive_trigger=True,no_trigger_is_no_adoption_evidence=True,
              constraints_unchanged=True,accounting_tolerances_not_statistical_significance=True)
METRICS=('net_PnL_USDT','gross_cost_addback_PnL_USDT','signed_conditional_funding_USDT','fees_USDT',
         'assumed_spread_USDT','assumed_slippage_USDT','turnover','fills','owned_funding_events',
         'all_observation_max_drawdown','minute_max_drawdown','maximum_total_gross')

def check(ok,text):
    if not ok: raise ValueError(text)

def small(path,expected=None):
    original=Path(path); path=original.resolve()
    check((path.is_relative_to(ROOT) or path.is_relative_to(STATE)) and not original.is_symlink()
          and path.is_file() and path.stat().st_size<=2_000_000 and path.suffix in ('.json','.py'), 'Ordinary small metadata only')
    data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    check(expected is None or digest==expected,'Frozen small receipt/source changed')
    return (json.loads(data) if path.suffix=='.json' else None),digest

def closed(report):
    identity=report['binding']['task_id'];check(re.fullmatch('[0-9a-f]{32}',identity) is not None,'Exact actual task')
    path=STATE/'task-progress'/('task-'+identity+'.json'); value,digest=small(path)
    check(value['id']==identity and value['status']=='completed' and value['exit_code']==0,'Actual/audit must be closed0 before any ledger read')
    return dict(path=str(path),sha256=digest,task=value)

def output_identity(rows):
    result={r['kind']:{k:r[k] for k in ('path','sha256','bytes','rows')} for r in rows}
    check(len(rows)==len(result)==4 and set(result)=={'minute_nav','daily_nav','funding_ledger','fill_ledger'},'Exactly four bound saved outputs')
    return result

def numeric_flags(proof,new):
    flagged=[]
    for witness in proof['gate_numeric_witnesses']:
        keys=('float_condition_met','exact_credited_condition_met','independent_condition_met',
              'predicate_sign_disagreement','rounding_sensitive_trigger')
        check(all(type(witness[k]) is bool for k in keys),'Explicit independently checked numeric predicates')
        disagree=len({witness[k] for k in keys[:3]})>1
        sensitive=(witness['status']=='ROUNDING_SENSITIVE_TRIGGER_WITNESS' or
                   witness['predicate_sign_disagreement'] or witness['rounding_sensitive_trigger'] or disagree)
        check(witness['status'] in ('ROUNDING_SENSITIVE_TRIGGER_WITNESS','NO_SIGN_DISAGREEMENT'),'Exact numeric audit status')
        if sensitive: flagged.append(witness)
    check(proof['rounding_sensitive_trigger_count']==len(flagged),'Independent explicit sensitivity count, not absence-by-missing-field')
    scopes=[new,new['summary'],*new['summary']['past_funding_gate_checks']]
    actual_flags=[s for s in scopes if any(s.get(k)=='ROUNDING_SENSITIVE_TRIGGER_WITNESS' for k in ('status','reason','action','diagnostic')) or
        s.get('rounding_sensitive_trigger') is True or s.get('predicate_sign_disagreement') is True or
        s.get('rounding_sensitive_trigger_count',0)>0]
    return dict(adoption_paused=bool(flagged or actual_flags),independent_sensitive_count=len(flagged),
        independent_sensitive_witnesses=flagged[:8],actual_explicit_witness_count=len(actual_flags),
        producer_field_absence_is_not_independent_numeric_clearance=True)

def attribution(row,control_summary,gate_exit_us,events_expected):
    if gate_exit_us is None:
        return dict(scope='NO_ACTUAL_GATE_EXIT_NO_FOREGONE_ATTRIBUTION',applies=False,
            gate_actual_exit_us=None,foregone_positive_owned_coupon_USDT='0',foregone_negative_owned_coupon_USDT='0',
            foregone_positive_share=None,major_positive_coupon_foregone=False,funding_ledger_binding=row,
            ledger_contents_read=False,not_new_strategy_cashflow=True,publication_or_unit_certified=False)
    import pyarrow.parquet as pq
    path=Path(row['path']);check(not path.is_symlink() and path.resolve().is_relative_to(STATE) and path.stat().st_size==row['bytes']<=1_000_000,'Bound small saved funding ledger only')
    with path.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    check(digest==row['sha256'],'Saved funding-ledger byte SHA; no old NAV read')
    columns=['event_us','symbol','ownership_qualified','signed_funding_USDT']
    total_positive=Decimal(0);foregone_positive=Decimal(0);foregone_negative=Decimal(0);count=owned=foregone_count=0
    witnesses=[]
    for batch in pq.ParquetFile(path).iter_batches(batch_size=256,columns=columns):
        for item in batch.to_pylist():
            count+=1;check(item['symbol'] in ('BTCUSDT','ETHUSDT') and math.isfinite(item['signed_funding_USDT']),'Required attribution values only')
            if not item['ownership_qualified']: continue
            owned+=1;amount=Decimal(str(item['signed_funding_USDT']));total_positive+=max(amount,Decimal(0))
            if gate_exit_us is None or item['event_us']<gate_exit_us: continue
            foregone_count+=1;foregone_positive+=max(amount,Decimal(0));foregone_negative+=min(amount,Decimal(0))
            if len(witnesses)<8: witnesses.append(item)
    check(count==events_expected==row['rows'] and owned==control_summary['owned_funding_events'],'Saved full-control attribution scope')
    share=foregone_positive/total_positive if total_positive>0 else None
    return dict(scope='POST_RESULT_SAVED_CONTROL_CONDITIONAL_COUPON_ATTRIBUTION_NOT_CASHFLOW_OR_TRADING_SIGNAL',
        gate_actual_exit_us=gate_exit_us,applies=gate_exit_us is not None,control_positive_owned_coupon_USDT=str(total_positive),
        foregone_positive_owned_coupon_USDT=str(foregone_positive),foregone_negative_owned_coupon_USDT=str(foregone_negative),
        avoided_negative_coupon_magnitude_USDT=str(-foregone_negative),foregone_owned_events=foregone_count,
        foregone_positive_share=float(share) if share is not None else None,
        major_positive_coupon_foregone=share is not None and share>Decimal('0.5'),witnesses=witnesses,
        original_control_quantities_retained=True,not_new_strategy_cashflow=True,publication_or_unit_certified=False,
        funding_ledger_binding=row,required_columns=columns,old_NAV_read=False,account_or_QA_replayed=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Existing bounded/progress clean runtime')
    resource_record=resources.status();binding,binding_sha=small(args.binding);out=args.output.resolve()
    check(out.is_relative_to(ROOT/'reports/fast_research') and not out.exists(),'Exclusive comparison receipt')
    check(binding['contract_id']=='D032_ECONOMIC_COMPARISON_BINDING_V1' and binding['reader_authorized'] is True
          and binding['scope']=='POST_RESULT_CONDITIONAL_ATTRIBUTION_NOT_CASHFLOW_OR_TRADING_SIGNAL'
          and binding['gate_rules']==GATE_RULES and binding['adoption_criteria']==CRITERIA
          and binding['helper_sha256']==small(__file__)[1],'Explicit root-frozen read scope, exact8/7/1 profile and pre-results criteria')
    master,master_sha=small(ROOT/MASTER,binding['master_protocol_sha256'])
    check(master['contract_id']=='CARRY_PAST_FUNDING_EXIT_D032_V1' and master['gate_rules']==GATE_RULES
          and master['adoption_criteria']==CRITERIA,'Exact master8/7/1 rules and before-results adoption/pause criteria')
    audit,audit_sha=small(ROOT/AUDIT,binding['audit_sha256'])
    check(audit['status']==AUDIT_STATUS,'Completed independent new account audit required')
    audit_task=closed(audit);cases=binding['cases'];check(len(cases)==2 and {c['period'] for c in cases}==set(CONTROL_PINS),'Two full windows only')
    audit_cases={c['period']:c for c in audit['cases']};check(len(audit['cases'])==2 and set(audit_cases)==set(CONTROL_PINS)
        and audit['completed_cases_verified']==2,'Audit exact two-window scope')
    prepared=[];case_meta={};tasks={'audit':audit_task};small_proofs={str(args.binding.resolve()):binding_sha,MASTER:master_sha,AUDIT:audit_sha}
    for case in cases:
        period=case['period'];control_name,control_sha,parent_name,parent_sha,minutes,days,events,files=CONTROL_PINS[period]
        control_path=ROOT/'reports/fast_research'/control_name;parent_path=ROOT/'reports/fast_research'/parent_name
        control,_=small(control_path,control_sha);parent,_=small(parent_path,parent_sha)
        new_path=ROOT/'reports/fast_research'/('CARRY_PAST_FUNDING_EXIT_'+period+'_ACTUAL_20261003_V1.json')
        new,new_sha=small(new_path,case['new_actual_sha256']);proof=audit_cases[period]
        check(new['status']==NEW_STATUS and new['binding']['protocol_sha256']==master_sha
              and proof['actual_report_sha256']==new_sha,'Exact audited actual and master protocol')
        tasks[period]=closed(new);check(audit_task['task']['started_at']>=tasks[period]['task']['ended_at'],'Audit after actualclosed0')
        check(new['capital_net_APR']==control['capital_net_APR']=='NOT_EVALUABLE'
              and new['candidate_status']==control['candidate_status']=='NO_QUALIFIED_CANDIDATE'
              and not new['funding_unit_certified'] and not new['native_Bybit_prices_or_filters']
              and not new['unseen_qualification'] and not new['locked_consumed'],'No candidate/native/unit/longAPR promotion')
        cs,ns=control['summary'],new['summary'];check(cs['initial_capital_USDT']==ns['initial_capital_USDT']==10000
              and cs['rows']==ns['rows']==minutes and cs['all_source_events']==ns['all_source_events']==events
              and len(ns['months'])==len(cs['months'])==(4 if period=='122D' else 3),'Fixed complete saved summaries')
        check(len(new['input_bindings'])==files and new['input_bindings']==control['input_bindings'],'Same input metadata; no market/source re-QA')
        old_rules,new_rules=control['binding']['rules'],new['binding']['rules']
        check(all(new_rules.get(k)==v for k,v in old_rules.items()),'Unchanged C0/cost/caps/wallet/execution constraints')
        check(new_rules['past_funding_exit']==GATE_RULES,'Actual exact same funding-gate arithmetic/rules')
        control_outputs=output_identity(control['output_bindings'])
        parent_outputs=parent['output_bindings'] if period=='122D' else parent['output_bindings']['PAIR_TRIM']
        check(control_outputs==output_identity(parent_outputs)==case['frozen_control_outputs'],'Exact old four-output SHA metadata accepted by parent')
        check(abs(ns['all_observation_max_drawdown']-proof['all_observation_max_drawdown'])<=1e-10,'Saved audited all-observation risk within original accounting ratio tolerance')
        numerics=numeric_flags(proof,new)
        case_meta[period]=dict(new_actual_path=str(new_path),new_actual_sha256=new_sha,control_actual_path=str(control_path),control_actual_sha256=control_sha)
        prepared.append((period,cs,ns,control_outputs['funding_ledger'],events,numerics));small_proofs[str(new_path)]=new_sha
        small_proofs[str(control_path)]=control_sha;small_proofs[str(parent_path)]=parent_sha
    check(len({v['task']['id'] for v in tasks.values()})==3,'Separate twoactual/audit tasks')
    sensitive_count=sum(v[5]['independent_sensitive_count'] for v in prepared)
    check(audit['rounding_sensitive_trigger_count']==sensitive_count and
          audit['economic_adoption_paused_due_to_rounding']==(sensitive_count>0),'Explicit independent top-level numerical pause')
    results=[]
    # No Parquet reader is reached until all both-window actual/audit0 bindings above pass.
    for period,cs,ns,row,events,numerics in prepared:
        gate_exit=ns['exit_us'] if ns['exit_reason']==GATE_REASON else None
        check(gate_exit is None or ns['past_funding_gate_scheduled']>0,'Do not attribute margin/terminal stops to a gate')
        foregone=attribution(row,cs,gate_exit,events);deltas={k:ns[k]-cs[k] for k in METRICS}
        results.append(dict(period=period,**case_meta[period],control_summary={k:cs[k] for k in METRICS},new_summary={k:ns[k] for k in METRICS},
            deltas=deltas,control_months=cs['months'],new_months=ns['months'],gate_exit_reason=ns['exit_reason'],gate_exit_us=gate_exit,
            conditional_attribution=foregone,numeric_adoption_check=numerics,gate_actually_exited=gate_exit is not None,
            net_improves=deltas['net_PnL_USDT']>1e-7,
            all_observation_DD_not_worse=deltas['all_observation_max_drawdown']<=1e-10))
    adopted=all(r['gate_actually_exited'] and r['net_improves'] and r['all_observation_DD_not_worse']
        and not r['conditional_attribution']['major_positive_coupon_foregone'] and not r['numeric_adoption_check']['adoption_paused'] for r in results)
    report=dict(status='COMPLETE_D032_SAVED_SUMMARY_CONDITIONAL_ATTRIBUTION_NOT_NATIVE_OR_LONG_TERM_APR',
        created_utc=datetime.now(UTC).isoformat(),binding_path=str(args.binding.resolve()),binding_sha256=binding_sha,
        binding=dict(task_id=os.environ['COIN_TASK_ID'],comparison_binding_path=str(args.binding.resolve()),comparison_binding_sha256=binding_sha,source_sha256=small(__file__)[1]),
        helper_path=str(Path(__file__).resolve()),helper_sha256=small(__file__)[1],task_id=os.environ['COIN_TASK_ID'],
        source_receipt_hashes=small_proofs,actual_closed_task_copies=tasks,gate_rules=GATE_RULES,adoption_criteria=CRITERIA,cases=results,
        research_action='CONTINUE_FIXED_GATE_RESEARCH' if adopted else 'PAUSE_FIXED_GATE_RECIPE_PRESERVE_CAPABILITY',
        economic_adoption_criteria_passed=adopted,economic_adoption_scope='CONDITIONAL_RESEARCH_ONLY_NOT_INVESTMENT_QUALIFICATION',
        numerical_adoption_paused=any(r['numeric_adoption_check']['adoption_paused'] for r in results),
        no_monthly_winner_selection_or_curve_concatenation=True,same_caps_not_equal_realized_risk=True,
        candidate_status='NO_QUALIFIED_CANDIDATE',capital_net_APR='NOT_EVALUABLE',funding_unit_certified=False,
        signal_availability_certified=False,foregone_attribution_is_not_cashflow=True,old_NAV_or_account_replayed=False,
        source_QA_or_CRC_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources=resource_record)
    with out.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=report['status'],output=str(out),sha256=small(out)[1])))

if __name__=='__main__':main()
