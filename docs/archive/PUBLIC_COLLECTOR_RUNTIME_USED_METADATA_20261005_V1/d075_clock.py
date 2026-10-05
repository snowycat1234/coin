import json,os,time
from pathlib import Path
p=Path('/home/xflops/coin-state/d075-runtime-restoration-20261005-v1')
old=json.loads((p/'PRESERVATION.json').read_bytes())
print(json.dumps(dict(task_id=os.environ['COIN_TASK_ID'],observed_epoch=time.time(),
 current_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 preserved_boot_id=old['boot_id'],preserved_uptime=old['uptime'],
 current_uptime=Path('/proc/uptime').read_text().strip())))
