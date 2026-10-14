"""Focused standard-library transport tests; no CONTROL or finance reruns."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
    raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_LAUNCH_REQUIRED')
from pathlib import Path
import argparse,ast,gzip,hashlib,json,os,shutil,subprocess,tempfile,unittest
HERE=Path(__file__).resolve().parent
CACHE_INDEX=None
EXPECTED=None

def sha(data):return hashlib.sha256(data).hexdigest()
def child_environment():
    return {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONOPTIMIZE','PYTHONSTARTUP')}
def compiled_wrapper():
    ns={'__name__':'transport_unit_review','__file__':str(HERE/'restore_transport.py')}
    exec(compile((HERE/'restore_transport.py').read_bytes(),str(HERE/'restore_transport.py'),'exec'),ns)
    return ns
class Transport(unittest.TestCase):
    def call(self,root,index,temp,sha_value=None):
        out=Path(temp)/'restored';receipt=Path(temp)/'receipt.json'
        r=subprocess.run([sys.executable,'-I','-S','-B',str(root/'restore_transport.py'),
            '--manifest-sha',sha_value or EXPECTED,'--cache-index',str(index),
            '--output',str(out),'--receipt',str(receipt)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20,env=child_environment())
        return r,out,receipt
    def test_exact_saved_restore_before_any_project_import(self):
        with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
            r,out,receipt=self.call(HERE,CACHE_INDEX,d)
            self.assertEqual(r.returncode,0,r.stdout)
            saved=json.loads(receipt.read_text())
            self.assertEqual(saved['project_imports'],0);self.assertEqual(saved['CONTROL_retests'],0)
            self.assertEqual(saved['immutable_reused_blobs'],61);self.assertEqual(saved['restored_scientific_files'],14)
            aliases=json.loads((HERE/'GENERATED_EVIDENCE_CATALOG.json').read_text())['aliases']
            bodies=[(out/a).read_bytes() for a in aliases]
            self.assertEqual(bodies[0],bodies[1]);self.assertEqual(len(json.loads(bodies[0])['runs']),19)
            self.assertEqual(sha(bodies[0]),'99b934cdbf99679512cf484cb145a654d131207d5d94cb92433a2aa6a4b2ce97')
    def test_wrong_external_manifest_fails_before_output(self):
        with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
            r,out,receipt=self.call(HERE,CACHE_INDEX,d,'0'*64)
            self.assertNotEqual(r.returncode,0);self.assertIn('PUBLIC_MANIFEST_PIN',r.stdout)
            self.assertFalse(out.exists());self.assertFalse(receipt.exists())
    def test_scientific_tamper_fails_before_output(self):
        with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
            copy=Path(d)/'payload';shutil.copytree(HERE,copy)
            source=copy/'coin_paired_headroom_native_generated_20261014/native_adapter.py'
            source.write_bytes(source.read_bytes()+b'\n')
            r,out,receipt=self.call(copy,CACHE_INDEX,d)
            self.assertNotEqual(r.returncode,0);self.assertIn('EXACT_BLOB_SIZE_REQUIRED',r.stdout)
            self.assertFalse(out.exists());self.assertFalse(receipt.exists())
    def test_cache_tamper_fails_before_output(self):
        with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
            index=json.loads(CACHE_INDEX.read_text());key=next(iter(index));bad=Path(d)/'bad_public_code.json'
            bad.write_bytes(Path(index[key]).read_bytes()+b' ');index[key]=str(bad)
            changed=Path(d)/'cache.json';changed.write_text(json.dumps(index))
            r,out,receipt=self.call(HERE,changed,d)
            self.assertNotEqual(r.returncode,0);self.assertIn('EXACT_BLOB_SIZE_REQUIRED',r.stdout)
            self.assertFalse(out.exists());self.assertFalse(receipt.exists())
    def test_unlisted_shadow_and_cache_refused_without_execution(self):
        for name in ('gzip.py','__pycache__/unlisted.pyc'):
            with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
                copy=Path(d)/'payload';shutil.copytree(HERE,copy)
                marker=Path(d)/'executed.json';extra=copy/name;extra.parent.mkdir(parents=True,exist_ok=True)
                extra.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("shadow executed")\n')
                r,out,receipt=self.call(copy,CACHE_INDEX,d)
                self.assertNotEqual(r.returncode,0);self.assertIn('EXACT_PUBLIC_PAYLOAD_FILE_AND_DIRECTORY_SET_REQUIRED',r.stdout)
                self.assertFalse(marker.exists());self.assertFalse(out.exists());self.assertFalse(receipt.exists())
    def test_nonisolated_and_optimized_launch_refused_before_shadow_import(self):
        with tempfile.TemporaryDirectory(dir=HERE.parent) as d:
            copy=Path(d)/'payload';shutil.copytree(HERE,copy)
            marker=Path(d)/'executed.json';(copy/'gzip.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("shadow executed")\n')
            for flags in (['-B'],['-I','-B'],['-I','-S','-B','-O']):
                r=subprocess.run([sys.executable,*flags,str(copy/'restore_transport.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20,env=child_environment())
                self.assertNotEqual(r.returncode,0);self.assertIn('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_LAUNCH_REQUIRED',r.stdout)
                self.assertFalse(marker.exists())
    def test_traversal_arrays_and_oversized_gzip_refused(self):
        ns=compiled_wrapper()
        for path in ('../evil.py','a/../evil.py','/absolute.py','a\\b.py','data.npz','data.npy','data.parquet','wheel.whl'):
            with self.assertRaises(ValueError):ns['relative'](path)
        with self.assertRaises(ValueError):ns['decompress'](gzip.compress(b'x'*1000,mtime=0),sha(b'x'*10),10)
    def test_no_project_import_or_network_dependency(self):
        tree=ast.parse((HERE/'restore_transport.py').read_text())
        names={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        names|={n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
        self.assertLessEqual(names,{'pathlib','argparse','gzip','hashlib','io','json','re','sys'})
        self.assertNotIn('subprocess',names);self.assertNotIn('socket',names)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache-index',type=Path,required=True);p.add_argument('--manifest-sha',required=True)
    a=p.parse_args();CACHE_INDEX=a.cache_index;EXPECTED=a.manifest_sha
    raw=(HERE/'PUBLIC_PAYLOAD_MANIFEST.json').read_bytes()
    if sha(raw)!=EXPECTED:raise ValueError('EXTERNAL_PUBLIC_MANIFEST_REQUIRED')
    manifest=json.loads(raw)
    for name,r in manifest['files'].items():
        b=(HERE/name).read_bytes()
        if len(b)!=r['bytes'] or sha(b)!=r['SHA256']:raise ValueError('EXACT_PUBLIC_TEST_INPUT_REQUIRED')
    unittest.main(argv=[sys.argv[0]],verbosity=2)
