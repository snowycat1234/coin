"""Read actual module/checkpoint/minute progress; never infer invented percentages."""
import argparse,json,os,time
from pathlib import Path

FILES=(('冻结v2回放','replay-progress.json',864),('HALF旧模型对照','half-controls/HALF_CONTROL_RESULTS_progress.json',348),
       ('Policy开发训练','POLICY_FIT_PROGRESS.json',60),('固定最终训练','POLICY_FINAL_FITS.json',12),
       ('新模型开发账户','policy-development/POLICY_DEVELOPMENT_RESULTS_progress.json',576),('五方案封存账户','locked-bridge-progress.json',400))

def read(path):
    try:return json.loads(Path(path).read_text())
    except (FileNotFoundError,json.JSONDecodeError):return None

def snapshot(state):
    state=Path(state);steps=[]
    for label,file,total in FILES:
        value=read(state/file)
        steps.append(dict(module=label,started=value is not None,completed=value.get('completed',0) if value else 0,
                          total=total,failed=value.get('failed',0) if value else 0,status=value.get('status',value.get('stage','RUNNING')) if value else 'NOT_STARTED'))
    training=read(state/'policy-train-progress.json');final_training=read(state/'policy-final-progress.json')
    pipeline=read(state/'pipeline-progress.json')
    locked=read(state/'locked-bridge-progress.json')
    if locked:
        tag='raw_fraction' if locked['funding_scale']==1 else 'raw_percent'
        inner=read(state/'locked-bridge-native'/locked['active_scenario']/tag/'LOCKED_BRIDGE_RESULTS_progress.json')
        if inner:steps[-1].update(completed=locked['completed']+inner['completed'],failed=inner['failed'],scenario=locked['active_scenario'],funding_scale=locked['funding_scale'])
    complete=read(state/'TRANSFORMER_V3_FINAL_RESULTS.json')
    if complete and complete.get('status')=='FINAL_IMPUTED_LOCKED_SENSITIVITY_COMPLETE':steps[-1].update(completed=400,status='COMPLETE')
    roots=[state/'native',state/'half-controls/native',state/'policy-development/native']
    if locked:roots.append(state/'locked-bridge-native'/locked['active_scenario']/tag/'native')
    minute=[]
    for root in roots:
        for p in root.glob('**/progress.json'):
            v=read(p)
            if v and isinstance(v.get('current'),int) and isinstance(v.get('total'),int) and v['current']<v['total']:
                minute.append(dict(path=str(p),**v))
    minute=sorted(minute,key=lambda v:v.get('updated_at',0),reverse=True)[:10]
    return dict(observed_at=time.time(),steps=steps,pipeline=pipeline,training=training,final_training=final_training,
                recent_incomplete_minute_steps=minute,scope='READ_SAVED_ACTUAL_PROGRESS; OLD_STOPPED_PREFIXES_MAY_REMAIN_IN_RECENT_LIST_UNTIL_FULL_MODULE_END')

def display(value):
    stamp=time.strftime('%H:%M:%S');parts=[]
    for r in value['steps']:
        if r['started']:parts.append(f"{r['module']} {r['completed']}/{r['total']}，执行失败 {r['failed']}")
    if value['pipeline']:parts.append('阶段 '+value['pipeline']['stage'])
    for field in ('training','final_training'):
        t=value[field]
        if t:parts.append(f"最近训练：{t['family']} seed{t['seed']} fold{t['fold']}，epoch {t['epoch']}/{t['max_epoch']}，batch {t['batch']}/{t['total_batches']}")
    for r in value['recent_incomplete_minute_steps'][:2]:
        parts.append(f"账户最近记录：{r.get('detail','')} {r['current']}/{r['total']} {r.get('unit','')}")
    print('['+stamp+'] '+' | '.join(parts),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--watch',action='store_true');p.add_argument('--interval',type=float,default=15);p.add_argument('--json',action='store_true');a=p.parse_args()
    if a.interval<=0:raise ValueError('Positive watch interval required')
    while True:
        value=snapshot(a.state)
        if a.json:print(json.dumps(value,ensure_ascii=False),flush=True)
        else:display(value)
        if not a.watch:break
        time.sleep(a.interval)

if __name__=='__main__':main()
