"""Reuses the published source-only parser/audits, never a financial replay."""
import importlib.util,json,io,os,subprocess,sys,zipfile
from pathlib import Path
from recover import STATE,get,jsonget,sha,write,REPO,FULL2021
ROOT=STATE/'source2021'
def main():
 prefix='research/core5-2021-fullsource-20261013/'
 raw=get('53357f33f4e6ccb536af762fbff39b269c24d837','research/settled-funding-direction-20261012/public/INPUTS_FINAL/PACKET.zip')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None
  cube=z.read('Y2023.npz');assert sha(cube)=='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
 write(STATE/'inputs/Y2023.npz',cube)
 c='e0d3400b23842f11f167a63e7d80856d76501de8';p='research/temporal-feature-data-20261009/';idx=jsonget(c,p+'INDEX.json')
 parts=[get(c,p+r['file'],r['SHA256']) for r in idx['parts']];features=b''.join(parts);assert len(features)==idx['bytes'] and sha(features)==idx['SHA256']
 write(STATE/'inputs/features.zip',features)
 # Check date-column footer bounds before the original audits read table bodies.
 import pyarrow.parquet as pq
 with zipfile.ZipFile(io.BytesIO(features)) as z:
  for n in z.namelist():
   if n.endswith('.parquet'):
    file=pq.ParquetFile(io.BytesIO(z.read(n)))
    for i in range(file.metadata.num_row_groups):
     group=file.metadata.row_group(i)
     for j in range(group.num_columns):
      col=group.column(j)
      if col.path_in_schema=='dt':
       assert col.statistics and col.statistics.has_min_max
       assert str(col.statistics.max)<'2026-03-01',('reserved-range source',n,col.statistics.max)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1',COIN_CUBE_PATH=str(STATE/'inputs/Y2023.npz'),COIN_FEATURES_PATH=str(STATE/'inputs/features.zip'),COIN_2021_SOURCE_OUT=str(STATE/'prepared_2021'))
 # Its supported local-Git cache search is pointed at this instance's existing repo.
 loader=ROOT/'restore_local_git.py'
 write(loader,b"import importlib.util\nfrom pathlib import Path\ns=importlib.util.spec_from_file_location('original_source_restore',Path(__file__).parent/'restore_public_sources.py')\nm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.REPOS=[Path('/workspace/coin')]\nm.main()\n")
 for name in ('test_source_parser.py','restore_local_git.py','audit_warmup.py','audit_funding.py','assemble_offline.py','prepare_full_2021.py','verify_few_boundaries.py'):
  print('SOURCE2021_STEP',name,flush=True)
  with (STATE/(name+'.log')).open('xb') as log:
   subprocess.run([sys.executable,str(ROOT/name)],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('FULL2021_SOURCE_READY',flush=True)
if __name__=='__main__':main()
