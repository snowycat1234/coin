"""Export completed evidence and an explicitly partial progress snapshot on cloud Linux.

Read-only with respect to live research, model weights, and protected evidence.
Large input data, weights, and minute ledgers are referenced by SHA, not copied.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from modules.transformer_v2.train import sha
from modules.transformer_v3.development_report import compact, half_linearity, regret_comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower():
        raise RuntimeError('Export scientific evidence on the independent cloud server only')
    state, repo, output = (Path(p).resolve() for p in (args.state, args.repo, args.output))
    if output.is_relative_to(state) or output.is_relative_to(repo):
        raise ValueError('Use a separate publication directory; never modify live evidence/source')
    output.mkdir(parents=True, exist_ok=False)
    captured = datetime.now(timezone.utc).isoformat()
    sources = {}

    def read(relative):
        path = state / relative
        raw = path.read_bytes()
        sources[relative] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        return json.loads(raw), raw

    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    def copy(relative, name=None):
        _, raw = read(relative)
        (output / (name or Path(relative).name)).write_bytes(raw)

    pipeline, _ = read('pipeline-progress.json')
    replay, _ = read('replay-progress.json')
    fits, _ = read('POLICY_FIT_PROGRESS.json')
    final, _ = read('POLICY_FINAL_FITS.json')
    analysis, analysis_raw = read('V2_REPLAY_ANALYSIS.json')
    half, _ = read('half-controls/HALF_CONTROL_RESULTS.json')
    partial, _ = read('policy-development/POLICY_DEVELOPMENT_RESULTS.json')
    full, _ = read('V2_BYBIT_LIQUIDATION_REPLAY.json')
    if sources['V2_BYBIT_LIQUIDATION_REPLAY.json']['sha256'] != analysis['replay_results_sha256']:
        raise ValueError('Frozen replay source changed after analysis')
    assert replay['completed'] == 864 and replay['failed'] == 0
    assert fits['status'] == 'COMPLETE' and fits['completed'] == 60
    assert final['status'] == 'COMPLETE' and final['completed'] == 12
    assert half['status'] == 'COMPLETE' and not half['errors'] and len(half['cases']) == 348
    (output / 'V2_REPLAY_ANALYSIS.json').write_bytes(analysis_raw)
    report = state / 'V2_BYBIT_LIQUIDATION_REPORT.md'
    (output / report.name).write_bytes(report.read_bytes())
    sources[report.name] = dict(bytes=report.stat().st_size, sha256=sha(report))
    half_rows = [compact(case, 'HALF') for case in half['cases']]
    partial_rows = [compact(case, case['task']['profile']) for case in partial['cases']]
    write('HALF_CONTROL_COMPACT_RESULTS.json', dict(status='COMPLETE', rows=half_rows,
        total=348, errors=half['errors'], source=sources['half-controls/HALF_CONTROL_RESULTS.json']))
    write('POLICY_DEVELOPMENT_PARTIAL_RESULTS.json', dict(status='PARTIAL_SNAPSHOT_NOT_FINAL',
        captured_at_UTC=captured, completed=len(partial_rows), total=576, errors=partial['errors'],
        rows=partial_rows, selection_permitted=False, source=sources['policy-development/POLICY_DEVELOPMENT_RESULTS.json']))
    evidence=[]
    for group, cases in (('frozen_v2_replay', full['cases']), ('half_controls', half['cases']), ('policy_development_partial', partial['cases'])):
        for case in cases:
            row=dict(group=group, task_id=case['task']['id'])
            for name in ('summary', 'independent_audit'):
                path, digest = case[name + '_path'], case[name + '_sha256']
                if sha(path) != digest:
                    raise ValueError('Saved financial evidence changed: ' + path)
                row[name + '_path'], row[name + '_sha256'] = path, digest
            row['maximum_NAV_error_USDT'] = case['independent_audit']['maximum_NAV_error_USDT']
            evidence.append(row)
    write('WALLET_EVIDENCE_INDEX.json', dict(status='ALL_EXPORTED_COMPLETED_WALLET_SUMMARY_AND_AUDIT_HASHES_CHECKED', rows=evidence,
        large_ledgers_retained_on_server=True, snapshot_not_all_registered_policy_wallets=True))
    write('OLD_MODEL_FULL_HALF_PAIRS.json', dict(status='COMPLETED_OLD_MODEL_RISK_COMPARISON',
        independent_wallets_not_spliced=True,
        pairs=half_linearity([dict(row, profile='FULL') for row in analysis['rows']] + half_rows)))
    records=[]
    for path in sorted((state / 'policy-fits').glob('*/*/*/*/FIT_COMPLETE.json')):
        proof, _ = read(path.relative_to(state).as_posix())
        row=dict(folder=str(path.parent), completion_receipt_sha256=sha(path), completion=proof)
        row['completion'] = {key: value for key, value in proof.items() if key != 'binding'}
        for phase in ('inner', 'refit'):
            result_path = path.parent / phase / 'RESULT.json'
            result, _ = read(result_path.relative_to(state).as_posix())
            for filename, field in (('weights.pt', 'weights_sha256'), ('scaler.npz', 'scaler_sha256')):
                if sha(result_path.parent / filename) != result[field]:
                    raise ValueError('Completed fit artifact changed: ' + str(result_path))
            row[phase] = {key: value for key, value in result.items() if key != 'binding'}
            row[phase + '_receipt_sha256'] = sha(result_path)
        records.append(row)
    assert len(records) == 60
    write('POLICY_DEVELOPMENT_FIT_RECEIPTS.json', dict(status='COMPLETE', completed=60, total=60,
        weights_and_scalers_hash_checked=True, records=records))
    for record in final['results']:
        folder = Path(record['folder'])
        for filename, field in (('weights.pt', 'weights_sha256'), ('scaler.npz', 'scaler_sha256')):
            if sha(folder / filename) != record['result'][field]:
                raise ValueError('Final fit artifact changed')
    copy('POLICY_FINAL_FITS.json')
    for name in ('POLICY_FINAL_FIT_PLAN.json', 'POLICY_TRAIN_BINDING.json', 'POLICY_EXECUTION_CAPACITY.json',
                 'PROTOCOL_COMMIT_RECEIPT.json', 'TRANSFORMER_V3_PROTOCOL_RECEIPT.json',
                 'EVENT_ORDERING_REPAIR_RECEIPT.json', 'COMMITTED_AUTONOMOUS_TESTS.log',
                 'FROZEN_V2_PREDICTION_DIAGNOSTICS.json', 'POLICY_PREDICTION_METRICS.json'):
        if name.endswith('.log'):
            raw = (state / name).read_bytes()
            sources[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            (output / name).write_bytes(raw)
        else:
            copy(name)
    old, _ = read('FROZEN_V2_PREDICTION_DIAGNOSTICS.json')
    new, _ = read('POLICY_PREDICTION_METRICS.json')
    write('POLICY_COMPLETED_PREDICTION_COMPARISON.json', dict(
        status='COMPLETED_FORECAST_DIAGNOSTICS_NOT_ACCOUNT_PROFITABILITY',
        comparisons=regret_comparison(old['rows'], new['rows'])))
    snapshot=dict(status='INTERIM_PUBLICATION_NOT_FINAL_RESEARCH', captured_at_UTC=captured,
        source_HEAD=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
        stage=pipeline, stages=[
            dict(name='frozen_v2_replay', completed=864, total=864, status='COMPLETE'),
            dict(name='old_model_half_controls', completed=348, total=348, status='COMPLETE'),
            dict(name='policy_development_fits', completed=60, total=60, status='COMPLETE'),
            dict(name='fixed_final_past_only_fits', completed=12, total=12, status='COMPLETE'),
            dict(name='policy_development_wallets', completed=len(partial_rows), total=576, status='PARTIAL_SNAPSHOT'),
            dict(name='development_aggregate_and_freeze', status='NOT_RUN_AT_SNAPSHOT'),
            dict(name='imputed_locked_sensitivity_wallets', completed=0, total=400, status='NOT_RUN_AT_SNAPSHOT'),
            dict(name='final_report_and_full_v2_integrity_closeout', status='NOT_RUN_AT_SNAPSHOT')],
        execution_errors=partial['errors'], old_restoration=analysis['restoration_counts'],
        original_incomplete_restored=analysis['restored_original_incomplete'],
        replay_full_calendar_paid_cash=analysis['complete_task_rows'],
        nonliquidating_parity_checks=analysis['nonliquidating_parity_checks'],
        old_neutral_stability_gate_pass=analysis['stable_neutral_gate_pass'],
        investment_qualification='NONE/CASH', final_model_selection='NOT_DONE',
        official_risk_tiers='UNAVAILABLE; CONDITIONAL_MMR005_MMD0',
        original_v2_formal_locked='PRESERVED_NOT_EVALUABLE',
        large_artifacts='RETAINED_ON_SERVER; SHA_REFERENCES_ONLY',
        source_snapshots=sources)
    write('PROGRESS_SNAPSHOT.json', snapshot)
    lines=['# Transformer v3 当前阶段成果（中途快照）', '',
        f'抓取时间（UTC）：{captured}。这是静态快照，服务器继续后台执行。', '',
        '| 模块 | 完成数 | 状态 |', '|---|---:|---|',
        '|旧模型逐仓强平回放|864/864|完成|', '|旧模型半仓位对照|348/348|完成|',
        '|新 policy 开发训练|60/60|完成|', '|固定过去数据最终训练|12/12|完成|',
        f'|新模型开发账户|{len(partial_rows)}/576|进行中，仅发布已完成账户|',
        '|开发汇总与冻结|—|待执行|', '|五种补值假设的后续账户测试|0/400|待执行|',
        '|最终报告与旧证据完整核验|—|待执行|', '',
        '旧111个停机账户恢复108个：96个强平停机、12个旧破产停机均恢复完整回放；3个风险减仓受限仍保留N/E。',
        '864项中861项完整日历且终端现金结算；原720模型账户717项完整。753项原完整且未强平账户完成经济结果一致性核对，没有新增强平触发。',
        f"旧neutral稳定性门槛：{analysis['stable_neutral_gate_pass']}。修好回放不代表策略通过投资门槛。", '',
        '两种新模型的60次开发训练及12次固定过去数据最终训练完成，发布训练记录和权重/scaler SHA；行情、权重及分钟账本仍留服务器。',
        '已完成的预测诊断及新旧regret差异均附表。regret使用日频expert代理，IC、未来价差和命中率不等于真实账户净收益。',
        '半仓位结果和与全仓位配对表已发布；新模型账户表仅是已完成子集，不能用该子集做最终选择或认定盈利。', '',
        '官方risk档位仍不可得，MMR=.005/MMD=0为明确条件假设；原v2正式封存N/E保留。补值测试尚未运行。投资资格仍NONE/CASH。', '',
        '索引：', '',
        '- [真实阶段进度与来源SHA](PROGRESS_SNAPSHOT.json)',
        '- [旧模型强平回放报告](V2_BYBIT_LIQUIDATION_REPORT.md) / [完整864行分析](V2_REPLAY_ANALYSIS.json)',
        '- [348项半仓位账户](HALF_CONTROL_COMPACT_RESULTS.json) / [全仓位与半仓位配对](OLD_MODEL_FULL_HALF_PAIRS.json)',
        '- [60次开发训练记录](POLICY_DEVELOPMENT_FIT_RECEIPTS.json) / [12次最终训练记录](POLICY_FINAL_FITS.json)',
        '- [新模型预测诊断](POLICY_PREDICTION_METRICS.json) / [新旧预测对照](POLICY_COMPLETED_PREDICTION_COMPARISON.json)',
        '- [新模型已完成账户子集](POLICY_DEVELOPMENT_PARTIAL_RESULTS.json)',
        '- [全部已发布账户的独立核验与来源SHA](WALLET_EVIDENCE_INDEX.json)',
        '- [训练前协议提交凭据](PROTOCOL_COMMIT_RECEIPT.json) / [47项已提交源码测试](COMMITTED_AUTONOMOUS_TESTS.log)', '',
        '服务器查看动态进度：`bash /home/ubuntu/coin/watch_transformer_v3.sh`。退出查看器不停止后台任务。']
    (output / 'CURRENT_STAGE_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    files=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(output.iterdir()) if p.is_file()]
    write('PUBLICATION_MANIFEST.json', dict(captured_at_UTC=captured, files=files,
        exporter_sha256=sha(__file__), source_HEAD=snapshot['source_HEAD']))
    print(json.dumps(dict(output=str(output), files=len(files)+1, completed_policy_wallets=len(partial_rows),
        publication_bytes=sum(p.stat().st_size for p in output.iterdir())), ensure_ascii=False))


if __name__ == '__main__':
    main()
