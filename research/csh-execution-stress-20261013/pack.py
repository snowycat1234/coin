"""Minimal audit packet: existing final state, journals, core numeric trace, daily/targets."""
import argparse,datetime,gzip,hashlib,io,json,os,shutil,sys,time,zipfile
from pathlib import Path
from recover import STATE,REPO,sha,write
HERE=Path(__file__).resolve().parent
CORE=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional','cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover','gross_weight','net_signed_weight']
IDX=[*range(9),34,35]

def build(case):
 import numpy as np
 original=STATE/'wallets'/case;destination=HERE/'result'/case
 destination.mkdir(parents=True,exist_ok=False)
 pointer=json.loads((original/'recovery/POINTER.json').read_text());binding=json.loads((original/'BINDING.json').read_text());assert pointer['binding']==binding
 original_snapshot=original/'recovery'/pointer['snapshot_path'];assert sha(original_snapshot.read_bytes())==pointer['snapshot_SHA256']
 snapshot=json.loads(gzip.decompress(original_snapshot.read_bytes()));assert snapshot['state']['rows_written']==pointer['completed_minutes']
 frames=[]
 for r in pointer['chunks']:
  raw=(original/'recovery'/r['path']).read_bytes();assert sha(raw)==r['SHA256']
  with np.load(io.BytesIO(raw),allow_pickle=False) as a:
   values=a['minute_chunk'];assert values.shape==(r['rows'],r['columns']) and values.dtype==np.float64
   assert np.isfinite(values).all();frames.append(values[:,IDX].copy())
 values=np.concatenate(frames);assert len(values)==pointer['completed_minutes']
 start=pointer['binding']['calendar'][0];close=np.arange(len(values),dtype=np.int64)*60000000+start+60000000
 trace=STATE/'pack-work'/case/'CORE_MINUTE.npz';trace.parent.mkdir(parents=True,exist_ok=True)
 np.savez_compressed(trace,values=values,close_us=close,columns=np.array(CORE))
 fingerprints=json.loads((original/'MINUTE_NUMERIC.json').read_text());by_name={r['name']:r for r in fingerprints}
 for j,n in enumerate(CORE):assert sha(values[:,j].tobytes())==by_name[n]['raw_SHA256']
 assert sha(close.tobytes())==by_name['close_us']['raw_SHA256']
 result=json.loads((original/'RESULT.json').read_text());assert result['completed_minutes']==len(values)
 finish=datetime.datetime.fromtimestamp((original/'RESULT.json').stat().st_mtime_ns/1e9,datetime.UTC).isoformat()
 times=dict(start_UTC=json.loads((original/'STARTED.json').read_text())['start_UTC'],end_UTC=finish,end_clock_definition='Actual filesystem timestamp when final RESULT.json write completed, before worker final print/exit',elapsed_monotonic_seconds=result['elapsed_seconds'])
 members={n:(original/n).read_bytes() for n in ('RESULT.json','BINDING.json','DAILY.csv','TARGETS.csv','MINUTE_NUMERIC.json')}
 members['TIMES.json']=(json.dumps(times,indent=2,sort_keys=True)+'\n').encode()
 members['FINAL_STATE.json.gz']=original_snapshot.read_bytes();members['POINTER.json']=(original/'recovery/POINTER.json').read_bytes();members['CORE_MINUTE.npz']=trace.read_bytes()
 # Snapshot already contains all original financial and scheduling journals.
 # Store summary + extrema separately for independent reader convenience.
 account=json.loads((original/'ACCOUNT.json').read_text());members['SUMMARY.json']=(json.dumps(dict(summary=account['summary'],extrema=account['extrema']),indent=2,sort_keys=True)+'\n').encode()
 packet=STATE/'pack-work'/case/'PACKET.zip'
 with zipfile.ZipFile(packet,'w',compression=zipfile.ZIP_STORED) as z:
  for n,raw in members.items():
   info=zipfile.ZipInfo(n,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED;z.writestr(info,raw)
 body=packet.read_bytes();parts=[]
 for i,off in enumerate(range(0,len(body),4*2**20)):
  raw=body[off:off+4*2**20];name=f'PACKET.zip.part{i:04d}';write(destination/name,raw);parts.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
 index=dict(case=case,packet_bytes=len(body),packet_sha256=sha(body),parts=parts,members={n:dict(bytes=len(raw),sha256=sha(raw)) for n,raw in members.items()},
  core_minute_columns=CORE,core_minute_rows=len(values),full_original_minute_numeric_columns=37,
  numerical_scope='Published 11 core completed-minute float64 columns + exact int64 clocks, all37 daily values, all37 original raw-column fingerprints. 25 per-asset minute columns remain in original local lossless checkpoints and are not independently recovered from this minimal packet.',
  original_checkpoint_sha256=pointer['snapshot_SHA256'],original_state_hash=pointer['state_hash'],times=times)
 write(destination/'INDEX.json',(json.dumps(index,indent=2,sort_keys=True)+'\n').encode())
 write(destination/'RESULT.json',members['RESULT.json']);write(destination/'TIMES.json',members['TIMES.json'])
 print('MINIMAL_PACKET_READY',case,len(body),len(parts),flush=True)
 return index
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('case');a=p.parse_args();os.sched_setaffinity(0,{sorted(os.sched_getaffinity(0))[1]});build(a.case)
