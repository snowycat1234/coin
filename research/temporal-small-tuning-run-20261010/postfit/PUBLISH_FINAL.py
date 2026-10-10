"""Publish only existing verified results; no fitting, inference or rollout."""
import hashlib
import csv
import json
import shutil
from pathlib import Path

state = Path('/workspace/coin-state/work/temporal-two-expert-20261009')
run = state/'small-tuning-run'
public = Path('/workspace/coin-temporal/research/temporal-small-tuning-run-20261010')
result = json.loads((run/'VERIFIED_RESULT.json').read_text())
verification = json.loads((run/'VERIFICATION.json').read_text())
if verification['status'] != 'PASS' or result['actual_fits'] != 6 or result['later_full773_refit'] != 'NOT_RUN' or result['reserve_results_read']:
    raise ValueError('All six verified results and no refit/reserve read required')
final=public/'final'
final.mkdir(exist_ok=False)
for row in result['all_fit_results']:
    source=run/row['task_id'];target=final/row['task_id'];target.mkdir()
    for name in ['INITIAL.json','BEST.json','MATCHED512.json','latest.json']:
        pointer=json.loads((source/name).read_text())
        shutil.copy2(source/name,target/name)
        body=target/pointer['file']
        if not body.exists(): shutil.copy2(source/pointer['file'],body)
        if hashlib.sha256(body.read_bytes()).hexdigest()!=pointer['SHA256']: raise ValueError('Exact source-bound generation body required')
    for p in sorted(source.iterdir()):
        if p.name in {'RUN.json','SCALER.json','SCALER.npz','CONTROL_NAV.npz','TERMINAL.json','CAP_FINALIZATION.json','CAP_ORIGINAL.pt','FAILURE.json'} or p.name.startswith(('VALIDATION_','RESOURCE_SLICE_','CONSOLE_SLICE_')):
            shutil.copy2(p,target/p.name)
global_names=['VERIFIED_RESULT.json','VERIFICATION.json','RESULT.json','CONTROLLER_RECEIPT.json','CONTROLLER_EVENTS.jsonl','BASE512_OLD_COMPARISON.json','PUBLIC_PREFIT_RECEIPT.json','START_PUBLIC_READBACK.json','PROGRESS_READBACK.json','MATCHED512_READBACK.json','INITIAL_NAV_CHECK.json','RUNTIME_EXTENSION_PUBLIC_READBACK.json','RUNTIME_EXTENSION_5400.json','RUNTIME_EXTENSION_DECISION.json']
for name in global_names:
    if (run/name).exists(): shutil.copy2(run/name,public/name)
for path in sorted(run.glob('COMPLETED_PROGRESS_PUBLIC_READBACK*.json')):
    shutil.copy2(path,public/path.name)
if (run/'RUNTIME_5400_ORIGINALS').exists():
    shutil.copytree(run/'RUNTIME_5400_ORIGINALS',public/'runtime-extension'/'originals')
