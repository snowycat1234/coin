import hashlib,json,subprocess,sys
from datetime import UTC,datetime
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state');sys.path.insert(0,str(root))
from scripts.research_v8.registry import read_verified
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
path=root/'reports/fast_research/V8_SHARED_SOURCE_VIEW_153D_20261002_V1.json'
assert sha(path)=='dd931ce79f7f78e7e2c070f553077ffeca4ed73d7c0c0a1c744e4288d68f05cf'
view=json.loads(path.read_text());prior=json.loads((root/'reports/fast_research/V7_SHARED_SOURCE_VIEW_123D_20261002_V1.json').read_text())
assert view['status']=='PASS_SHARED_V8_SOURCE_VIEW_153D'
assert (view['actual_common_days'],view['actual_unique_stream_days'],view['actual_rows'])==(153,612,10575360)
assert view['binding']['selected'][:492]==prior['binding']['selected']
selected=view['binding']['selected']
assert len(selected)==612 and len({(s['market'],s['symbol'],s['day']) for s in selected})==612
assert min(s['day'] for s in selected)=='2025-07-01' and max(s['day'] for s in selected)=='2025-11-30'
assert not view['research_labels_or_model_outcomes_read'] and not view['locked_consumed'] and view['model_fits']==0
for p,h in view['source_hashes'].items():assert sha(root/p)==h
producer=json.loads(Path(view['actual_original_source_producer']['path']).read_text())
assert producer['status']=='completed' and producer['exit_code']==0 and producer['pid']==3134 and producer['start_ticks']==519151
tasks=[json.loads(p.read_text()) for p in (state/'task-progress').glob('task-*.json')]
tasks=[t for t in tasks if t['title']=='V8 四流153日来源绑定 · 不读标签或模型']
assert len(tasks)==1 and tasks[0]['status']=='completed' and tasks[0]['exit_code']==0
events=read_verified((root/'reports/experiment_registry.jsonl').read_bytes())
completion=next(e for e in events if e['event_id']=='v8-jul-nov-153d-source-view-20261002-v1:complete')
assert completion['output_sha256']==sha(path) and completion['success_failure']==view['status']
proofs={str(path.relative_to(root)):sha(path)}
for market in ('SPOT','PERP'):
 for symbol in ('BTCUSDT','ETHUSDT'):
  stem=f'reports/fast_research/V8_MONTHLY_{market}_{symbol}_202511'
  ap=root/(stem+'_SOURCE_ACCEPTANCE_V1.json');a=json.loads(ap.read_text())
  assert a['status']=='PASS_SOURCE_ONLY_INDEPENDENT_MONTHLY_QA' and a['checked_days']==30 and a['checked_rows']==518400
  for suffix,k in [('_V1.json','receipt_sha256'),('_INDEPENDENT_QA_V1.json','qa_sha256')]:
   rp=root/(stem+suffix);assert sha(rp)==a[k];proofs[str(rp.relative_to(root))]=sha(rp)
  for rp in root.glob(stem+'_*.json'):proofs[str(rp.relative_to(root))]=sha(rp)
for name in ('V8_NOVEMBER_OPERATIONAL_SOURCE_ARCHIVE_20261002_V1.json','V8_L1_RECOVERY_SOURCE_ARCHIVE_20261002_V1.json'):
 ap=root/'reports/fast_research'/name;a=json.loads(ap.read_text());proofs[str(ap.relative_to(root))]=sha(ap)
 for item in a['source_archives']:
  rel=item['archive_path'].replace('\\','/');assert sha(root/rel)==item['sha256'];proofs[rel]=item['sha256']
 for item in a.get('existing_receipts',[]):
  rel=item['path'].replace('\\','/');assert sha(root/rel)==item['sha256'];proofs[rel]=item['sha256']
for name in ('V8_NOVEMBER_SOURCE_PREREGISTRATION_20261002_V1.json','V8_NOVEMBER_SOURCE_OPERATIONAL_START_20261002_V1.json',
 'V8_L1_AND_MINUTE_LIVENESS_20261002_V1.json'):
 p=root/'reports/fast_research'/name;proofs[str(p.relative_to(root))]=sha(p)
extra=['scripts/research_v8/fetch_monthly_from_recovery.py','docs/archive/V8_L1_AND_MINUTE_LIVENESS_SOURCE_20261002_V1.py']
sources=view['source_hashes']|{p:sha(root/p) for p in extra}
archive=root/'docs/archive/V8_SOURCE_153D_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
sources[str(archive.relative_to(root))]=sha(archive)
receipt=dict(status='ROOT_PASS_153D_SOURCE_AND_TRUTHFUL_RECOVERY_EVIDENCE_ONLY',created_utc=datetime.now(UTC).isoformat(),
 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 data_hash=sha(path),protocol_hash=view['registration_start']['protocol_hash'],
 environment_hash=sha(root/'environments/v8/uv.lock'),seed=None,
 exact_command='bash scripts/bounded.sh /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_source_153d_root_acceptance_20261002_v1.py',
 source_hashes=sources,verified_prior_files=proofs,actual_verifier_unified_session_id=44714,actual_verifier_exit_code=0,
 actual_verifier_task=tasks[0],actual_producer_task=producer,old_492_prefix_unchanged=True,
 common_days=153,stream_days=612,source_rows=10575360,november_QA_stream_days=120,
 actual_disk=view['disk'],peak_RSS_bytes=view['peak_rss_bytes'],classification='SCREENING_SOURCE_SUPPORT_ONLY',
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',P1_gate='NOT_READY',market_models_fit=0,
 locked_consumed=False,orders_sent=0,limitations=['Source acceptance does not establish predictive, economic or execution alpha.',
 'L1 clock uncertainty and gaps remain in their original receipts; no health-duration splicing or real-time eligibility is granted.',
 'No market data bytes are committed to Git; existing actual producer/source receipts are verified without redundant row conversion.'])
out=root/'reports/fast_research/V8_SOURCE_153D_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({k:receipt[k] for k in ('status','common_days','stream_days','source_rows','P1_gate')}))
