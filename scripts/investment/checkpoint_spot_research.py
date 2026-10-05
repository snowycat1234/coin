"""Small reusable publication step for an accepted immutable Spot experiment."""
import argparse,hashlib,json,os,shutil,subprocess,time
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import FIELDS,append_event

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();began=time.monotonic()
c=read(a.config);accept=read(ROOT/c['acceptance']);assert accept['status']=='ACTUAL_SPOT_RESEARCH_ACCEPTED'
assert git('rev-parse','HEAD')==accept['parent_commit']==c['parent_commit']
for r in accept['references'].values():assert sha(r['path'])==r['sha256']
v=read(accept['references']['result']['path']);protocol=read(accept['references']['protocol']['path'])
assert c['module']==protocol['module'] and c['decision']['adopted']==accept['development_recipe_adopted']
archive=ROOT/c['archive'];archive.mkdir()
for source,name in c['archive_copies']:
    p=Path(source);p=p if p.is_absolute() else ROOT/p
    assert p.resolve().is_relative_to(ROOT) or p.resolve().is_relative_to(STATE)
    assert p.suffix not in ('.parquet','.sqlite','.db','.vhdx','.log') and p.stat().st_size<4_000_000
    assert Path(name).name==name
    shutil.copyfile(p,archive/name)
tasks={}
for role,tid in c['task_ids'].items():
    p=STATE/'task-progress'/('task-'+tid+'.json');t=read(p)
    expected=c.get('expected_exit_codes',{}).get(role,0)
    assert t['ended_at'] and t['exit_code']==expected and t['status']==('failed' if expected else 'completed')
    tasks[role]=dict(id=tid,title=t['title'],started_at=t['started_at'],ended_at=t['ended_at'],exit_code=t['exit_code'])
    shutil.copyfile(p,archive/p.name)
for role,paths in c.get('attempts',{}).items():
    event=dict.fromkeys(FIELDS);event.update(event_id=c['module']+':'+role,event_type='OPERATIONAL_RESEARCH_RESULT',
        experiment_id=protocol['experiment_id'],git_commit=c['parent_commit'],model_family=c.get('attempt_model_family','CAUSAL_TARGET_FIXTURE_NOT_MODEL'),fits=0,
        success_failure=tasks[role]['title']+':EXIT_'+str(tasks[role]['exit_code']),artifact_path=(archive/paths).relative_to(ROOT).as_posix(),
        artifact_sha256=sha(archive/paths),reason_for_next_experiment=c.get('attempt_reason','Fixture construction verified; no producer change or parameter search'))
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
controls=read(protocol['spot_control']['path']);daily=read(protocol['economic_reference']['path']) if protocol.get('economic_reference') else None
for r in (protocol['spot_control'],protocol.get('economic_reference')):
    if r is not None:assert sha(r['path'])==r['sha256']
doc='# '+c['module']+'：'+c['title']+'\n\n'+c['decision']['summary']+'\n\n'
assert len(v['cases'])==len(controls['cases'])==2
cols=[controls['cases'][0],v['cases'][0],controls['cases'][1],v['cases'][1]]
capital=cols[0]['config']['initial_cash'];assert all(x['config']['initial_cash']==capital for x in cols)
doc+=f"## 同市场与完整资本对照\n\n{v['actual_calendar_days']}已见开发日、共享{capital:,.0f} USDT、Binance Spot价格配Bybit用户VIP0费用，非Bybit原生证据。\n\n"
doc+='| 指标 | 控制 '+cols[0]['id']+' | 新配方 '+cols[1]['id']+' | 控制 '+cols[2]['id']+' | 新配方 '+cols[3]['id']+' |\n|---|---:|---:|---:|---:|\n'
for label,fn in [('marked净USDT',lambda x:x['summary']['final_nav']-capital),('同数量成本加回gross诊断',lambda x:x['summary']['gross_pnl_before_costs']),('费用USDT',lambda x:x['summary']['fees']),('执行成本USDT',lambda x:x['summary']['execution_costs']),('日收益年化波动%',lambda x:x['summary']['annual_volatility']*100),('日终MDD%',lambda x:x['summary']['max_drawdown']*100),('分钟MDD%',lambda x:x['risk']['minute_max_drawdown']*100),('成交数',lambda x:x['summary']['trade_count']),('换手/本金',lambda x:x['turnover_over_full_initial_capital']),('平均gross%',lambda x:x['risk']['minute_mean_gross_weight']*100),('平均net%',lambda x:x['risk']['minute_mean_net_weight']*100),('峰gross%',lambda x:x['risk']['minute_max_gross_weight']*100),('峰单币%',lambda x:x['risk']['minute_max_asset_weight']*100)]:
    doc+='| '+label+' | '+' | '.join(f'{fn(x):.6f}' for x in cols)+' |\n'
