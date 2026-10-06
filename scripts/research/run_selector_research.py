"""Single local resumable DAG; no LLM, exchange orders, keys or paid services."""
import argparse,fcntl,json,os,sys,time,resource,subprocess,threading,multiprocessing
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
sys.path.append('/home/xflops/coin-state/selector-support-v1')
import numpy as np
import polars as pl
import psutil,yaml
from scipy.stats import rankdata
from quant.paths import ROOT,STATE
from quant import resources,disk
from scripts.research import selector_data as data
from scripts.research.selector_jobs import cv_job,account_job,atomic,prediction_path
from scripts.investment.reuse_cycle_controls import sha
from scripts.task_progress_api import Progress

PROGRESS=ROOT/'state/selector_progress.json'
class Tracker:
    def __init__(self,run,total):
        self.run=run;self.started=time.time();self.progress=Progress();self.stop=threading.Event();self.process=psutil.Process()
        self.total=total;self.counts={};self.cpu_previous={};self.cpu_at=time.monotonic()
        self.value=dict(stage='DATA',elapsed=0,ETA=None,fold=None,model=None,completed_jobs=0,total_jobs=total,best_validation_score_so_far=None,RAM=None,CPU=None,
            status='RUNNING',pid=os.getpid(),run_dir=str(run),ETA_role='ESTIMATE_AFTER_COMPLETED_JOBS_NOT_GUARANTEED',LLM_API_calls=0)
        self.thread=threading.Thread(target=self.publish_loop,daemon=True);self.thread.start()
    def publish_loop(self):
        while not self.stop.is_set():
            try:
                now=time.monotonic();current={p.pid:sum(p.cpu_times()[:2]) for p in [self.process,*self.process.children(recursive=True)] if p.is_running()}
                delta=sum(max(0,v-self.cpu_previous.get(pid,v)) for pid,v in current.items());cpu=delta/max(1e-6,now-self.cpu_at)*100
                self.cpu_previous=current;self.cpu_at=now
                self.value.update(elapsed=time.time()-self.started,RAM=resources.status()['ram_current_bytes'],CPU=cpu,updated_at=time.time())
                payload=dict(self.value);atomic(PROGRESS,payload);atomic(self.run/'progress.json',payload)
            except (psutil.Error,OSError):pass
            self.stop.wait(5)
    def update(self,stage,completed,total,**details):
        self.counts[stage]=completed
        self.value.update(stage=stage,completed_jobs=sum(self.counts.values()),total_jobs=self.total,stage_completed=completed,stage_total=total,ETA_scope='CURRENT_STAGE_ONLY',**details)
        self.progress.update(stage,completed,total,'jobs',**details)
        print(f'[{stage} {completed}/{total}] '+str(details),flush=True)
    def close(self,status):
        self.value['status']=status;self.stop.set();self.thread.join();atomic(PROGRESS,self.value);atomic(self.run/'progress.json',self.value)
        self.progress.stop.set();self.progress.thread.join(timeout=3)

def resume_result(path,binding):
    p=Path(path)
    if not p.exists():return None
    r=json.loads(p.read_bytes());assert r['_binding']==binding,'Resume refuses changed configuration/source/data'
    if 'prediction' in r:
        assert sha(r['prediction'])==r['prediction_sha256'] and sha(r['model_path'])==r['model_sha256']
    if 'artifacts' in r:
        for v in r['artifacts'].values():assert sha(v['path'])==v['sha256']
    return r

def stage_jobs(pool,tracker,stage,tasks,binding,config):
    total=len(tasks);results=[];pending={};tasks=iter(tasks);count=0;start=time.monotonic()
    def submit_next():
        nonlocal count
        try:item=next(tasks)
        except StopIteration:return False
        cached=resume_result(item['checkpoint'],binding)
        if cached is not None:
            results.append(cached);count+=1;tracker.update(stage,count,total,fold=item.get('fold'),model=item.get('model'));return True
        future=pool.submit(item['function'],*item['args']);pending[future]=item;return True
    while len(pending)<config['workers']:
        if not submit_next():break
    exhausted=False
    while pending or not exhausted:
        assert tracker.value['elapsed']<config['budget']['wall_seconds'],'Finite registered DAG budget exhausted; resume retained'
        ready,_=wait(pending,timeout=5,return_when=FIRST_COMPLETED) if pending else (set(),set())
        for future in ready:
            item=pending.pop(future);r=future.result();r['_binding']=binding;atomic(item['checkpoint'],r);results.append(r);count+=1
            owned_bytes=sum(p.stat().st_size for p in Path(config['run_dir']).rglob('*') if p.is_file())
            assert owned_bytes<config['budget']['disk_reserved_bytes'],'Registered owned artifact budget exhausted; checkpoints retained'
            tracker.update(stage,count,total,fold=item.get('fold'),model=item.get('model'),ETA=(time.monotonic()-start)/count*(total-count))
        while len(pending)<config['workers'] and not exhausted:
            if not submit_next():exhausted=True
    return results

