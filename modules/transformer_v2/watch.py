"""Read-only live progress, authoritative service state and real per-case minutes."""
import argparse,json,subprocess,time
from pathlib import Path

def snapshot(state):
    state=Path(state);units={}
    for stage in ('train','final-fit','evaluate','assist','dev-report','pipeline','locked-data','locked-evaluate','final-report'):
        name=f'coin-transformer-v2-{stage}-20261007.service'
        text=subprocess.run(['systemctl','show',name,'-p','ActiveState','-p','MainPID','-p','ExecMainStatus'],capture_output=True,text=True).stdout
        units[stage]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
    progress={}
    for name in ('FIT_PROGRESS.json','train-progress.json','final-fit-progress.json','FINAL_FITS.json','economic-progress.json','pipeline-progress.json','locked-data-progress.json','locked-economic-progress.json'):
        path=state/name
        if path.exists():
            try:
                value=json.loads(path.read_text());progress[name]={k:v for k,v in value.items() if k not in ('results','cases','artifacts','tasks')}
            except (ValueError,OSError):pass
    active=[]
    for root in (state/'native',state/'locked-native/native'):
        if not root.exists():continue
        for path in root.rglob('progress.json'):
            if (path.parent/'RESULT.json').exists():continue
            try:
                value=json.loads(path.read_text());active.append(dict(case=str(path.parent.relative_to(state)),**value))
            except (ValueError,OSError):pass
    return dict(services=units,progress=progress,unique_development_results_on_disk=len(list((state/'native').rglob('RESULT.json'))),
                active_native_cases=active,observed_at=time.time())

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--once',action='store_true');a=p.parse_args()
    while True:
        value=snapshot(a.state);print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)
        if a.once:break
        time.sleep(10)

if __name__=='__main__':main()
