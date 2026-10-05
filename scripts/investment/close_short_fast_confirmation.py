"""One result, one state update and one checkpoint for the finite4h comparison."""
import hashlib, json, os, subprocess
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE
from quant import disk, resources
from scripts.research_v8.registry import FIELDS, append_event


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def main():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    names=['reports/SHORT_FAST4H_BASE27_REVIEW_20261006_V1.json']
    base=json.loads((ROOT/names[0]).read_bytes())
    if base['all_pass']:names.append('reports/SHORT_FAST4H_STRESS43_REVIEW_20261006_V1.json')
    else:assert not (ROOT/'reports/fast_research/SHORT_FAST4H_STRESS43_20261006_V1.json').exists(),'Failed BASE cannot launch stress'
    reviews=[];raws=[];tasks=[];selected=[]
    for name in names:
        r=json.loads((ROOT/name).read_bytes());assert r['status']=='PASS_PAIRED_FAST_SHORT_REVIEW_NOT_INVESTMENT'
        p=ROOT/r['producer']['path'];assert sha(p)==r['producer']['sha256'];raw=json.loads(p.read_bytes())
        for k,h in raw['binding']['source_hashes'].items():assert sha(ROOT/k)==h,k
        assert raw['binding']['git_commit']==head
        for tid in (r['task_id'],r['producer']['task_id']):
            t=json.loads((STATE/'task-progress'/('task-'+tid+'.json')).read_bytes());assert t['status']=='completed' and t['exit_code']==0;tasks.append(t)
        reviews.append(r);raws.append(raw)
        cost=r['pairs'][0]['cost'];selected += [name,r['producer']['path'],f'protocols/SHORT_FAST4H_{cost}_20261006_V1.json']
    passed=all(r['all_pass'] for r in reviews)
    choice='RETAIN_FAST4H_DEVELOPMENT_CHALLENGER' if passed else 'PAUSE_FAST4H_RECIPE_RETAIN_D096'
    next_action='停止本303日的快线周期/阈值调整；将已固定最佳SHORT规则移至另一个完整下跌及随后反弹周期，优先补最小必要历史与透明基准；先核已授权/已有输入、当时可知标的资格与费用，保留两币对照。目的是检验跨周期有效性，不能按当前303日事后赢家声称独立收益。不改变资金/数据封存/风险权限。'
    rows=[v for r in reviews for v in r['pairs']];primary=next(v for v in rows if v['cost']=='BASE27' and v['unit']=='RAW_AS_PERCENT')
    old=primary['reference'];fmt=lambda v:f'{v:.2f}'
    original=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json'
    old_proof=json.loads((ROOT/'reports/SHORT_CONFIRMATION_BASE27_REVIEW_20261006_V1.json').read_bytes())
    assert sha(original)==old_proof['producer']['sha256']
    old_case=next(v for v in json.loads(original.read_bytes())['cases'] if v['unit']=='RAW_AS_PERCENT')
    new_case=next(v for v in raws[0]['cases'] if v['unit']=='RAW_AS_PERCENT')
    component={}
    for label,case in [('D096',old_case),('FAST4H',new_case)]:
        item=case['artifacts']['trades.json'];assert sha(item['path'])==item['sha256']
        trades=json.loads(Path(item['path']).read_bytes())
        component[label]=dict(direction=case['summary']['long_short_marked_contribution'],
            actual_short_episodes=sum(v['quantity_before']==0 and v['quantity_after']<0 for v in trades),
            turnover=case['summary']['normalized_total_turnover'])
    report='reports/SHORT_FAST4H_ACCEPTED_20261006_V1.json'
    result=dict(status='ACCEPTED_FINITE_FAST_SHORT_ACCOUNTS_NOT_INVESTMENT',created_utc=datetime.now(UTC).isoformat(),
        task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),choice=choice,all_predeclared_pass=passed,
        best_research_recipe='DC_CONFIRMED_SHORT_FAST4H' if passed else 'DC_CONFIRMED_SHORT',
        investment='NONE/CASH',long_term_APR='NOT_EVALUABLE',actual_days=303,capital_per_counterfactual_USDT=10000,
        rows=rows,accounts=sum(len(r['cases']) for r in raws),fits=0,configurations=1,search=0,new_market_downloads=0,
        references={p:sha(ROOT/p) for p in selected},money_and_turnover=component,
        original_component_source_sha256=sha(original),next_action=next_action,limitations=base['limitations'])
    save(report,result)
    table=['','## D098：固定4小时确认的完整经济对照','',
        '每币已有日线双通道short须同时获4h20/10确认；先mask再daily signed covariance，日内失去确认只退出、下一日再入场。未训练/搜参/下载新行情。此适配不等于原论文或完整Turtle。', '',
        '|成本/资金费解释|原净USDT|4h净USDT|原SHORT|4hSHORT|原DD%|4hDD%|4hvol%|费用+执行|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in rows:
        table.append('|'+ '|'.join([v['cost']+'/'+v['unit'],fmt(v['reference']['net']),fmt(v['net']),fmt(v['reference']['SHORT']),fmt(v['SHORT']),fmt(v['reference']['DD']*100),fmt(v['DD']*100),fmt(v['vol']*100),fmt(v['fees']+v['execution'])])+'|')
    table += ['',choice+'。BASE两单位通过才做STRESS；实际'+str(result['accounts'])+'账户，均独立完整10k共享10币，不能相加。',
        'BASE/PCT净变动'+fmt(primary['delta']['net'])+'、SHORT变动'+fmt(primary['delta']['SHORT'])+'、LONG变动'+fmt(primary['delta']['LONG'])+'、毛价格变动'+fmt(primary['delta']['gross'])+'、费用+执行变动'+fmt(primary['delta']['fees']+primary['delta']['execution'])+'；这些来自实际新账本，不删成本保留旧收益。',
        'SHORT毛价格损益 '+fmt(component['D096']['direction']['SHORT']['gross'])+' → '+fmt(component['FAST4H']['direction']['SHORT']['gross'])+'；SHORT费用+执行 '+fmt(component['D096']['direction']['SHORT']['fees']+component['D096']['direction']['SHORT']['execution_cost'])+' → '+fmt(component['FAST4H']['direction']['SHORT']['fees']+component['FAST4H']['direction']['SHORT']['execution_cost'])+'。实际空头episodes '+str(component['D096']['actual_short_episodes'])+' → '+str(component['FAST4H']['actual_short_episodes'])+'，归一换手 '+fmt(component['D096']['turnover'])+' → '+fmt(component['FAST4H']['turnover'])+'。因此不只是成本吃掉同一毛收益；该完整适配改变了持仓路径、降低SHORT毛收益并增加成本。',
        '原/新BEAR标签SHORT '+fmt(old['regimes']['BEAR']['SHORT'])+'/'+fmt(primary['regimes']['BEAR']['SHORT'])+'；BULL '+fmt(old['regimes']['BULL']['SHORT'])+'/'+fmt(primary['regimes']['BULL']['SHORT'])+'；SIDEWAYS '+fmt(old['regimes']['SIDEWAYS']['SHORT'])+'/'+fmt(primary['regimes']['SIDEWAYS']['SHORT'])+'。只是既有滞后BTC描述，不是每币真实牛熊、不能证明未来熊市赚钱。',
        '实际SHORT保护退出成交片段'+str(primary['short_exit_fill_fragments'])+'；原正forecast保持，实际LONG可因covariance与资金竞争变化。关闭原长仓的反手清理单独记录 '+str(primary['long_cleanup_fill_fragments'])+'，不把其收益冒充short贡献。',
        '首20个4h完成bar不足时SHORT空仓，未给未知补值。两个BASE完整303日；真实fee/滑点/容量/风险/资金费保留，marked和付费清仓口径分别记录。',
        '公开fast信号独立标量reference与真实小型延迟/部分成交/硬风险反例通过；实际账户沿用独立Decimal钱包/NAV、ordered signed covariance核对。首轮测试字段范围错误保留V1，未为其修改财务内核。',
        '',next_action,'', '结果 `'+report+'` SHA256 `'+sha(ROOT/report)+'`。',
        '复现：经现有progress/bounded、2线程、D-hosted runtime运行 `scripts/investment/run_cta_leaderboard.py --protocol protocols/SHORT_FAST4H_BASE27_20261006_V1.json --run-dir /home/xflops/coin-state/REPLACE_WITH_UNUSED --output reports/fast_research/REPLACE_WITH_UNUSED.json`。原run/output不可覆盖。','']
    with (ROOT/'docs/SHORT_SELECTION.md').open('a') as f:f.write('\n'.join(table))
    state=(ROOT/'docs/RESEARCH_STATUS.md').read_text()
    a=state.index('## 最新定位与下一有限工作');b=state.index('## 数据、风险与资源')
    state=state[:a]+'## 最新结果与下一有限工作\n\nD098完成固定4h short确认的'+str(result['accounts'])+'个实际303日账户，0训练/搜索/新行情。'+choice+'；BASE/PCT新净'+fmt(primary['net'])+'（原'+fmt(old['net'])+'），SHORT '+fmt(primary['SHORT'])+'（原'+fmt(old['SHORT'])+'），vol '+fmt(primary['vol']*100)+'%、分钟DD '+fmt(primary['DD']*100)+'%。不是旧账本删交易；完整资本、方向/成本、过去状态与实际风险见 [SHORT研究](SHORT_SELECTION.md)。\n\n'+next_action+'\n\nD097已证明：旧10日线提高频率不能覆盖主要反弹，Chandelier默认完整24次持仓11次可更早触发但4月9日八仓仍未覆盖，保留备用、完整新CE经济账户NOT_RUN。能力不删除；暂停4h配方时reopen需新独立周期或具体噪音/持仓语义机制，不能同窗扫周期救参。\n\n'+state[b:]
    (ROOT/'docs/RESEARCH_STATUS.md').write_text(state)
    with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n\n## D098结果与决定\n\n'+choice+'；一配方、'+str(result['accounts'])+'真实账户、0拟合/搜参/新行情；BASE/PCT净'+fmt(primary['net'])+'（变化'+fmt(primary['delta']['net'])+'），SHORT '+fmt(primary['SHORT'])+'（变化'+fmt(primary['delta']['SHORT'])+'），vol '+fmt(primary['vol']*100)+'% DD '+fmt(primary['DD']*100)+'%。毛价格变化'+fmt(primary['delta']['gross'])+'，费用+执行变化'+fmt(primary['delta']['fees']+primary['delta']['execution'])+'。投资NONE/CASH，当前窗口仍开发、单位/原生规则假设保留。'+next_action+' 工件 '+report+' SHA '+sha(ROOT/report)+'。\n')
    event=dict.fromkeys(FIELDS);event.update(experiment_id=raws[0]['protocol']['experiment_id'],event_id='D098:DECISION',event_type='OPERATIONAL_RESEARCH_DECISION',git_commit=head,model_family='PUBLIC_DC_DAILY_PLUS_FIXED4H_CONFIRMATION',models_fit=0,success_failure=choice,artifact_path=report,artifact_sha256=sha(ROOT/report),result_influenced_later_choice=True,reason_for_next_experiment=next_action);append_event(ROOT/'reports/experiment_registry.jsonl',event)
    for p in (STATE/'task-progress').glob('task-*.json'):
        t=json.loads(p.read_bytes())
        if t.get('title','').startswith('SHORT4h') and t.get('status') in ('completed','failed') and t['started_at']>datetime(2026,10,5,17,50,tzinfo=UTC).timestamp():tasks.append(t)
    unique={t['id']:t for t in tasks};intervals=[]
    for t in sorted(unique.values(),key=lambda t:t['started_at']):
        a,b=t['started_at'],t['ended_at']
        if intervals and a<=intervals[-1][1]:intervals[-1][1]=max(b,intervals[-1][1])
        else:intervals.append([a,b])
    print('SHORT4h模块收尾磁盘实扫；总量未知',flush=True)
    scan=dict(disk.check(),measured_utc=datetime.now(UTC).isoformat());closed='reports/SHORT_FAST4H_MODULE_CLOSED_20261006_V1.json'
    save(closed,dict(status='COMPLETE_FINITE_SHORT_FAST_RULE_ACTUAL_ACCOUNTS',accepted_sha256=sha(ROOT/report),choice=choice,
        task_intervals_union_seconds=sum(b-a for a,b in intervals),tasks=[{k:t.get(k) for k in ('id','title','started_at','ended_at','exit_code')} for t in unique.values()],
        stage_timing_scope='RELATED_TASK_INTERVAL_UNION_NOT_WHOLE_TURN_THINKING_TIME',
        producer_computation_seconds=sum(r['elapsed_seconds'] for r in raws),
        peak_RSS_bytes=max(r['peak_RSS_bytes'] for r in raws),shared_sampled_peak=max(r['shared_RAM_sampled_peak_bytes'] for r in raws),
        owned_new_replay_bytes=sum(r['owned_bytes'] for r in raws),disk_scan=scan,resources=resources.status(),
        recipe_configurations=1,accounts=result['accounts'],fits=0,new_markets=0,locked_body_read=False))
    p=STATE/'task-progress/last-disk.json';tmp=p.with_suffix('.D098.tmp');tmp.write_text(json.dumps(dict(ledger=scan,measured_at=datetime.fromisoformat(scan['measured_utc']).timestamp(),source=closed)));tmp.replace(p)
    selected += [report,closed,'scripts/investment/short_fast_confirmation.py','scripts/investment/run_cta_leaderboard.py',
        'scripts/investment/review_short_fast_confirmation.py','scripts/investment/close_short_fast_confirmation.py',
        'tests/test_short_fast_confirmation.py','reports/SHORT_FAST4H_TESTS_20261006_V1.xml','reports/SHORT_FAST4H_TESTS_20261006_V2.xml',
        'docs/SHORT_SELECTION.md','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md',
        'reports/experiment_registry.jsonl','reports/GITHUB_SHORT_REBOUND_SYNC_VERIFIED_20261006_V1.json']
    binding='reports/GITHUB_SHORT_FAST4H_SOURCE_BINDING_20261006_V1.json'
    prior=json.loads((ROOT/'reports/GITHUB_SHORT_REBOUND_SOURCE_BINDING_20261006_V2.json').read_bytes())['prior_WIP_preserved']
    save(binding,dict(status='ACCEPTED_MODULE_SOURCE_BINDING',parent_commit=head,selected_module_paths=selected+[binding],
        source_hashes={p:sha(ROOT/p) for p in set(selected)|set(raws[0]['binding']['source_hashes'])},prior_WIP_preserved=prior,locked_body_read=False))
    (ROOT/'.cache/stage_selected_short_fast4h.ps1').write_text("$ErrorActionPreference = 'Stop'\n$paths = @(\n"+',\n'.join("'"+p+"'" for p in selected+[binding])+"\n)\n& git.exe -C 'D:/codex/coin' add -- $paths\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n")
    print(json.dumps(dict(choice=choice,net=primary['net'],SHORT=primary['SHORT'],accounts=result['accounts'],disk_bytes=scan['total_bytes'])))


if __name__=='__main__':main()
