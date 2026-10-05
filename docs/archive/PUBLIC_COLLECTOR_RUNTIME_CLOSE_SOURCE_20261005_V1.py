"""Accept finite original-source restoration evidence, without healthy-day claims."""
import argparse,hashlib,json,os,shutil,subprocess,time
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
PARENT='59f3b6232ff648bbb1ca24935e7b650944bcb5d6'
OUT=STATE/'d075-runtime-restoration-20261005-v1'
PREFIX='PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005_V1'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
parser=argparse.ArgumentParser();parser.add_argument('action',choices=('close','post'));parser.add_argument('--remote-head');args=parser.parse_args()
proof=ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RUNTIME_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json');assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action=='post':
 b=read(proof);assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
 assert not git('status','--porcelain=v1','--untracked-files=no')
 assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
 for n,h in b['source_hashes'].items():assert sha(ROOT/n)==h,n
 gate=ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RUNTIME_STAGED_GATE_20261005_V1.json';assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
 save(ROOT/'reports/GITHUB_PUBLIC_COLLECTOR_RUNTIME_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',git_commit=args.remote_head,remote_commit=args.remote_head,parent_commit=PARENT,
  source_binding_sha256=sha(proof),gate_sha256=sha(gate),task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
 print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=args.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
pres=read(OUT/'PRESERVATION.json');identity=read(OUT/'MANIFEST_IDENTITIES.json')
launch=read(OUT/'PUBLIC_COLLECTOR_RESTORE_LAUNCH_20261005_V1.json')
first=read(OUT/'PUBLIC_COLLECTOR_RESTORE_SAMPLE1_20261005_V1.json');last=read(OUT/'PUBLIC_COLLECTOR_RESTORE_SAMPLE2_20261005_V1.json')
assert pres['originals_preserved_stable'] and not pres['original_SQL_opened']
assert identity['exact_files']==identity['checked_files']==identity['required_files']==pres['manifest_count']==2256 and not identity['errors']
assert first['errors']==last['errors']==[]
assert first['public']['session']['id']==last['public']['session']['id']>pres['public']['session']['id']
assert first['microstructure']['checkpoint']['session']==last['microstructure']['checkpoint']['session']!=pres['microstructure']['checkpoint']['session']
assert last['advancement_comparison']['public_heartbeat_delta_ms']>0 and last['advancement_comparison']['micro_checkpoint_delta_us']>0 and last['advancement_comparison']['micro_accepted_events_delta']>0
assert [p['pid'] for p in first['processes']]==[p['pid'] for p in last['processes']]
for n,h in pres['source_hashes'].items():assert sha(ROOT/n)==h,n
holder=read(ROOT/'.cache/d075_holder.json');assert holder['reused'] and not holder['resource_limit_changed']
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
sleepers=[]
for path in Path('/proc').iterdir():
 if not path.name.isdecimal():continue
 try:
  argv=[x.decode() for x in (path/'cmdline').read_bytes().split(b'\0') if x]
  if argv==['/usr/bin/sleep','2147483647']:
   cg=(path/'cgroup').read_text();assert 'coin-quant.slice' in cg
   sleepers.append(dict(pid=int(path.name),cgroup=cg.strip(),RSS_kB=next(s for s in (path/'status').read_text().splitlines() if s.startswith('VmRSS:'))))
 except (OSError,UnicodeError):pass
assert len(sleepers)==1
dest=ROOT/'docs/archive/PUBLIC_COLLECTOR_RUNTIME_USED_METADATA_20261005_V1';dest.mkdir()
roles={};live={}
for role,v in {'preservation':pres,'identities':identity,'launch':launch,'first_sample':first,'second_sample':last}.items():
 t=read(STATE/'task-progress'/('task-'+v['task_id']+'.json'));assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
 roles[role]=t;save(dest/('task-'+t['id']+'.json'),t)
for receipt in last['actual_task_receipts']:
 t=receipt['metadata'];actual=read(STATE/'task-progress'/('task-'+t['id']+'.json'))
 assert actual['status']=='running' and (Path('/proc')/str(t['pid'])).exists()
 live[t['id']]=actual
for name in ('PRESERVATION.json','MANIFEST_IDENTITIES.json','MICRO_MANIFESTS_BEFORE.json','MICRO_CHECKPOINT_BEFORE.json','PUBLIC_COLLECTOR_RESTORE_LAUNCH_20261005_V1.json','PUBLIC_COLLECTOR_RESTORE_SAMPLE1_20261005_V1.json','PUBLIC_COLLECTOR_RESTORE_SAMPLE2_20261005_V1.json'):
 shutil.copyfile(OUT/name,dest/name)
for name in ('d075_preserve.py','d075_manifest.py','d075_restore.py','d075_clock.py','d075_launch_window.py'):
 shutil.copyfile(ROOT/'.cache'/name,dest/name)
save(dest/'holder.json',dict(host=holder,current_boot_id=boot,preserved_boot_id=pres['boot_id'],linux_sleepers=sleepers,scope='ONE_ATTACHED_WSL_CLIENT_TREE_NOT_REBOOT_OR_72H_GUARANTEE'))
gap_pub=(launch['launch_epoch_seconds']-max(r['last_websocket_received_ms'] for r in pres['public']['bars'])/1000)/60
gap_micro=(launch['launch_epoch_seconds']-pres['microstructure']['checkpoint']['asof_us']/1e6)/60
summary=(f"D075原两路公开采集再次退出后已保存49.37MB原文件/两闭合库，2256来源文件108.03MB streaming SHA全同；"
 f"单次原.venv/defaultDB/store/source恢复，新两次实际观测同PID、新session、闭合bars/heartbeat与L1检查点推进，errors[]。"
 f"断档约public{gap_pub:.1f}分钟/L1{gap_micro:.1f}分钟，不拼健康时间；原退出UNKNOWN。保存与恢复间boot_id变化已证实，"
 "systemd服务本身不维持WSL实例存活是官方限制，闲置退出仅可能机制；新增一个正常Windows隐藏WSL前台客户端，内部sleep仍经原bounded共享5GB，"
 "重复调用复用同客户端树，未改系统电源/资源/自动登录，未声称跨Windows重启或72h可靠。N/signed/共享账户与D074负增量结论保持；投资NONE/CASH、APR不可评价。"
 "最近实扫采用启动前容量检查，细节见docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md。下一有限资金费来源/解析/归一化/结算核对，未启动，不继续混合权重网格。")
doc=f'''# D075：恢复原公开采集并保留WSL会话

{summary}

## 实际修复与限定

D074验收发现PID890567/890568不存在。保存前boot_id={pres['boot_id']}，恢复后实际boot_id={boot}，证明期间WSL实例启动身份改变，但原退出码/唯一原因仍UNKNOWN。微软官方说明systemd服务不能单独保持WSL实例存活：[原文来源](https://learn.microsoft.com/en-us/windows/wsl/systemd)（本轮只公开文档检索，无API限制重试）。常驻前台客户端是针对该机制的有限修复，未证明所有重启/崩溃都已解决。

Windows helper `scripts/keep_wsl_research_runtime.ps1`启动或复用一棵隐藏wsl.exe客户端树，内部仅原bounded.sh + sleep；Store版System32 launcher与packaged child按父子身份算一棵，Linux实际仅一个sleep。首次复用检查把父子误判为两份而拒绝，修正后复用同host PID{holder['host_pid']}，没有重复启动或杀别的进程。Windows启动侧仅控制WSL客户端，Python/采集仍在D承载hpc_linux及原5GB/swap0/GPU0守卫内。不创建登录/计划任务、不改电源或用户全局WSL配置；Windows退出/显式终止后的自动恢复未测。

## 保存、来源与独立核对

保存原main/WAL/SHM及可用日志、task、host记录；缺失项按原PRESERVATION清单保留，不捏造文件。SQL只打开衍生副本；两闭合库SQLite backup及quick_check通过，原始文件复核未变化。2256目录成员、bytes与SHA按流式独立核对完全相同；不重复数据QA、不把身份当有效天。{identity['elapsed_seconds']:.2f}s/RSS{identity['process_peak_RSS_bytes']}B。旧2008清单历史不覆盖，新增源仍为L1 v1，不切v2、不重写来源/数据库。

主恢复复用已验收D066薄编排，只改新独占输出/实际2256清单与task匹配的PID+start_ticks，避免新boot复用PID时把旧task当新task。两次采样使用既有状态与直接lifecycle/audit记录核对新会话、源绑定和断档；源哈希与闭合库catalog另独立核对。行情/模型/账户/执行数学未重写，keys/orders/paid/locked/GPU=0。

## 新实时证据

同PID{[p['pid'] for p in last['processes']]}两次存在于原coin-quant.slice；public新session {last['public']['session']['id']}，heartbeat推进{last['advancement_comparison']['public_heartbeat_delta_ms']}ms；L1 checkpoint推进{last['advancement_comparison']['micro_checkpoint_delta_us']}us、accepted events增{last['advancement_comparison']['micro_accepted_events_delta']}。两币闭合接收时间均推进。UNGRACEFUL_PREVIOUS_SESSION/RESTART_GAP原记录保留，约{gap_pub:.1f}/{gap_micro:.1f}分钟不计连续资格。仅采样证明恢复与推进，feature持久化/健康天/72h/alpha全部不据此认证。

启动前guard总{launch['capacity']['total_bytes']}B，另reserve1GB，预计<32GB；这是原容量实扫时刻{launch['capacity']['measured_utc']}，后续live/Git增长未纳入。当前共享资源{json.dumps(resources.status(),ensure_ascii=False)}。原硬5GB/swap0/GPU0和D40/32warn/36stop不变，无新增观察平台。

## 科研决定与交接

D074实际对照仍为HOLD8收益参照/固定组合防御挑战者，三连续段−10.04/+158.98/−163.84USDT、12区间含零；无合格投资候选，保持现金。本模块恢复公开未来输入能力，不制造新收益或资格。下一一次有限资金费单位来源核对，既有HTTP403/451不重试或绕过；未启动市场/训练/HPO。

复现恢复编排见本模块used metadata四阶段脚本及实际清单。不可在现有live数据库重做preserve/launch或重放旧初始化；采集正在真实运行，应先按源码/当前进程接手。正常模块提交推送与精确remote只按后验凭证宣布。
'''
with (ROOT/'docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md').open('x') as f:f.write(doc)
for n in ('README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md'):
 path=ROOT/n;head,body=path.read_text().split('\n',1);path.write_text(head+'\n\n'+summary+'\n\n### D074及以前的历史状态（旧下一步按原时点阅读）\n'+body)
for n in ('docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md'):
 with (ROOT/n).open('a') as f:f.write('\n## D075原采集恢复已验收\n\n'+summary+'\n')
with (ROOT/'AGENTS.md').open('a') as f:f.write('\nD075原source/DB/store两路公开采集已再次保存/2256SHA/单次恢复/两新session推进；断档不拼资格，exit UNKNOWN，boot身份变化已证实。Windows正常keep_wsl_research_runtime仅一棵隐藏客户端树，sleep经原bounded，不改资源/电源/自动登录；有限恢复不等于跨重启/72h可靠。投资NONE/CASH，下一有限资金费单位来源核对未启动；现态与具体证据见docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md。\n')
report=ROOT/'reports'/(PREFIX+'.json');save(report,dict(status='ORIGINAL_PUBLIC_COLLECTORS_RESTORED_WITH_ATTACHED_WSL_CLIENT_NOT_QUALIFICATION',task_id=os.environ['COIN_TASK_ID'],
 parent_commit=PARENT,closed_actual_roles=roles,observed_live_roles=live,holder=holder,boot_id=boot,preserved_boot_id=pres['boot_id'],
 public_gap_minutes=gap_pub,micro_gap_minutes=gap_micro,healthy_gap_splicing=False,real_time_days_certified=0,alpha_eligible=False,orders_sent=0,locked_consumed=False,resources=resources.status()))
event=dict.fromkeys(FIELDS);event.update(event_id='D075-RESTORE:ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id='D075-ORIGINAL-PUBLIC-RUNTIME-RESTORE',git_commit=PARENT,
 model_family='NONE',fits=0,success_failure='RESTORED_NEW_SESSIONS_NOT_REAL_TIME_QUALIFICATION',artifact_path=report.relative_to(ROOT).as_posix(),artifact_sha256=sha(report),reason_for_next_experiment='Finite funding unit provenance audit',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
prior=ROOT/'reports/GITHUB_HOLD_EXIT_BLEND_TIME_SYNC_VERIFIED_20261005_V1.json';wip=read(prior)['prior_WIP_preserved'];assert len(wip)==36
selected={'scripts/keep_wsl_research_runtime.ps1','docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md','docs/archive/PUBLIC_COLLECTOR_RUNTIME_CLOSE_SOURCE_20261005_V1.py','reports/'+PREFIX+'.json',
 'README.md','AGENTS.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
selected.update(p.relative_to(ROOT).as_posix() for p in dest.iterdir());assert not set(wip).intersection(selected)
save(proof,dict(status='D075_ORIGINAL_RUNTIME_RESTORE_ACCEPTED_NOT_QUALIFICATION',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},
 prior_WIP_preserved=wip,private_SHA_only=private,private_body_read=False,live_collectors_left_running=True,models_fit=0,HPO=0,orders_sent=0,investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE'))
print(json.dumps(dict(status='D075_ACCEPTED_NOT_QUALIFICATION',paths=len(selected),public_gap_minutes=gap_pub,micro_gap_minutes=gap_micro)))
