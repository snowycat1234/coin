"""Existing progress-window publisher without model-library imports."""
import json,os,threading,time
from pathlib import Path
from quant.paths import STATE

class Progress:
    def __init__(self):
        self.pid=os.getpid()
        self.ticks=int(Path(f'/proc/{self.pid}/stat').read_text().split(') ',1)[1].split()[19])
        self.value=dict(pid=self.pid,start_ticks=self.ticks,task_id=os.environ.get('COIN_TASK_ID'),
            phase='启动',completed=None,total=None,unit='',metrics={},detail='已有任务进度接口')
        self.stop=threading.Event();self.thread=threading.Thread(target=self.heartbeat,daemon=True);self.thread.start()
    def heartbeat(self):
        while not self.stop.is_set():
            path=STATE/'task-progress'/f'sample-{self.pid}.json';temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(self.value,updated_at=time.time()),ensure_ascii=False,allow_nan=False))
            os.replace(temporary,path);self.stop.wait(2)
    def update(self,phase,completed,total,unit,**metrics):
        self.value=dict(self.value,phase=phase,completed=completed,total=total,unit=unit,metrics=metrics)
        print(json.dumps(dict(phase=phase,completed=completed,total=total,unit=unit,**metrics),ensure_ascii=False),flush=True)
