"""Pack exact final journals/state and eleven core minute values; no simulator."""
import argparse,gzip,hashlib,io,json,zipfile,csv
from pathlib import Path
import numpy as np
CORE=['nav','free_cash','isolated_balance','gross_notional','net_signed_notional','cumulative_fees','cumulative_execution_costs','cumulative_funding','cumulative_turnover','gross_weight','net_signed_weight']
def sha(b):return hashlib.sha256(b).hexdigest()
def build(out,dest,times):
 dest.mkdir(exist_ok=False);pointer=json.loads((out/'recovery/POINTER.json').read_text());raw=(out/'recovery'/pointer['snapshot_path']).read_bytes();assert sha(raw)==pointer['snapshot_SHA256'];snapshot=json.loads(gzip.decompress(raw));bind=json.loads((out/'BINDING.json').read_text());assert pointer['binding']==bind;result=json.loads((out/'RESULT.json').read_text());assert result['genuine_state_hash']==pointer['state_hash']
 fingerprints=json.loads((out/'MINUTE_NUMERIC.json').read_text())['columns'];names=[r['name'] for r in fingerprints if r['name']!='close_us'];by={r['name']:r for r in fingerprints};idx=[names.index(n) for n in CORE];pieces=[]
 for row in pointer['chunks']:
  b=(out/'recovery'/row['path']).read_bytes();assert sha(b)==row['SHA256']
  with np.load(io.BytesIO(b),allow_pickle=False) as z:a=z['minute_chunk'];assert a.shape==(row['rows'],row['columns']) and a.dtype==np.float64 and np.isfinite(a).all();pieces.append(a[:,idx].copy())
 values=np.concatenate(pieces);n=len(values);assert n==pointer['completed_minutes']==result['completed_minutes'];clock=bind['calendar'][0]+np.arange(1,n+1,dtype=np.int64)*60000000
 for j,name in enumerate(CORE):assert sha(values[:,j].tobytes())==by[name]['raw_SHA256']
 assert sha(clock.tobytes())==by['close_us']['raw_SHA256'];core=io.BytesIO();np.savez_compressed(core,values=values,close_us=clock,columns=np.array(CORE))
 account=json.loads((out/'ACCOUNT.json').read_text());s=account['summary'];metrics=dict(mean_net=float(values[:,10].mean()),max_abs_net=float(np.abs(values[:,10]).max()),fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],turnover_USDT=s['gross_fill_turnover_USDT'],terminal_residual_gross_USDT=s['terminal_marked_notional'])
 target=io.StringIO();writer=csv.DictWriter(target,fieldnames=['available_us','symbol','target_weight']);writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in account['targets'])
 members={n:(out/n).read_bytes() for n in ('RESULT.json','BINDING.json','MINUTE_NUMERIC.json','DAILY.csv','ACCOUNT.json','TIMING.json')};members.update({'FINAL_STATE.json.gz':raw,'POINTER.json':(out/'recovery/POINTER.json').read_bytes(),'CORE_MINUTE.npz':core.getvalue(),'TARGETS.csv':target.getvalue().encode(),'SUMMARY.json':json.dumps(dict(summary=s,extrema=account['extrema']),indent=2,sort_keys=True).encode()+b'\n','METRICS.json':json.dumps(metrics,indent=2,sort_keys=True).encode()+b'\n','TIMES.json':times.read_bytes()})
 packet=io.BytesIO()
 with zipfile.ZipFile(packet,'w',compression=zipfile.ZIP_STORED) as z:
  for name,b in members.items():z.writestr(zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)),b)
 body=packet.getvalue();parts=[]
 for i,offset in enumerate(range(0,len(body),4*2**20)):
  b=body[offset:offset+4*2**20];name=f'PACKET.zip.part{i:04d}';(dest/name).write_bytes(b);parts.append(dict(name=name,bytes=len(b),sha256=sha(b)))
 index=dict(case=result['case_id'],packet_bytes=len(body),packet_sha256=sha(body),parts=parts,members={name:dict(bytes=len(b),sha256=sha(b)) for name,b in members.items()},core_minute_rows=n,original_checkpoint_sha256=pointer['snapshot_SHA256'],original_state_hash=pointer['state_hash'],scope='Exact final state and all fills/funding/daily/targets; 11 core minute fields and original 37 numeric fingerprints. Full original minute chunks remain local. Not complete checkpoint byte cold recovery.')
 (dest/'INDEX.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
 for name in ('RESULT.json','METRICS.json','TIMES.json'):(dest/name).write_bytes(members[name])
 print('MINIMAL_PACKET_READY',n,len(body),len(parts))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('dest',type=Path);p.add_argument('--times',type=Path,required=True);a=p.parse_args();build(a.out,a.dest,a.times)
