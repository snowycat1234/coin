import json,os,hashlib,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.research.selector_jobs import atomic
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
original=json.loads((ROOT/'configs/selector_v1.yaml').read_bytes());fixed=json.loads((ROOT/'configs/selector_v1.yaml').read_bytes())
fixed['run_dir']=str(STATE/'selector-v1-20261006-servicefix')
fixed['source_hashes']['scripts/research/selector.sh']=sha(ROOT/'scripts/research/selector.sh')
assert {k:v for k,v in original.items() if k not in ('run_dir','source_hashes')}=={k:v for k,v in fixed.items() if k not in ('run_dir','source_hashes')}
assert not (STATE/'selector-v1-20261006/cv').exists()
path=ROOT/'configs/selector_v1_runtime_fix.yaml'
assert not path.exists();atomic(path,fixed)
p=ROOT/'docs/SELECTOR_RUNNER.md';t=p.read_text().replace('selector_v1.yaml','selector_v1_runtime_fix.yaml');t+='\n后台启动修复：原systemd用户manager没有WSL_DISTRO_NAME，既有bounded守卫在训练前以1退出；实际日志保留在STATE/selector-v1-startup.log。启动器现显式传入经外层核对的hpc_linux标识并将日志持久写入D-hosted STATE。原selector_v1.yaml保留；runtime_fix仅修改launcher源码SHA与新运行目录，数据/feature/H/models/cost/budget/gates/placebo完全相同。旧准备目录/两日QA保留，正式新目录在commit后开始。\n';p.write_text(t)
p=ROOT/'docs/RESEARCH_STATUS.md';t=p.read_text().replace('自动DAG与训练前回归已完成，正式fit **NOT_STARTED**；先提交split/features/horizon/model/budget/gates/placebo，再做两日静态共享钱包接线检查。通过后由独立Python服务完成训练、placebo、158共享钱包对照与报告，不需要LLM/API逐折参与。','训练前协议已commit/push `0dc2f2f` 并核远端；两日真实共享钱包接线QA通过（2880分钟、paid flat、独立资金/NAV核验，0fit）。首个后台启动因systemd缺WSL标识被bounded守卫阻止，训练仍 **NOT_STARTED**；已修启动标识与持久日志，新runtime_fix配置只改launcherSHA与运行目录，其余科学协议完全相同，先commit修复再启动自主DAG。最终模型净收益 **NOT_YET_READ**，不需要LLM/API逐折参与。').replace('../configs/selector_v1.yaml','../configs/selector_v1_runtime_fix.yaml');p.write_text(t)
log=STATE/'selector-v1-startup.log'
receipt=dict(status='PASS_MINIMAL_SERVICE_STARTUP_FIX_NO_MODEL_FITS',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(Path(__file__)),failure='bounded rejected missing WSL_DISTRO_NAME before Python; captured native diagnostic exit1',failed_native_log_path=str(log),failed_native_log_sha256=sha(log),old_run_preserved=True,model_fits=0,scientific_parameters_identical=True,changed_fields=['run_dir','source_hashes.scripts/research/selector.sh'],original_config_sha256=sha(ROOT/'configs/selector_v1.yaml'),runtime_fixed_config_sha256=sha(path),QA_ref='reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json')
atomic(ROOT/'reports/SELECTOR_ML_LAUNCH_FIX_20261006_V1.json',receipt)
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\nD108启动纠正：首个systemd后台进程在进入Python前被bounded WSL身份守卫拒绝（实测32ms、exit1、日志Use D-hosted hpc_linux）；最初短暂active不算存活。修复仅为外层核真实hpc后传入WSL_DISTRO_NAME与持久日志，0fit；原冻结配置不覆盖，runtime_fix只变启动器SHA/新目录，所有训练/经济/验收协议逐字段一致，旧2日共享钱包QA有效保留。需先commit再正式启动。\n')
print(json.dumps(dict(status=receipt['status'],model_fits=0)))