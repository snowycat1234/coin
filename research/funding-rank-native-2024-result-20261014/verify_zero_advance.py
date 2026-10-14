from pathlib import Path
import argparse,json,sys
p=argparse.ArgumentParser();p.add_argument('--runtime-root',required=True);p.add_argument('--roots',required=True);p.add_argument('--case',required=True);a=p.parse_args();sys.path.insert(0,a.runtime_root)
import v2_launcher as v
roots=json.loads(Path(a.roots).read_text());port,account,sim=v.load_engine(roots);c=Path(a.case)/'checkpoint';pointer=json.loads((c/'POINTER.json').read_text());snapshot,verified=port.restore_snapshot(c,pointer['binding']);window=v.source_window(2024,roots['source2024'],roots.get('derived_csv'));state=sim.from_snapshot(snapshot,window,account_class=account);assert state.state_hash()==pointer['state_hash'];assert state.rows_written==pointer['completed_minutes'];print(json.dumps({'status':'PASS_REAL_ZERO_ADVANCE','state_hash':state.state_hash(),'minutes':state.rows_written,'advance_calls':0}))
