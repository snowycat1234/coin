import json,os,subprocess,hashlib
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE
from scripts.research_v8.registry import append_event,FIELDS
from scripts.research.selector_jobs import atomic
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
run=STATE/'selector-v1-20261006';qa=json.loads((run/'selfcheck.json').read_bytes());account=json.loads((run/'accounts/QA_STATIC_TWO_DAYS/result.json').read_bytes())
assert qa['status']=='PASS_NATIVE_DATA_FEATURE_LABEL_FOLDS_AND_SHARED_ACCOUNT_WIRING_NO_FITS' and qa['model_fits']==0
assert qa['source_binding']['config_sha256']==sha(ROOT/'configs/selector_v1.yaml')
assert account['summary']['completed_minutes']==2880 and account['summary']['terminal_cash_realized']
assert account['independent']['maximum_NAV_error_USDT']<1e-7 and account['independent']['maximum_wallet_error_USDT']<1e-7
qa_task='01ff09c984624ed0b71efa261c15d584';task=json.loads((STATE/'task-progress'/('task-'+qa_task+'.json')).read_bytes());assert task['exit_code']==0 and task['status']=='completed'
qa.update(task_id=qa_task,source_sha256=sha(ROOT/'scripts/research/run_selector_research.py'),native_account_artifacts=account['artifacts'],observed_minutes=2880,scope='TWO_DAY_STATIC_WIRING_ONLY_NOT_SELECTOR_PERFORMANCE')
atomic(ROOT/'reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json',qa)
unit=subprocess.check_output(['systemctl','--user','show','coin-selector-v1.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','Slice'],text=True)
assert 'ActiveState=active' in unit and 'Slice=coin-research.slice' in unit
launch=dict(status='NATIVE_SELECTOR_DAG_STARTED_NO_MODEL_RESULT_INTERPRETED',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(Path(__file__)),created_utc=datetime.now(UTC).isoformat(),git_preregistration_commit=qa['source_binding']['git_preregistration_commit'],config_sha256=qa['source_binding']['config_sha256'],native_unit=unit,QA_task=qa_task,QA_artifact='reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json',QA_sha256=sha(ROOT/'reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json'),LLM_API_calls_inside_DAG=0,model_economic_results='NOT_YET_READ',qualification='NONE_CASH',historical_scope='SEEN_DEVELOPMENT_INTERNAL_CHRONOLOGICAL_VALIDATION',original_collectors_untouched=True)
atomic(ROOT/'reports/SELECTOR_ML_LAUNCH_20261006_V1.json',launch)
p=ROOT/'docs/RESEARCH_STATUS.md';text=p.read_text();text=text.replace('自动DAG与训练前回归已完成，正式fit **NOT_STARTED**；先提交split/features/horizon/model/budget/gates/placebo，再做两日静态共享钱包接线检查。通过后由独立Python服务完成训练、placebo、158共享钱包对照与报告，不需要LLM/API逐折参与。','训练前协议已commit/push `0dc2f2f` 并核远端；两日静态共享钱包接线检查通过（2880分钟、真实成交与paid flat、独立资金/NAV核验，无模型fit）。`coin-selector-v1.service` 已实际后台启动，按冻结协议自主完成训练、placebo、158共享钱包对照和报告；最终模型经济指标 **NOT_YET_READ**。进度见8765或state/selector_progress.json；不需要LLM/API逐折参与，SSH断开不影响运行。')
text=text.replace('[实际榜单]', '\n[实际榜单]',1);p.write_text(text)
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\nD108运行交付：训练前commit '+head+' 已push并核远端。真实2880分钟静态共享钱包接线检查通过，0模型fit，完整资本10k/真实成交/独立钱包NAV核验/paid flat；这是接线QA，不是selector收益。后台coin-selector-v1已实际启动，固定DAG自主执行，0LLM/API。用户提问的0/1jobs现显示当前步骤进行中，中文阶段说明；未知总量仍不造百分比，UI只改显示，不改协议/模型/账户。完整结果完成后再读取一次，当前净收益未读，投资NONE/CASH。\n')
event=dict.fromkeys(FIELDS);event.update(experiment_id='D108_SELECTOR_RUNNER_LAUNCH',event_id='D108_SELECTOR_RUNNER_LAUNCH:QA',event_type='OPERATIONAL_RESEARCH_DECISION',git_commit=head,model_family='FROZEN_EXPERT_UTILITY_SELECTOR',models_fit=0,success_failure='PASS_TWO_DAY_NATIVE_WIRING_NO_ALPHA_CLAIM',artifact_path='reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json',artifact_sha256=sha(ROOT/'reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json'),reason_for_next_experiment='Detached local finite preregistered DAG; interpret only final results',result_influenced_later_choice=False);append_event(ROOT/'reports/experiment_registry.jsonl',event)
paths=['tools/task_progress/index.html','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl','reports/SELECTOR_ML_NATIVE_SELFCHECK_20261006_V1.json','reports/SELECTOR_ML_LAUNCH_20261006_V1.json','reports/GITHUB_SELECTOR_ML_PREREGISTRATION_SYNC_VERIFIED_20261006_V1.json','docs/archive/SELECTOR_OPS_CLOSE_SOURCE_20261006_V1.py']
prior=json.loads((ROOT/'reports/GITHUB_SELECTOR_ML_PREREGISTRATION_SOURCE_BINDING_20261006_V1.json').read_bytes())['prior_WIP_preserved']
binding='reports/GITHUB_SELECTOR_ML_LAUNCH_SOURCE_BINDING_20261006_V1.json'
atomic(ROOT/binding,dict(status='ACCEPTED_MODULE_SOURCE_BINDING',parent_commit=head,selected_module_paths=paths+[binding],source_hashes={p:sha(ROOT/p) for p in paths},prior_WIP_preserved=prior,scientific_sources_unchanged=True,locked_body_read=False))
print(json.dumps(dict(status=launch['status'],QA_minutes=2880,native_unit=unit)))