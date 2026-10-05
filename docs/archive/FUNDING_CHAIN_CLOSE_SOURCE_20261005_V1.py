"""Close the finite source-to-saved-wallet audit without promoting units."""
import argparse, hashlib, json, os, shutil, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

PARENT='4211222fcf3fc921d4abc13191538189e08a83d4'
PREFIX='FUNDING_CHAIN_20261005_V1'
def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2,ensure_ascii=False); f.write('\n')
def git(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
p=argparse.ArgumentParser(); p.add_argument('action',choices=['close','post']); p.add_argument('--remote-head'); a=p.parse_args()
binding=ROOT/'reports/GITHUB_FUNDING_CHAIN_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json')
assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if a.action=='post':
    b=read(binding); assert git('rev-parse','HEAD')==a.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
    for n,h in b['source_hashes'].items(): assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_FUNDING_CHAIN_STAGED_GATE_20261005_V1.json'
    assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/'reports/GITHUB_FUNDING_CHAIN_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',git_commit=a.remote_head,remote_commit=a.remote_head,parent_commit=PARENT,
        source_binding_sha256=sha(binding),gate_sha256=sha(gate),task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=a.remote_head))); raise SystemExit
assert git('rev-parse','HEAD')==PARENT
protocol=ROOT/'protocols'/f'{PREFIX}.json'; config=read(protocol)
actual=ROOT/'reports/fast_research'/f'{PREFIX}.json'; result=read(actual)
independent=STATE/'d076-funding-independent-20261005-v1/RESULT.json'; reference=read(independent)
assert config['audit_source_sha256']==result['audit_source_sha256']==sha(ROOT/'scripts/investment/audit_saved_funding_chain.py')
assert result['protocol_sha256']==reference['protocol_sha256']==sha(protocol)
assert reference['primary_result_sha256']==sha(actual)
assert result['actual_wallet_events']==reference['total_wallet_events']==14544
assert result['actual_wallets']==len(reference['wallets'])==8
assert not result['funding_unit_certified'] and not reference['archive_units_certified']
assert actual.stat().st_size < config['budget']['maximum_result_bytes']
for wallet in config['wallet_reports']:
    assert sha(wallet['path'])==wallet['sha256']
    original=read(wallet['path'])
    for n in ('scripts/research_v8/funding_price_source_v2.py','scripts/investment/multi_asset_data.py','scripts/investment/perpetual_directional.py','src/quant/perpetual_account.py'):
        if n in original['binding']['source_hashes']:
            assert sha(ROOT/n)==original['binding']['source_hashes'][n],n
live=[]
for pth in Path('/proc').iterdir():
    if not pth.name.isdecimal(): continue
    try:
        argv=(pth/'cmdline').read_bytes().split(b'\0')
        if argv[0] == str(ROOT/'.venv/bin/python').encode() and argv[1:5] in ([b'-u',b'-m',b'quant.microstructure',b'--run'],[b'-u',b'-m',b'quant.collector_public_v3',b'--run']):
            cg=(pth/'cgroup').read_text(); assert 'coin-quant.slice' in cg
            live.append(dict(pid=int(pth.name),argv=[x.decode() for x in argv if x],cgroup=cg.strip()))
    except (OSError,UnicodeError): pass
assert len(live)==2
dest=ROOT/'docs/archive/FUNDING_CHAIN_USED_METADATA_20261005_V1'; dest.mkdir()
tasks=[]
failed=[read(x) for x in (STATE/'task-progress').glob('task-*.json') if read(x).get('title')=='D076 核对真实完成任务并保存结论' and read(x).get('exit_code')==1]
assert len(failed)==1
save(dest/'FAILED_CLOSE_TASK.json',failed[0])
shutil.copyfile(ROOT/'.cache/d076_failed_close_source.py',dest/'failed_close_source.py')
for value in (result,reference):
    task=read(STATE/'task-progress'/('task-'+value['task_id']+'.json'))
    assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']
    save(dest/('task-'+task['id']+'.json'),task); tasks.append(task)