fields=['task_id','fold','candidate','step','utility_excess_vs_VOL','net_PnL_USDT','maximum_drawdown','utility_sum','mean_loss','fees_USDT','spread_USDT','slippage_USDT','funding_USDT','risk_events','model_identity']+[f'mean_requested_{s}' for s in ('CASH','VOL','SMA','DONCHIAN','CS','SHORT')]
with (public/'VALIDATION_CURVES.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
    for row in result['all_fit_results']:
        for v in row['validation']:
            m=v['metrics']
            record=dict(task_id=row['task_id'],fold=row['settings']['fold'],candidate=row['settings']['candidate'],step=v['step'],utility_excess_vs_VOL=v['utility_excess'],net_PnL_USDT=m['net_PnL'],maximum_drawdown=m['maximum_drawdown'],utility_sum=m['utility_sum'],mean_loss=m['mean_loss'],fees_USDT=m['fees'],spread_USDT=m['spread'],slippage_USDT=m['slippage'],funding_USDT=m['funding'],risk_events=m['risk_events'],model_identity=v['model_identity'])
            record.update({f'mean_requested_{s}':w for s,w in zip(('CASH','VOL','SMA','DONCHIAN','CS','SHORT'),m['requests_mean'],strict=True)})
            writer.writerow(record)
postfit=public/'postfit';postfit.mkdir(exist_ok=False)
for p in sorted((state/'tuning-tools').iterdir()):
    if p.suffix in {'.py','.json','.xml'}: shutil.copy2(p,postfit/p.name)
selected=result['selected']; settings=result['selected_settings']
text=['Six fresh fits completed under the reviewed [protocol](PROTOCOL.json).',
      f"Selected recipe: **{selected['candidate']}**, Adam lr **{settings['lr']}**, wallet-equal mix **{settings['wallet_equal_mix']}**.",
      f"Return **{result['later_full773_refit_steps']} updates** for the later fresh773-date refit; that refit has **not run**. Q4 reserved outcomes were **not read**.",
      '',
      '| Fold | Candidate | Actual updates | Stop | Best update | Best utility excess vs VOL | Best net PnL (USDT) | Best MDD |',
      '|---|---|---:|---|---:|---:|---:|---:|']
for row in result['all_fit_results']:
    best=row['best'];m=best['metrics']
    text.append(f"| {row['settings']['fold']} | {row['settings']['candidate']} | {row['completed_updates']} | {row['status']} | {best['step']} | {best['utility_excess']:.8f} | {m['net_PnL']:.4f} | {100*m['maximum_drawdown']:.4f}% |")
text+=['','| Recipe | Mean best utility excess | Worst fold excess | Best updates |','|---|---:|---:|---|']
for c in result['candidates']:
    text.append(f"| {c['candidate']} | {c['mean_utility_excess']:.8f} | {c['worst_utility_excess']:.8f} | {c['best_updates']} |")
text+=['',
 'These are project-seen development daily-surrogate results on Jan–Mar and Apr–Jun2024,63decisions/62active intervals each; each complete wallet pays its terminal flattening. They establish a recipe under the fixed selection rule, not convergence or native validation.',
 '',
 'The13,699-parameter model uses CORE5 BTC/ETH/SOL/XRP/DOGE,64completed daily steps,24causal values plus24validity masks. Shared per-asset GRU32 feeds joint160→32 and18current expert values/masks. CASH/VOL/CS/SHORT weights form a masked simplex; canonical SMA/DONCHIAN outputs remain zero. No observed wallet state. Same sigmoid allocation heads, risk mapper, L1≤.1, gross≤.6, per-asset≤.3, costs/funding and own-path gradient contract.',
 '',
 'Exactly653/744active prefix dates across five natural chronological wallets per fold; seed20261009,dropout.1, train-only787/878-row normalization. Fresh Adam for every fit. OneCPU per fit, at most two fits concurrently,2GB resident each/shared8GB,swap0/GPU0. Every completed update fsynced and slices resume full model/Adam/allRNG.',
 '',
 '[VERIFIED_RESULT.json](VERIFIED_RESULT.json) contains selection and all validation metrics; [VERIFICATION.json](VERIFICATION.json) rechecks source-bound snapshots, all Adam ages, initial identities, chronology, masked requests, NAV/PnL/MDD/utility, ordered stopping rules and exact reviewed tie ranking. Verification runs zero fits, inferences or wallet rollouts. Both baseline512 model/Adam/allRNG states match the earlier frozen512 models bitwise.',
 '',
 'Seven focused adapter tests, two independent post-fit checks and eighteen operational-extension tests pass. Original68 sources and all77 fitting-source identities remain unchanged; old failed warm mixed-weight result remains. Checkpoint generation files and pointers in [final/](final/) retain their original filenames for strict restoration. [PREFIT_RECEIPT.json](PREFIT_RECEIPT.json), [postfit/](postfit/) and [CONTROLLER_RECEIPT.json](CONTROLLER_RECEIPT.json) hold test, verification and resource receipts.',
 '',
 'Frozen execution: `python -m modules.temporal_small_tuning prepare|worker|select`; final verified ranking: `python postfit/VERIFY_SELECT.py --output STATE/small-tuning-run`. The independent selector checks terminal status/weights/source identities and uses mean-score tolerance1e-5, then exact worst-fold max and fixed recipe order. It leaves all fitting sources byte unchanged.',
 '',
 'A separate zero-update cap finalizer is provided for the frozen controller/resource-clock mismatch. It requires the exited-controller receipt and actual cumulative-cap evidence (3600seconds originally,5400only if the authorized extension was applied), archives the original body, preserves model/Adam/RNG, repairs only an already-due check and writes truthful capped metadata. Any use is explicitly recorded in the affected final task directory.',
 '',
 'The separately authorized operational3600→5400second cumulative guard extension was published and byte-verified before any use. Its tested overlay changes only numeric time-guard constants, retains1200second hard/1100second training slices and all update/early-stop/memory/selection rules, and preserves the77 fitting-source files and bindings. If needed, same-fit continuations preserve all earlier resource receipts and capped checkpoint bodies. [Runtime extension](runtime-extension/) contains the prepared permission/code/test identities; actual application or no-need decision is recorded separately.',
 '',
 'Dependencies reuse the pinned [official CPU Torch recipe](../temporal-july-frozen-transfer-20261010/requirements-transfer.txt). No provider downloads or reserved outcome access occurred in these six fits. The later773-date refit and Q4 feature binding/native evaluation remain separate authorized stages.',
 '',
 'Historical [training-start](TRAINING_START.json), [live progress](PROGRESS_CHECKPOINT.json) and [matched512](matched512/) snapshots remain preserved. Those public copies use MODEL_ADAM_RNG.pt; rename to the pointer generation filename for strict restoration. Final copies already use original generation names.',
 '']
(public/'README.md').write_text('\n'.join(text))
status_path=Path('/workspace/coin-temporal/docs/RESEARCH_STATUS.md')
heading,_,earlier_status=status_path.read_text().split('\n\n',2)
summary=(
    f"Six approved fresh temporal tuning fits are complete: {result['total_completed_updates']} total updates on the fixed653/744active-date prefixes. "
    f"The reviewed rule selects {selected['candidate']} (Adam lr{settings['lr']}, wallet-equal mix{settings['wallet_equal_mix']}) and {result['later_full773_refit_steps']} updates for the later fresh773-date refit; that refit is NOT_RUN. "
    f"Selected mean/worst development utility excess vs frozenVOL are {selected['mean_utility_excess']:.8f}/{selected['worst_utility_excess']:.8f}; these project-seen daily-surrogate results do not establish convergence or promotion. "
    "All six best/matched512/terminal model/Adam/RNG identities, chronology, NAV metrics and stopping/selection rules independently verified. "
    "Both baseline512 states match the earlier models bitwise;77fitting sources and original68remain unchanged. "
    "Seven adapter, two post-fit and eighteen operational-extension tests pass. At most two bounded1CPUworkers, resident2GB/shared8GB,swap0/GPU0; every completed update durable and exact-resumed. "
    "The separately authorized3600→5400second operational extension decision and all prior receipts are retained. No Q4reserved outcomes, provider downloads or native wallets; Q4feature binding/native validation and the selected full refit remain separate stages. "
    "[Results, counts and checkpoints](../research/temporal-small-tuning-run-20261010/README.md)."
)
status_path.write_text('\n\n'.join((heading,summary,earlier_status)))
manifest={str(p.relative_to(public)):dict(bytes=p.stat().st_size,SHA256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(public.rglob('*')) if p.is_file() and p.name not in {'PUBLIC_MANIFEST.json','FINAL_PUBLIC_READBACK.json'}}
(public/'PUBLIC_MANIFEST.json').write_text(json.dumps(dict(status='SIX_VERIFIED_FITS_DURABLY_PUBLISHED',files=manifest,selected=selected['candidate'],later_full773_refit_steps=result['later_full773_refit_steps'],actual_updates=result['total_completed_updates'],reserve_read=False),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(files=len(manifest),bytes=sum(r['bytes'] for r in manifest.values()),selected=selected['candidate'],later_full773_refit_steps=result['later_full773_refit_steps'])))
