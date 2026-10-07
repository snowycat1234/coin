"""Report every frozen wallet, retaining stopped accounts as explicit N/E rows."""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from modules.transformer_v2.train import atomic,sha
from modules.transformer_v2.report import compact_case,compare

def analyze(cases,reasons,protocol):
    rows=[]
    for c in cases:
        row=compact_case(c);s=c['summary']
        row.update(task_id=c['task']['id'],old_complete=c['old_complete'],old_completion=c['old_completion'],
                   liquidation_count=s['liquidation_count'],liquidation_loss_USDT=s['liquidation_loss_USDT'],
                   liquidation_counts_by_symbol=s['liquidation_counts_by_symbol'],reentry_after_liquidation=s['reentry_after_liquidation'],
                   nonliquidating_economic_parity=c['nonliquidating_economic_parity'],
                   stopped_marked_prefix_NAV_USDT=s['NAV'] if not row['full_calendar_and_paid_cash'] else None)
        rows.append(row)
    index={r['task_id']:r for r in rows};restoration=[]
    for old in reasons:
        new=index[old['task_id']]
        restoration.append(dict(task_id=old['task_id'],old_status=old['account_status'],old_stop_us=old['stop_us'],
            restored_full_calendar_and_paid_cash=new['full_calendar_and_paid_cash'],new_completion=new['native_completion'],
            liquidation_count=new['liquidation_count'],reentries=new['reentry_after_liquidation'],net_USDT=new['net_USDT'],
            new_summary_sha256=new['summary_sha256']))
    groups={}
    for reason in sorted({r['old_status'] for r in restoration}):
        own=[r for r in restoration if r['old_status']==reason]
        groups[reason]=dict(original=len(own),restored=sum(r['restored_full_calendar_and_paid_cash'] for r in own),
                           retained_incomplete=[r['task_id'] for r in own if not r['restored_full_calendar_and_paid_cash']])
    summaries,paired,chosen=compare(rows,protocol)
    important=[r for r in rows if r['family'] in ('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK') and r['seed']=='ENSEMBLE' and r['mapping'] in ('NEUTRAL','COMBINED')]
    counts=Counter();loss=0.
    # Corrected oracle/exposure rows may repeat model targets; never sum duplicates
    # as one wallet or as a unique original-model liquidation statistic.
    original=[r for r in rows if not r['task_id'].startswith(('legacy-controls/','development-exposure/','corrected-oracles/'))]
    for r in original:counts.update(r['liquidation_counts_by_symbol']);loss+=r['liquidation_loss_USDT']
    return dict(status='FROZEN_V2_REPLAY_ANALYZED',task_rows=len(rows),original_model_tasks=len(original),rows=rows,restoration=restoration,
        restoration_counts=groups,restored_original_incomplete=sum(r['restored_full_calendar_and_paid_cash'] for r in restoration),
        original_incomplete=len(reasons),complete_task_rows=sum(r['full_calendar_and_paid_cash'] for r in rows),
        original_complete_model_tasks=sum(r['full_calendar_and_paid_cash'] for r in original),
        nonliquidating_parity_checks=sum(r['nonliquidating_economic_parity'] is True for r in rows),
        previously_complete_new_liquidation=[r['task_id'] for r in rows if r['old_complete'] and r['liquidation_count']],
        original_model_liquidation_count=sum(r['liquidation_count'] for r in original),original_model_liquidation_loss_USDT=loss,
        original_model_liquidation_counts_by_symbol=dict(counts),loss_scope='SUM_OF_SEPARATE_RESET_WALLET_DIAGNOSTICS; NOT_ONE_PORTFOLIO_LOSS',
        important_neutral_combined_windows=important,summaries=summaries,paired_deltas=paired,
        descriptive_v2_rank_choice=dict(family=chosen['family'],mapping=chosen['mapping']),
        stable_neutral_gate_pass=any(s['development_gate_pass'] for s in summaries if s['family'] in ('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK') and s['mapping']=='NEUTRAL'),
        gate_scope='REUSE_V2_REGISTERED_COMMON_SIX_WINDOW_TWO_FUNDING_SEED_STABILITY_GATE; NO_NEW_THRESHOLDS',
        no_stopped_account_return_imputed=True,no_new_fits=True,no_locked_economics=True,
        certification='CONDITIONAL_BYBIT_STYLE_MINUTE_MARK_AND_LEGACY005_MMR; NATIVE_RISK_SNAPSHOT_UNAVAILABLE')

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);a=p.parse_args();state=Path(a.state)
    source=state/'V2_BYBIT_LIQUIDATION_REPLAY.json';data=json.loads(source.read_text())
    if data['status']!='COMPLETE' or data['errors'] or len(data['cases'])!=864:raise RuntimeError('All frozen replay tasks must finish before analysis and v3 release')
    for c in data['cases']:
        if sha(c['summary_path'])!=c['summary_sha256'] or sha(c['independent_audit_path'])!=c['independent_audit_sha256']:raise ValueError('Saved wallet proof changed')
    repo=Path(__file__).resolve().parents[2];protocol=json.loads((repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json').read_text())
    reasons=json.loads((state/'V2_INCOMPLETE_REASONS.json').read_text())['rows'];result=analyze(data['cases'],reasons,protocol)
    result.update(replay_results_sha256=sha(source),analysis_source_sha256=sha(__file__),v2_protection_receipt_sha256=sha(state/'PHASE0_V2_PRESERVATION.json'))
    dest=state/'V2_REPLAY_ANALYSIS.json'
    if dest.exists():raise RuntimeError('Preserve previous replay analysis')
    atomic(dest,result)
    lines=['# Frozen v2 isolated-liquidation replay','',result['certification'],'',
           f"Actual replay rows {result['task_rows']}; full calendar + paid terminal cash {result['complete_task_rows']}. Original720 full {result['original_complete_model_tasks']}/720.",
           f"Original111 restored {result['restored_original_incomplete']}/111; per reason {json.dumps(result['restoration_counts'])}.",
           f"Previously complete non-liquidating parity checks: {result['nonliquidating_parity_checks']}; new triggers on previously complete accounts: {json.dumps(result['previously_complete_new_liquidation'])}.",
           '', 'Stopped prefixes remain N/E and are present in the complete row table; their marked NAV is not a full-window return. Neither independent wallets nor repeated oracle rows are added into one portfolio.',
           '', '|Model|Mapping|Funding|Window|Complete|Net %|Liq count|Liq loss USDT|Re-entry|Long net|Short net|',
           '|---|---|---:|---|---|---:|---:|---:|---|---:|---:|']
    for r in result['important_neutral_combined_windows']:
        value='N/E' if r['net_return_percent'] is None else f"{r['net_return_percent']:.4f}"
        lines.append(f"|{r['family']}|{r['mapping']}|{r['funding_scale']}|{r['window']}|{r['full_calendar_and_paid_cash']}|{value}|{r['liquidation_count']}|{r['liquidation_loss_USDT']:.4f}|{json.dumps(r['reentry_after_liquidation'])}|{r['long_net_USDT']:.4f}|{r['short_net_USDT']:.4f}|")
    lines.extend(['',f"Registered neutral stability gate: {result['stable_neutral_gate_pass']}.",
                  'Rank metrics describe forecasting; actual wallet fees, funding, liquidation, exposure, MDD, volatility and Sharpe remain separate in V2_REPLAY_ANALYSIS.json.',
                  'This is supplementary v2 evidence. Original v2 final conclusion and formal locked N/E are preserved. No paper-trading promotion at this stage.'])
    (state/'V2_BYBIT_LIQUIDATION_REPORT.md').write_text('\n'.join(lines)+'\n')
    print('REPLAY ANALYSIS',result['restored_original_incomplete'],'of111 restored; native tiers remain uncertified',flush=True)

if __name__=='__main__':main()
