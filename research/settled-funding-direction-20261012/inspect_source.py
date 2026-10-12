"""Bounded public source schema inspection; no target or economic scoring."""
import importlib.util,io,json,subprocess,zipfile,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
def sha(raw):return hashlib.sha256(raw).hexdigest()
spec=importlib.util.spec_from_file_location('consumer',ROOT/'research/portfolio-risk-2025-admission-20261012/source2025.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
z,read=m.consumer()
for name in z.namelist():
 if name.startswith('economics2025/BTC'):
  f=pd.read_parquet(io.BytesIO(read(name)));print(name,len(f),list(f.columns),f.head(1).to_dict('records'),f.tail(1).to_dict('records'),flush=True)
with np.load(io.BytesIO(read('features2025/FEATURES.npz')),allow_pickle=False) as a:print('FEATURES',[(k,a[k].shape) for k in a.files],int(a['completed_day_available_us'][0]),int(a['completed_day_available_us'][-1]),flush=True)
z.close()
c='e0d3400b23842f11f167a63e7d80856d76501de8';p='research/temporal-feature-data-20261009/';ix=json.loads(git(c+':'+p+'INDEX.json'));chunks=[]
for r in ix['parts']:
 b=git(c+':'+p+r['file']);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];chunks.append(b)
b=b''.join(chunks);assert sha(b)==ix['SHA256'];z=zipfile.ZipFile(io.BytesIO(b));assert z.testzip() is None
name='source_tables_not_model_inputs/economics/BTCUSDT_funding_events.parquet';f=pd.read_parquet(io.BytesIO(z.read(name)));print('2022WARM_SCHEMA',len(f),list(f.columns),f.head(1).to_dict('records'),f.tail(1).to_dict('records'),flush=True)
ix=json.loads(git('d69e9ac94478c5be54cb46c622afec7aaf3c61f7:research_artifacts/native_20261008/INDEX.json'));print('NATIVE_FILES',[(r.get('path'),r.get('bytes'),r.get('SHA256')) for r in ix['files'] if 'tail' in str(r).lower()],flush=True)