shutil.copyfile(independent,dest/'INDEPENDENT_RESULT.json')
shutil.copyfile(ROOT/'.cache/d076_independent_review.py',dest/'independent_review.py')
summary=('D076已独立读20份BTC/ETH原资金费归档、1818原事件，与HOLD8/固定组合8保存钱包14544条资金费/真实先前成交逐项核对；'
    '缩放一次、ms原clock、符号、event前仓位与严格过去mark时间/总资金费及净桥一致。另按BUY/SELL gross量/首持仓clock重建quantity，'
    '10k+成交cash_delta+资金费重建8末NAV，未将抵押物记利润。未发现错误，原账户/策略不改；单位物理定义/官方结算发布clock仍UNCONFIRMED，'
    'source校验与条件账本通过不能升级原生/单位认证，已有403/451不重试。BASE/F组合比HOLD8多付14.05USDT资金费，四情景净仍低，'
    '非重复入账或符号问题。保留HOLD8收益参照/组合防御挑战者，投资NONE/CASH、长期APR不可评价。主0.817s/RSS75.37MB，'
    '独立0.351s/RSS29.74MB；0新回放/fit/HPO/API/下载，原5GB/swap0/GPU0/40GB保持。'
    '停止无新来源证据的单位调查；下一先核对同窗BTC/ETH Spot源与现有库存/收到资产扣费入口，齐全后以真实产品价格和完整本金做一组有限Spot/永续HOLD对照，'
    '判断资金费负担与额外现货成本/基差影响，不把旧永续账本删除资金费改叫现货。尚未启动。')
doc='''# D076：资金费原字段到保存钱包的有限核对

'''+summary+'''

## 问题、改变与结论

新增一个直接读取已接受原CSV与保存账本的小型审计入口，未复制账户或修改策略。原20份资金源校验和/SHA、1818数值/事件逐项一致；calc_time按ms×1000，保留归档毫秒偏移而不强制移回整点。原始数值转换为float64后未换单位；本样本Decimal原文本与float round-trip文本差最大0，不代表binary float在数学上精确保留所有十进制小数。两种条件scale只在结算入口应用一次。

主核对从早于event的实际position_delta重建quantity，子agent独立实现另以BUY/SELL gross_quantity与首次持仓clock重建，资金费在同刻成交之前。1816持仓事件/每钱包、2无过去mark零仓事件均一致；负rate给多头正收入、正rate给多头支出，所有金额按保存Decimal字符串计算。独立重建10k+成交cash_delta+资金费=末NAV，保证金内部划转不进入利润。本样本只有实际多头/现金；参考中正负q手算不宣称重新验收活动空头入口。

| 完整10k、303已见开发日 | HOLD8资金费 USDT | 组合资金费 USDT | 组合−HOLD8净 USDT |
|---|---:|---:|---:|
'''
left={w['case_id']:w for w in result['wallets'] if w['wallet']=='HOLD8'}
for w in result['wallets']:
    if w['wallet']=='BLEND':
        old=left[w['case_id']]
        doc+=f"| {w['case_id'].replace('TWO_ASSET_','')} | {float(old['funding_total_decimal']):.8f} | {float(w['funding_total_decimal']):.8f} | {w['net_USDT']-old['net_USDT']:.8f} |\n"