def save_weights(run,name,unit,decisions,weights):
    p=run/'weights'/(name+'_'+unit+'.npz');p.parent.mkdir(exist_ok=True);np.savez_compressed(p,decisions=decisions,weights=weights);return str(p)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',default='configs/selector_v1.yaml');ap.add_argument('--status',action='store_true');ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--selfcheck',action='store_true');a=ap.parse_args()
    if a.status:
        print(PROGRESS.read_text() if PROGRESS.exists() else '{"status":"NOT_STARTED"}');return
    assert os.environ.get('COIN_TASK_ID'),'Launch through existing WSL progress/bounded wrapper'
    config=yaml.safe_load((ROOT/a.config).read_text());run=Path(config['run_dir']);assert run.parent==STATE and config['workers']==2
    git=config['git_executable'];head=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # No fit, feature preparation or economic run until protocol AND code are
    # present byte-for-byte in the same Git commit. Unrelated WIP is preserved.
    for name in [a.config,*config['source_hashes']]:
        blob=subprocess.check_output([git,'show',head+':'+name],cwd=ROOT);assert blob==(ROOT/name).read_bytes(),'Commit required before training: '+name
    for name,h in config['source_hashes'].items():assert sha(ROOT/name)==h
    support=config['support_runtime'];assert sha(ROOT/support['path'])==support['sha256']
    for name,digest in json.loads((ROOT/support['path']).read_bytes())['installed_file_sha256'].items():
        assert sha(Path('/home/xflops/coin-state/selector-support-v1')/name)==digest
    from scripts.investment.chandelier_short_levels import PACKAGE
    frozen=config['indicator_runtime'];assert sha(ROOT/frozen['path'])==frozen['sha256']
    for name,digest in json.loads((ROOT/frozen['path']).read_bytes())['supplementary_runtime']['installed_file_sha256'].items():assert sha(PACKAGE/name)==digest
    assert sha(ROOT/'state/dataset_lock.json')==config['data']['locked_sha256']
    assert config['data']['training_scope']==['2022-01-01','2024-01-01'] and config['horizons']==[30,60,90]
    audit=ROOT/config['data']['split_audit']['path'];assert sha(audit)==config['data']['split_audit']['sha256']
    run.mkdir(exist_ok=True);lock=(run/'runner.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    binding=dict(config_sha256=sha(ROOT/a.config),source_hashes=config['source_hashes'],data=config['data'],git_preregistration_commit=head)
    binding_path=run/'binding.json'
    if binding_path.exists():
        old=json.loads(binding_path.read_bytes());assert {k:v for k,v in old.items() if k!='git_preregistration_commit'}=={k:v for k,v in binding.items() if k!='git_preregistration_commit'}
        binding=old
    else:atomic(binding_path,binding)
    cv_count=len(config['models'])*len(config['horizons'])*len(config['units'])*len(config['folds'])
    shuffle_count=2*config['placebo']['shuffle_each']*len(config['units'])*len(config['folds'])
    account_count=(len(config['models'])*len(config['horizons'])+2*config['placebo']['shuffle_each']+config['placebo']['random']+6+len(config['horizons']))*len(config['units'])
    tracker=Tracker(run,8+cv_count+shuffle_count+account_count+1);status='FAILED'
    try:
        tracker.update('DATA',0,1);scan=disk.check(config['budget']['disk_reserved_bytes']);atomic(run/'disk_before.json',dict(scan,measured_at=time.time()))
        lib=data.library(config);whole=data.window(config);tracker.update('DATA',1,1)
        tracker.update('FEATURES',0,1);frame=data.features(whole['daily'],config['features']);frame.write_parquet(run/'features.parquet');tracker.update('FEATURES',1,1)
        tracker.update('LABELS',0,6)
        for i,unit in enumerate(config['units']):
            for j,h in enumerate(config['horizons']):
                times,relative,utility,ends=data.labels(lib,unit,h);assert np.array_equal(times,frame['decision_us'].to_numpy())
                np.savez_compressed(run/('labels_'+unit+'_'+str(h)+'.npz'),relative=relative,utility=utility,label_ends=ends)
                tracker.update('LABELS',i*3+j+1,6)
        import importlib.metadata
        for package,version in config['runtime_versions'].items():assert importlib.metadata.version(package)==version,'Frozen installed library version '+package
        # MLP eligibility is checked using actual purged train rows and label
        # equivalent blocks, not inflated overlapping daily sample counts.
        max_train=max(len(data.fold_indices(times,times+h*data.DAY,h,data.stamp(start),data.stamp(end),config['min_train_rows'])[0]) for h in config['horizons'] for start,end in config['folds'])
        atomic(run/'MLP_SKIP.json',dict(status='SKIPPED_INSUFFICIENT_SAMPLES',max_actual_train_rows=max_train,min_required=config['mlp_min_train_rows'],overlap_not_independent=True))
        assert max_train<config['mlp_min_train_rows'],'MLP would require a separately budgeted future protocol'
        if a.selfcheck:
            fixture=dict(config,validation_end='2022-10-03');clock=np.arange(data.stamp(config['validation_start']),data.stamp(fixture['validation_end']),data.DAY)
            wp=save_weights(run,'QA_STATIC_TWO_DAYS','RAW_AS_FRACTION',clock,np.tile([.5,.25,.25],(len(clock),1)))
            checked=account_job(fixture,str(run),'QA_STATIC_TWO_DAYS','RAW_AS_FRACTION',wp)
            assert checked['summary']['terminal_cash_realized'] and checked['summary']['completed_minutes']==2880
            atomic(run/'selfcheck.json',dict(status='PASS_NATIVE_DATA_FEATURE_LABEL_FOLDS_AND_SHARED_ACCOUNT_WIRING_NO_FITS',source_binding=binding,
                wallet_error=checked['independent']['maximum_wallet_error_USDT'],NAV_error=checked['independent']['maximum_NAV_error_USDT'],model_fits=0,
                scope='Two-day static real-wallet wiring only; not model economics, strategy selection, or validation evidence'))
            status='SELFCHECK_PASS_NO_FITS';return
        if a.prepare_only:status='PREPARED_NO_FITS_NO_BACKTEST';return
        ctx=multiprocessing.get_context('spawn')
        with ProcessPoolExecutor(max_workers=config['workers'],mp_context=ctx,max_tasks_per_child=16) as pool:
            tasks=[]
            for model in config['models']:
                for h in config['horizons']:
                    for unit in config['units']:
                        for fold in range(len(config['folds'])):
                            key=f'{model}_H{h}_{unit}_F{fold}';tasks.append(dict(function=cv_job,args=(config,str(run),model,h,unit,fold),checkpoint=run/'cv'/key/'result.json',model=model,fold=fold+1))
            cv=stage_jobs(pool,tracker,'CV',tasks,binding,config)
            paths={};scores={};decisions=None
            for model in config['models']:
                for h in config['horizons']:
                    key=f'{model}_H{h}';scores[key]=[]
                    for unit in config['units']:
                        subset=[r for r in cv if (r['model'],r['horizon'],r['unit'])==(model,h,unit)];decisions,w,score=prediction_path(config,run,model,h,unit,subset)
                        paths[key,unit]=save_weights(run,key,unit,decisions,w);scores[key].append(score)
                        tracker.value['best_validation_score_so_far']=max(min(v) for v in scores.values() if len(v)==2) if any(len(v)==2 for v in scores.values()) else None
            champion=max(sorted(scores),key=lambda name:min(scores[name]));model,h=champion.rsplit('_H',1);h=int(h)
            atomic(run/'selection.json',dict(champion=champion,criterion='MIN_ACROSS_TWO_FUNDING_CONDITIONS_COMMON_MATURE_DATE_WEIGHTED_UTILITY_RANK',scores=scores,role='SEEN_INTERNAL_VALIDATION_NOT_UNSEEN'))
            placebo_tasks=[]
            for kind in ('LABEL_SHUFFLE','FEATURE_SHUFFLE'):
                for replicate in range(config['placebo']['shuffle_each']):
                    seed=config['seed']+replicate+(1000 if kind=='FEATURE_SHUFFLE' else 0)
                    for unit in config['units']:
                        for fold in range(len(config['folds'])):
                            key=f'{model}_H{h}_{unit}_F{fold}_{kind}_{seed}'
                            placebo_tasks.append(dict(function=cv_job,args=(config,str(run),model,h,unit,fold,kind,seed),checkpoint=run/'cv'/key/'result.json',model=model,fold=fold+1))
            pcv=stage_jobs(pool,tracker,'PLACEBO_FIT',placebo_tasks,binding,config)
            for kind in ('LABEL_SHUFFLE','FEATURE_SHUFFLE'):
                for replicate in range(config['placebo']['shuffle_each']):
                    seed=config['seed']+replicate+(1000 if kind=='FEATURE_SHUFFLE' else 0);name=kind+'_'+str(replicate)
                    for unit in config['units']:
                        subset=[r for r in pcv if r['unit']==unit and r['placebo']==kind and r['seed']==seed]
                        _,w,_=prediction_path(config,run,model,h,unit,subset);paths[name,unit]=save_weights(run,name,unit,decisions,w)
            from scripts.investment.regime_ranking_screen import bounded_path
            frozen=config['data']['d106_reference'];assert sha(ROOT/frozen['path'])==frozen['sha256'];original=json.loads((ROOT/frozen['path']).read_bytes())
            state_times=np.array([v['decision_us'] for v in original['feature_states']]);indices=[original['expert_order'].index(e) for e in data.EXPERTS]
            full_weights=np.array(original['weight_path']);assert np.allclose(full_weights[:,indices].sum(axis=1),1)
            d106=np.array([full_weights[int(np.searchsorted(state_times,t,side='right')-1),indices] for t in decisions])
            for unit in config['units']:
                for name,w in [('SMA200_SIGNED',np.tile([1.,0.,0.],(len(decisions),1))),('HOLD',np.tile([0.,1.,0.],(len(decisions),1))),('CASH',np.tile([0.,0.,1.],(len(decisions),1))),
                    ('STATIC',np.tile([.5,.25,.25],(len(decisions),1))),('D106_FIXED_MAP',d106)]:paths[name,unit]=save_weights(run,name,unit,decisions,w)
                # Expanding past winner uses only H-day labels with label end
                # <= decision-H. It is another causal comparator, not oracle.
                label=np.load(run/('labels_'+unit+'_'+str(h)+'.npz'));w=[]
                for t in decisions:
                    mature=(times+h*data.DAY<=t-h*data.DAY);valid=label['utility'][mature];assert np.isfinite(valid).all()
                    row=np.zeros(3);row[int(np.argmax(valid.mean(axis=0)))]=1;w.append(row)
                paths['EXPANDING_PAST_WINNER',unit]=save_weights(run,'EXPANDING_PAST_WINNER',unit,decisions,bounded_path(w,np.array([0.,0.,1.]),config['max_daily_L1_change']))
                selected=np.load(paths[champion,unit])['weights'];steps=np.linalg.norm(np.diff(np.vstack([[0.,0.,1.],selected]),axis=0),ord=1,axis=1)
                for replicate in range(config['placebo']['random']):
                    rng=np.random.default_rng(config['seed']+2000+replicate);previous=np.array([0.,0.,1.]);w=[]
                    for distance in steps:
                        if distance>1e-12:
                            candidates=np.flatnonzero(2*(1-previous)>=distance-1e-12);j=int(rng.choice(candidates));target=np.eye(3)[j]
                            previous+=distance/(2*(1-previous[j]))*(target-previous)
                        w.append(previous.copy())
                    name='RANDOM_'+str(replicate);paths[name,unit]=save_weights(run,name,unit,decisions,np.array(w))
                from scripts.investment.oracle_expert_opportunity import optimal_path
                source_nav={e:np.r_[10000.,lib[e,unit]['daily_nav.parquet'].sort('day_end_us')['nav'].to_numpy()] for e in data.EXPERTS}
                for horizon in config['horizons']:
                    bounds=[(i,min(len(decisions),i+horizon)) for i in range(0,len(decisions),horizon)];offset=int((decisions[0]-times[0])//data.DAY)
                    growth=np.array([[source_nav[e][offset+b]/source_nav[e][offset+a] for e in data.EXPERTS] for a,b in bounds]);start_targets=[];end_targets=[]
                    for a,b in bounds:
                        start_targets.append([[lib[e,unit]['targets.parquet'].filter(pl.col('available_us')==int(decisions[a]))['target_weight'].item()] for e in data.EXPERTS])
                        end_targets.append([[lib[e,unit]['targets.parquet'].filter(pl.col('available_us')==int(decisions[b-1]))['target_weight'].item()] for e in data.EXPERTS])
                    path,_=optimal_path(growth,start_targets,end_targets,.00135);w=np.zeros((len(decisions),3))
                    for (a,b),j in zip(bounds,path):w[a:b,j]=1
                    name='ORACLE_H'+str(horizon);paths[name,unit]=save_weights(run,name,unit,decisions,w)
            account_tasks=[]
            for (name,unit),path in paths.items():
                cid=name+'_'+unit;account_tasks.append(dict(function=account_job,args=(config,str(run),cid,unit,path),checkpoint=run/'accounts'/cid/'result.json',model=name))
            accounts=stage_jobs(pool,tracker,'BACKTEST',account_tasks,binding,config)
        tracker.update('REPORT',0,1)
        from scripts.research.selector_report import publish
        publish(config,run,binding,accounts,cv+pcv,champion,scores)
        tracker.update('REPORT',1,1);status='COMPLETE'
    except BaseException as e:
        atomic(run/'failure.json',dict(error_type=type(e).__name__,error=str(e),when=time.time(),resumable=True));raise
    finally:tracker.close(status)

if __name__=='__main__':main()