if daily is not None:doc+='\n保存经济参照净'+','.join(f"{x['summary']['final_nav']-x['config']['initial_cash']:.6f}" for x in daily['cases'])+'USDT。\n'
doc+='\n当前两个新账户保留正库存价值'+','.join(f"{x['terminal_marked_inventory_USDT']:.9f}" for x in v['cases'])+'USDT，liquidated return='+','.join(x['liquidated_return'] for x in v['cases'])+'。\n\n'+c['notes']+'\n\n'
doc+='## 工件与可复现命令\n\n'
for role,r in accept['references'].items():doc+=f"- {role}: `{r['path']}`，SHA `{r['sha256']}`。\n"
doc+='\n```bash\n'+c['reproducible_command']+'\n```\n'
with (ROOT/c['report_document']).open('x') as f:f.write(doc)
status=('# COIN 当前研究状态\n\n投资资格：**NONE/CASH**；长期APR **NOT_EVALUABLE**。\n\n'
        '研究参照：Spot HOLD8；防御挑战者：Spot日线固定50/50 HOLD10+EXIT10；N资产和永续signed能力保留。\n\n'
        '## 最新证据与决定\n\n'+c['decision']['summary']+'\n\n报告：['+c['module']+']('+Path(c['report_document']).name+')；结构化验收：`'+c['acceptance']+'`。\n\n'
        '## 当前工作与下一选择\n\n本轮市场回放与必要复核已结束。'+c['decision']['next']+'\n\n'
        '## 适用范围\n\n本轮及此前已查看的历史为开发筛选；跨场所成本代理、数量/最低订单历史规则、残仓、瞬时风险/清算及独立证据仍按各报告限定。未开启locked/真钱/keys/发单/付费/GPU；共享5GB、swap0、D总40GB及原风险caps不变。\n\n'
        '此前状态按Git保留；实验与负结果见 `../reports/experiment_registry.jsonl` 和 `RESEARCH_DECISION_LOG.md`。\n')
(ROOT/'docs/RESEARCH_STATUS.md').write_text(status)
for n in c.get('progress_entry_paths',[]):
    with (ROOT/n).open('a') as f:f.write('\n'+c['module']+'已验收；当前决定与下一步统一见 [RESEARCH_STATUS](RESEARCH_STATUS.md)，详细报告 `'+c['report_document']+'`。\n')
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## '+c['module']+'\n\n'+c['decision']['summary']+' '+c['decision']['next']+'\n')
event=dict.fromkeys(FIELDS);event.update(event_id=c['module']+':ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=protocol['experiment_id'],git_commit=c['parent_commit'],model_family='NORMAL_SPOT_FIXED_RECIPE',fits=0,
 success_failure='ACCOUNT_ACCEPTED_DEVELOPMENT_'+('ADOPT' if c['decision']['adopted'] else 'NOT_ADOPT'),artifact_path=c['acceptance'],artifact_sha256=sha(ROOT/c['acceptance']),reason_for_next_experiment=c['decision']['next'],result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
save(archive/'publication_manifest.json',dict(task_id=os.environ['COIN_TASK_ID'],tasks=tasks,acceptance=dict(path=c['acceptance'],sha256=sha(ROOT/c['acceptance'])),
 config_sha256=sha(a.config),publisher_source_sha256=sha(__file__),elapsed_seconds=time.monotonic()-began,created_utc=datetime.now(UTC).isoformat()))
ledger=v['disk_before'];tmp=STATE/'task-progress'/('last-disk-'+c['module']+'.tmp')
tmp.write_text(json.dumps(dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source=c['module']+' actual pre-replay full scan, not current post-artifact total')));tmp.replace(STATE/'task-progress/last-disk.json')
wip=read(ROOT/c['prior_sync_proof'])['prior_WIP_preserved'];selected=set(c['selected_paths'])
selected.update(p.relative_to(ROOT).as_posix() for p in archive.iterdir());assert not selected.intersection(wip)
save(ROOT/c['source_binding'],dict(status='ACCEPTED_MODULE_SOURCE_BINDING',parent_commit=c['parent_commit'],selected_module_paths=sorted(selected),
 source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,private_SHA_only=accept['private_SHA_only'],private_body_read=False))
print(json.dumps(dict(status='MODULE_DOCUMENTS_AND_SOURCE_BINDING_SAVED',selected_paths=len(selected),adopted=c['decision']['adopted'])))