doc+='''
BASE/F组合原gross多10.70、fee/exec多11.55、资金费多付14.05，净少14.90。单位假设显著影响绝对净值，两条情景为各自重新模拟的真实完整钱包，不能把F资金费后验乘.01替代P回放；本轮只核保存结果，不制造新收益。配对排序在原四条件一致，足以保留防御用途判断，不能据此确认任一单位或长期alpha。

## 官方证据与剩余缺口

本轮有限检索的[官方binance-public-data README](https://github.com/binance/binance-public-data)描述CHECKSUM保证归档完整性，未给出本次fundingRate CSV字段单位定义。[Binance官方资金费说明](https://www.binance.com/en/support/faq/detail/360033525031)说明资金费现金方向与按持仓价值计算的一般公式；该公式不是CSV字段与API同事件数值对应的证明。此前正式API parity请求受访问限制终止，本轮0 API请求、不使用镜像或替代端点绕过。缺口是官方archive物理单位定义，或可合法访问的同币同结算事件官方API/归档值对应；拿到其中明确证据才reopen单位认证。不能根据量级或哪条收益更高选解释。

严格过去mark时间和保存值的计算已核，市场mark原数值QA复用原已接受金融报告，本轮不重读分钟价格，不认证精确官方charge clock、publication、Bybit原生行情/filters/MMR或可交易盈亏。旧F/P报告、失败/API限制及原单位UNKNOWN全部保留，未改写其成功标准。

## 实际运行与复现

主审计与独立复核各一次实际closed0；首次元数据验收把含采集参数的两个进度父进程也计入而拒绝，修正为原.venv准确argv后另行验收，原失败源/closed1任务保存，不重跑科研；输入无新数据/训练/回放。20源zip+CHECKSUM+normalized合计读取65,586B，另读取保存JSON账本；该值不含receipt与wallet文件，也不是磁盘增长。共享峰是当前boot资源组观测366,342,144B而不是隔离本任务峰。最近真实整盘测量28,451,150,938B@2026-10-05T02:17:18.163809+00:00，早于本轮，不将其当新扫描；本轮小报告/代码增长另据selected文件统计，采集增长未精确重扫。

```bash
scripts/with_task_progress.sh --title '资金费来源链路核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/audit_saved_funding_chain.py --protocol protocols/FUNDING_CHAIN_20261005_V1.json --output reports/fast_research/FUNDING_CHAIN_REPLAY_NEW.json
scripts/with_task_progress.sh --title '独立成交现金复核' -- env PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/FUNDING_CHAIN_USED_METADATA_20261005_V1/independent_review.py --protocol protocols/FUNDING_CHAIN_20261005_V1.json --primary-result reports/fast_research/FUNDING_CHAIN_REPLAY_NEW.json --output /home/xflops/coin-state/OWN_NEW_DIRECTORY/RESULT.json
```

历史复现须checkout协议parent_commit，并从本模块提交恢复审计源及协议，形成与本轮相同的运行前工作区；output必须新路径、STATE目录预先新建。主/独立报告及task实际元数据另保存于本模块metadata目录。投资现金、研究参照保持；下一产品对照先验证可用源，不假定已开始或数据齐全。原两路采集本轮验收时实际存活，但该有限观测不是连续健康天或72h保证。Git同步仅按实际远端后验宣布。
'''
with (ROOT/'docs/FUNDING_CHAIN_20261005.md').open('x') as f: f.write(doc)
for n in ('docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md'):
    path=ROOT/n; head,body=path.read_text().split('\n',1)
    path.write_text(head+'\n\n'+summary+'\n\n### D075及以前历史状态（旧下一步按原时点阅读）\n'+body)
for n in ('docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md'):
    with (ROOT/n).open('a') as f: f.write('\n## D076资金费链路已验收\n\n'+summary+'\n')
with (ROOT/'AGENTS.md').open('a') as f: f.write('\n'+summary+'\n')
accept=ROOT/'reports/FUNDING_CHAIN_ACCEPTED_20261005_V1.json'
save(accept,dict(status='SAVED_SOURCE_CHAIN_AND_INDEPENDENT_FULL_CAPITAL_CASH_ACCEPTED_NOT_UNIT_CERTIFICATION',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    result_sha256=sha(actual),independent_result_sha256=sha(independent),actual_completed_scientific_tasks=tasks,live_collectors=live,
    resources=resources.status(),strategy_or_account_changed=False,funding_unit_certified=False,candidate='NONE',investment='CASH'))
for role,value,path in [('MAIN',result,actual),('INDEPENDENT',reference,independent)]:
    event=dict.fromkeys(FIELDS); event.update(event_id='D076-FUNDING-CHAIN:'+role,event_type='CORRECTNESS_DIAGNOSTIC_RESULT',experiment_id='D076-FUNDING-CHAIN',git_commit=PARENT,
        model_family='NONE',fits=0,success_failure='PASS_CONDITIONAL_CHAIN_NOT_PHYSICAL_UNIT_OR_ALPHA',artifact_path=str(path),artifact_sha256=sha(path),
        reason_for_next_experiment='Stop unit investigation without new evidence; assess actual Spot/perpetual product economics on same known window',result_influenced_later_choice=True)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
prior=ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RUNTIME_SYNC_VERIFIED_20261005_V1.json'
wip=read(prior)['prior_WIP_preserved']; assert len(wip)==36
selected={'AGENTS.md','scripts/investment/audit_saved_funding_chain.py','protocols/'+PREFIX+'.json','docs/FUNDING_CHAIN_20261005.md',
    'docs/archive/FUNDING_CHAIN_CLOSE_SOURCE_20261005_V1.py','reports/fast_research/'+PREFIX+'.json','reports/FUNDING_CHAIN_ACCEPTED_20261005_V1.json',
    'docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md',
    'reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir()); assert not selected.intersection(wip)
save(binding,dict(status='D076_CONDITIONAL_FUNDING_CHAIN_ACCEPTED',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,
    selected_file_bytes=sum((ROOT/n).stat().st_size for n in selected),private_SHA_only=private,private_body_read=False,
    candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE'))
print(json.dumps(dict(status='D076_ACCEPTED_NOT_UNIT_OR_ALPHA',paths=len(selected),selected_file_bytes=sum((ROOT/n).stat().st_size for n in selected))))


