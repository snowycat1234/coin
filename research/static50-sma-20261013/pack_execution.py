"""Small portable inputs+adapter; original engine/source stay Git pinned."""
import base64,hashlib,io,json,subprocess,textwrap,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DEST=HERE/'public/EXECUTION'
FILES=('PROTOCOL.json','NATIVE_PLAN.json','input/READINESS.json','input/Y2023.npz','input/Y2025.npz','native_wallet.py','targets.py','RESOURCE_GATE.json','public/ORIGINAL_TARGETS/INDEX.json')
DEPENDENCIES=('scripts/investment/resumable_perpetual.py','scripts/investment/perpetual_closing_exempt_account.py','research/quantity-grid-sensitivity-20261012/grid_account.py','src/quant/perpetual_account.py','research/sma200-native-20261013/native_apis.py','research/rejected-break-follow-native-20261012/cold_source.py','research/slow-momentum-cpd-20261011/launch.sh')
def sha(b):return hashlib.sha256(b).hexdigest()
def run():
 assert not DEST.exists() and not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
 DEST.mkdir(parents=True);records={};stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_STORED) as z:
  for name in FILES:
   b=(HERE/name).read_bytes();records[name]=dict(bytes=len(b),SHA256=sha(b));z.writestr(zipfile.ZipInfo(name,(1980,1,1,0,0,0)),b)
 raw=stream.getvalue();encoded=('\n'.join(textwrap.wrap(base64.b64encode(raw).decode('ascii'),76))+'\n').encode('ascii');(DEST/'EXECUTION.zip.b64').write_bytes(encoded)
 with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as z:
  assert z.testzip() is None and set(z.namelist())==set(FILES)
  for name in FILES:assert sha(z.read(name))==records[name]['SHA256']
 dependencies={p:sha((ROOT/p).read_bytes()) for p in DEPENDENCIES}
 r=json.loads((HERE/'input/READINESS.json').read_text())
 for key in ('Y2023','Y2025'):assert records['input/'+key+'.npz']['SHA256']==r['years'][key]['target_SHA256']
 (DEST/'INDEX.json').write_text(json.dumps(dict(status='PASS_MINIMAL_NATIVE_EXECUTION_INPUT_AND_GUARDED_ADAPTER_UNRUN',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),files=records,dependencies_required_from_pinned_coin_Git=dependencies,source_monthly_caches_REQUIRED_FROM_PUBLIC_GIT_NOT_PACKED=True,financial_kernel_SOURCE_SHAs={'resumable_perpetual':dependencies[DEPENDENCIES[0]],'closing_account':dependencies[DEPENDENCIES[1]],'quantity_grid':dependencies[DEPENDENCIES[2]],'perpetual_account':dependencies[DEPENDENCIES[3]]},ZIP_SHA256=sha(raw),ZIP_bytes=len(raw),UTF8_Base64_SHA256=sha(encoded),UTF8_Base64_bytes=len(encoded),new_wallets=0,source_downloads=0),indent=2,sort_keys=True)+'\n')
 print('ACTUAL_MINIMAL_GUARDED_EXECUTION_PACKAGE',len(raw),len(encoded),sha(raw),flush=True)
if __name__=='__main__':run()
