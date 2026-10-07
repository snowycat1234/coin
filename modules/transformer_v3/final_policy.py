"""Twelve final past-only policy refits; fixed median inner epoch, no locked labels."""
import argparse,json,os,platform,subprocess,time
from pathlib import Path
import numpy as np
import torch
from modules.transformer_v2.final_fit import final_indices
from modules.transformer_v2.train import atomic,sha
from .teachers import load_teacher_development,training_teacher_view
from .train_policy import fit_phase,FAMILIES,SEEDS

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);a=p.parse_args()
    if platform.system()!='Linux' or os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower():raise RuntimeError('Independent Linux server only')
    state=Path(a.state);repo=Path(__file__).resolve().parents[2]
    if subprocess.check_output(['git','-C',str(repo),'show','HEAD:modules/transformer_v3/final_policy.py'])!=Path(__file__).read_bytes():raise ValueError('Final-fit source must be committed')
    progress=json.loads((state/'POLICY_FIT_PROGRESS.json').read_text())
    if progress['status']!='COMPLETE' or progress['completed']!=60:raise RuntimeError('All development fits must precede fixed final median epochs')
    binding=json.loads((state/'POLICY_TRAIN_BINDING.json').read_text())
    if any(sha(repo/n)!=v for n,v in binding['sources'].items()):raise ValueError('Protected development training recipe changed')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    torch.set_num_threads(len(os.sched_getaffinity(0)));d=load_teacher_development(a.collector_root,a.work,a.source_run);tasks=[]
    if d['teacher_receipts']!=binding['teacher_sources']:raise ValueError('Teacher source changed after development fitting')
    for scenario,tag in enumerate(('raw_fraction','raw_percent')):
        indices,active,cutoff=final_indices(d,scenario);training_teacher_view(d,indices,cutoff,active)
        for family in FAMILIES:
            for seed in SEEDS:
                epochs=[json.loads((state/'policy-fits'/tag/f'fold{fi}'/family/f'seed{seed}'/'inner/RESULT.json').read_text())['best_epoch'] for fi in range(1,6)]
                tasks.append(dict(scenario=scenario,tag=tag,family=family,seed=seed,epochs=max(1,int(round(float(np.median(epochs))))),development_inner_epochs=epochs,
                    indices=indices.tolist(),active=active.tolist(),cutoff=cutoff.isoformat(),max_label_end=d['label_end'][indices].max().isoformat()))
    plan=dict(status='FIXED_MEDIAN_PAST_ONLY_RULE',tasks=tasks,source_sha256=sha(__file__),training_binding_sha256=sha(state/'POLICY_TRAIN_BINDING.json'),locked_read=False)
    path=state/'POLICY_FINAL_FIT_PLAN.json'
    if path.exists():
        if json.loads(path.read_text())!=plan:raise ValueError('Final refit plan changed')
    else:atomic(path,plan)
    results=[]
    for number,t in enumerate(tasks,1):
        folder=state/'policy-final-fits'/t['tag']/t['family']/f'seed{t["seed"]}'
        own=dict(binding,final_plan_sha256=sha(path),final_source_sha256=sha(__file__))
        context=dict(stage='POLICY_FIXED_FINAL_PAST_ONLY_REFIT',fold='FINAL',status=state/'policy-final-progress.json',outer_cutoff=t['cutoff'])
        for attempt in range(2):
            try:result=fit_phase(d,t['indices'],[],t['scenario'],np.array(t['active']),t['family'],t['seed'],folder,t['epochs'],False,own,context,t['cutoff']);break
            except Exception as exc:
                atomic(folder/f'FAILURE_ATTEMPT_{attempt+1}.json',dict(error=str(exc),time=time.time()))
                if attempt==1:raise
        results.append(dict(task=t,result=result,folder=str(folder)))
        atomic(state/'POLICY_FINAL_FITS.json',dict(status='RUNNING',completed=number,total=12,results=results,locked_read=False))
        print(f'POLICY FINAL {number}/12 {t["family"]} {t["tag"]} seed{t["seed"]}',flush=True)
    atomic(state/'POLICY_FINAL_FITS.json',dict(status='COMPLETE',completed=12,total=12,results=results,locked_read=False))

if __name__=='__main__':main()
