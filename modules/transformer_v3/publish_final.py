"""Publish completed research reports without rerunning fits or economic wallets."""
import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from modules.transformer_v2.train import sha


def main():
    parser = argparse.ArgumentParser()
    for name in ('state', 'repo', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower():
        raise RuntimeError('Independent cloud Linux only')
    state, repo, out = (Path(p).resolve() for p in (args.state, args.repo, args.output))
    if out.is_relative_to(state) or out.is_relative_to(repo):
        raise ValueError('Publication must not modify science state or execution source')
    out.mkdir(parents=True, exist_ok=False)
    captured=datetime.now(timezone.utc).isoformat()
    sources={}

    def read(relative):
        raw=(state / relative).read_bytes()
        sources[relative]=dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        return json.loads(raw)

    def write(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    pipeline=read('pipeline-progress.json')
    if pipeline['stage']!='COMPLETE_SERVER_RESEARCH_AND_PROTECTED_EVIDENCE_AUDIT':
        raise ValueError('All research and protected-evidence verification must finish first')
    final=read('TRANSFORMER_V3_FINAL_RESULTS.json')
    dev=read('TRANSFORMER_V3_DEV_RESULTS.json')
    release=read('LOCKED_DEVELOPMENT_FREEZE.json')
    preserve=read('FINAL_V2_PRESERVATION_AUDIT.json')
    if preserve['status']!='PASS_ALL_PROTECTED_V2_BYTES_UNCHANGED' or preserve['files']!=16025:
        raise ValueError('Full original-evidence closeout required')
    if final['status']!='FINAL_IMPUTED_LOCKED_SENSITIVITY_COMPLETE' or final['locked_accounts']!=400:
        raise ValueError('Final research is not complete')
    if final['development_results_sha256']!=sources['TRANSFORMER_V3_DEV_RESULTS.json']['sha256']:
        raise ValueError('Final development evidence identity changed')
    if release['development_results_sha256']!=final['development_results_sha256'] or final['chosen']!=release['chosen']:
        raise ValueError('Final choice differs from pre-locked freeze')
    if final['locked_development_freeze_sha256']!=sources['LOCKED_DEVELOPMENT_FREEZE.json']['sha256']:
        raise ValueError('Pre-locked freeze changed')
    if len(dev['rows'])!=1788 or len(final['rows'])!=400:
        raise ValueError('All registered rows including N/E must be retained')
    if sum(r['full_calendar_and_paid_cash'] for r in final['rows'])!=final['complete_locked_accounts']:
        raise ValueError('Final complete count mismatch')
    if [a['question'] for a in final['answers']]!=list(range(1,12)):
        raise ValueError('All eleven scientific answers required')
    for relative, digest in dev['sources'].items():
        if sha(state / relative)!=digest:
            raise ValueError('Frozen development input changed: '+relative)
    for key, filename in (('replay_analysis_sha256','V2_REPLAY_ANALYSIS.json'),
                          ('locked_evidence_sha256','IMPUTED_LOCKED_SENSITIVITY.json')):
        if sha(state / filename)!=final[key]:
            raise ValueError('Final input evidence identity changed: '+filename)
    if sha(repo / 'modules/transformer_v3/final_report.py')!=final['source_sha256']:
        raise ValueError('Final report source identity changed')
    for item in release['frozen_weights_and_scalers']:
        if sha(item['path'])!=item['sha256']:
            raise ValueError('Protected released model artifact changed')
    index=[]
    groups=(('v2_full','V2_BYBIT_LIQUIDATION_REPLAY.json',864),
            ('v2_half','half-controls/HALF_CONTROL_RESULTS.json',348),
            ('v3_development','policy-development/POLICY_DEVELOPMENT_RESULTS.json',576),
            ('imputed_locked','IMPUTED_LOCKED_SENSITIVITY.json',400))
    for group, filename, count in groups:
        data=read(filename)
        if len(data['cases'])!=count or data.get('errors'):
            raise ValueError('Missing registered execution: '+group)
        for case in data['cases']:
            task=case['task']
            item=dict(group=group, task_id=task['id'],
                full_calendar_and_paid_cash=case['economic_calendar_complete'] and case['terminal_cash_realized'],
                completion=case['summary']['completion'], maximum_NAV_error_USDT=case['independent_audit']['maximum_NAV_error_USDT'])
            for kind in ('summary', 'independent_audit'):
                path, digest=case[kind+'_path'], case[kind+'_sha256']
                if sha(path)!=digest:
                    raise ValueError('Saved financial proof changed: '+path)
                item[kind+'_path'], item[kind+'_sha256']=path, digest
            if sha(task['target_path'])!=task['target_sha256']:
                raise ValueError('Saved causal/noncausal target identity changed')
            item['target_path'],item['target_sha256']=task['target_path'],task['target_sha256']
            index.append(item)
        del data
    assert len(index)==2188
    write('FINAL_WALLET_EVIDENCE_INDEX.json',dict(status='PASS_ALL_2188_REGISTERED_SUMMARIES_AUDITS_AND_TARGET_IDENTITIES',
        rows=index, count=len(index), separate_reset_wallets_not_one_portfolio=True))
    exports=('TRANSFORMER_V3_FINAL_REPORT.md','TRANSFORMER_V3_FINAL_RESULTS.json',
             'TRANSFORMER_V3_DEV_REPORT.md','TRANSFORMER_V3_DEV_RESULTS.json',
             'LOCKED_DEVELOPMENT_FREEZE.json','FINAL_V2_PRESERVATION_AUDIT.json',
             'BRIDGE_BASE_MANIFEST.json','PROTOCOL_COMMIT_RECEIPT.json','POLICY_FIT_PROGRESS.json')
    for name in exports:
        raw=(state / name).read_bytes()
        if name in sources and hashlib.sha256(raw).hexdigest()!=sources[name]['sha256']:
            raise ValueError('Completed export changed during publication')
        sources[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (out / name).write_bytes(raw)
    write('FINAL_PIPELINE_PROGRESS.json',pipeline)
    columns=('scenario','family','seed','mapping','profile','funding_scale','window','days',
        'full_calendar_and_paid_cash','native_completion','net_USDT','net_return_percent','gross_price_USDT',
        'fees_USDT','spread_USDT','slippage_USDT','execution_cost_USDT','funding_USDT','turnover_USDT','Sharpe',
        'realized_vol','MDD','mean_gross','mean_signed_exposure','long_net_USDT','short_net_USDT',
        'liquidation_count','liquidation_loss_USDT','summary_sha256')
    for name, rows in (('TRANSFORMER_V3_DEV_ROWS.csv',dev['rows']),('TRANSFORMER_V3_LOCKED_ROWS.csv',final['rows'])):
        with (out / name).open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=columns,extrasaction='ignore',lineterminator='\n')
            writer.writeheader()
            for row in rows:
                writer.writerow({k:('N/E' if row.get(k) is None and k in ('net_USDT','net_return_percent') else row.get(k,'')) for k in columns})
    incomplete=[dict(scope=scope,task_id=r['task_id'],family=r['family'],mapping=r['mapping'],profile=r['profile'],
        funding_scale=r['funding_scale'],scenario=r.get('scenario'),window=r['window'],completion=r['native_completion'],
        completed_minutes=r['completed_minutes'],required_minutes=r['required_minutes'],net_USDT=r['net_USDT'])
        for scope,rows in (('development',dev['rows']),('imputed_locked',final['rows'])) for r in rows if not r['full_calendar_and_paid_cash']]
    write('FINAL_NOT_EVALUABLE_ROWS.json',dict(status='PRESERVED_N_E_NOT_FAILED_SCRIPT_AND_NOT_FULL_RETURN',rows=incomplete))
    lines=['# Transformer v3 最终交付', '', '**B. CONTINUE RESEARCH；不晋级，投资状态 NONE/CASH。**', '',
        f'发布抓取时间（UTC）：{captured}。所有后台模块正常完成，服务器不再训练或回放。', '',
        '|模块|实际执行|完整日历且收费终值现金|', '|---|---:|---:|',
        '|旧模型强平回放|864/864|861/864|',
        '|旧模型HALF对照及新开发账户|348/348、576/576|与旧回放合计1782/1788|',
        '|开发训练／固定过去数据最终训练|60/60、12/12|训练完成不代表盈利|',
        '|五种补值×两种资金费口径后续账户|400/400|395/400|', '',
        '未完整账户均保留N/E，不把停机前缀当完整收益。执行完成数与经济完整数分别报告。', '',
        '冻结候选：ORACLE_POLICY_CROSS_ASSET / NEUTRAL / FULL。模型及仓位选择在后续测试前冻结。', '',
        '|资金费scale|五方案净收益率 min / median / max|五方案净USDT min / median / max|', '|---:|---|---|']
    for row in final['headline_selected_min_median_max']:
        def triple(key):
            return ' / '.join(f"{row['statistics'][key][q]:.4f}" for q in ('min','median','max'))
        lines.append(f"|{row['funding_scale']}|{triple('net_return_percent')}|{triple('net_USDT')}|")
    lines += ['', '两个资金费口径下均亏损，五种补值方案均未通过经济门槛；开发期候选门槛也未通过。LONG为正、SHORT为负，封存期所选每个独立账户均有一次1000SATS强平并在正常时点重新入场。',
        'B来自事前登记的描述性排名信号，不能解释为策略已合格；新policy的日频expert代理regret改善未通过预设跨fold门槛。', '',
        '旧111个停机账户恢复108个：96个强平与12个旧破产停机均恢复，3个容量受限风险减仓保持N/E。',
        '最终重新核对16,025个旧v2保护文件、33,182,604,674字节，全部SHA保持不变。旧正式封存N/E和负结果永久保留。',
        '官方risk档位缺失，MMR=.005/MMD=0为条件假设。五种补值只是敏感性实验，没有恢复精确交易所事件；未执行真实订单或paper部署。', '',
        '- [最终报告：11个问题](TRANSFORMER_V3_FINAL_REPORT.md)',
        '- [全部400行后续结果及五方案范围](TRANSFORMER_V3_FINAL_RESULTS.json) / [CSV](TRANSFORMER_V3_LOCKED_ROWS.csv)',
        '- [开发比较报告](TRANSFORMER_V3_DEV_REPORT.md) / [1788行开发结果](TRANSFORMER_V3_DEV_RESULTS.json) / [CSV](TRANSFORMER_V3_DEV_ROWS.csv)',
        '- [不可评价账户原因](FINAL_NOT_EVALUABLE_ROWS.json)',
        '- [2188项账户摘要、独立审计、目标身份校验](FINAL_WALLET_EVIDENCE_INDEX.json)',
        '- [后续测试前冻结凭据](LOCKED_DEVELOPMENT_FREEZE.json) / [旧证据最终完整性](FINAL_V2_PRESERVATION_AUDIT.json)',
        '- [本次发布逐文件SHA](FINAL_PUBLICATION_MANIFEST.json)', '',
        '行情、模型权重、环境和分钟大账本留服务器；本次发布没有重跑任何训练或经济账户。先前190/576静态阶段快照保留供追溯。']
    (out / 'FINAL_DELIVERY_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()]
    write('FINAL_PUBLICATION_MANIFEST.json',dict(status='VERIFIED_COMPLETED_RESEARCH_PUBLICATION',captured_at_UTC=captured,
        source_HEAD=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
        exporter_sha256=sha(__file__),files=files,science_sources=sources,
        no_training_or_economic_replay=True,all_2188_summary_audit_target_hashes_verified=True,
        all_frozen_released_weights_and_scalers_verified=True,
        maximum_independent_NAV_error_USDT=max(r['maximum_NAV_error_USDT'] for r in index),
        protected_v2_integrity=preserve))
    print(json.dumps(dict(output=str(out),files=len(files)+1,total_bytes=sum(p.stat().st_size for p in out.iterdir()),
        decision=final['decision'],registered_wallets=2188,complete_locked=final['complete_locked_accounts']),ensure_ascii=False))


if __name__=='__main__':
    main()
