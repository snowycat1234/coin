"""Use two freed CPU workers for a fixed distant tail, reused by the main runner.

No primary process is stopped. No models, targets, rankings or financial bindings
change. Leave a 32-case safety buffer before the primary runner reaches this tail.
"""
import argparse,concurrent.futures,json,multiprocessing,os,time
from pathlib import Path
from .train import atomic
from .evaluate import native_worker

def safe_to_launch(state,task,tail_start,buffer=32):
    state=Path(state);progress=json.loads((state/'economic-progress.json').read_text())
    if progress.get('completed',0)>=tail_start-buffer:return False
    base=state/'native'/task['id']
    # A result is reusable; an attempt without a result belongs to a live/failed
    # owner and must never be stolen. The tail is fixed before any outcome read.
    return not (base/'RESULT.json').exists() and not any(base.glob('attempt-*'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state)
    tasks=json.loads((state/'NATIVE_TASKS.json').read_text())['tasks'];assert len(tasks)==720
    first=len(tasks)-120;tail=tasks[first:];done=[];errors=[];next_index=0
    path=state/'DEV_FIXED_TAIL_ASSIST.json'
    if path.exists():raise RuntimeError('Fixed assistance already started; do not duplicate owners')
    atomic(path,dict(status='FIXED_TAIL_TWO_WORKERS',source_indices=[first,len(tasks)],tasks=[t['id'] for t in tail],completed=[],errors=[],pid=os.getpid()))
    with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
        pending={}
        while pending or next_index<len(tail):
            while len(pending)<2 and next_index<len(tail):
                task=tail[next_index];next_index+=1
                if not safe_to_launch(state,task,first):continue
                pending[pool.submit(native_worker,task)]=task
            if not pending:break
            ready,_=concurrent.futures.wait(pending,timeout=30,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in ready:
                task=pending.pop(future)
                try:future.result();done.append(task['id'])
                except Exception as exc:
                    # The primary runner can make the one remaining permitted
                    # attempt. Do not race its retry or erase this failed attempt.
                    errors.append(dict(task_id=task['id'],error=str(exc)))
                print(f'ASSIST {len(done)}/120 failed={len(errors)} {task["id"]}',flush=True)
            atomic(path,dict(status='RUNNING',source_indices=[first,len(tasks)],completed=done,errors=errors,in_flight=len(pending),pid=os.getpid(),updated_at=time.time()))
    atomic(path,dict(status='FINISHED_REUSE_BY_PRIMARY',source_indices=[first,len(tasks)],completed=done,errors=errors,pid=os.getpid(),updated_at=time.time()))

if __name__=='__main__':main()
