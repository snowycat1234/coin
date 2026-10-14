"""Standalone saved-byte transport checks; imports no financial/strategy source."""
from __future__ import annotations
import importlib.util,json,pathlib,shutil,subprocess,sys,tempfile,unittest
HERE=pathlib.Path(__file__).resolve().parent

def load(root):
    spec=importlib.util.spec_from_file_location('journal_transport',root/'restore_journals.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class SavedJournalTransport(unittest.TestCase):
    def copy(self,root):
        for name in ['restore_journals.py','JOURNAL_BODY_MANIFEST.json','GENERATED_JOURNALS.tar.gz']:
            shutil.copyfile(HERE/name,root/name)
    def test_all_33_native_bodies(self):
        manifest,bodies=load(HERE).verify()
        self.assertEqual(len(bodies),33);self.assertEqual(sum(map(len,bodies.values())),10028220)
        self.assertFalse(manifest['historical_GO'])
    def test_archive_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);self.copy(root);p=root/'GENERATED_JOURNALS.tar.gz';raw=bytearray(p.read_bytes());raw[-9]^=1;p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA256'):load(root).verify()
    def test_manifest_size_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);self.copy(root);p=root/'JOURNAL_BODY_MANIFEST.json';j=json.loads(p.read_text());j['native_total_bytes']+=1;p.write_text(json.dumps(j))
            with self.assertRaisesRegex(ValueError,'NATIVE_SIZE'):load(root).verify()
    def test_restore_exact_then_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            out=pathlib.Path(temp)/'new';command=[sys.executable,'-B',str(HERE/'restore_journals.py'),'--output',str(out)]
            r=subprocess.run(command,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            _,bodies=load(HERE).verify()
            for name,raw in bodies.items():self.assertEqual((out/name).read_bytes(),raw)
            r=subprocess.run(command,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('OUTPUT_MUST_BE_NEW',r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
